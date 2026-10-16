"""Макрос FreeCAD (Д-65): чертежи деталей TechDraw из 3D-геометрии STEP.

Виды — проекции формы детали из открытого <ID>.step; размеры и геометрические значения
легенды измеряются по этой же форме: сечение плоскостью z (наружный контур, внутренний
контур, отверстия, окна), цилиндрические грани, BoundBox. Из <ID>.assy.json → drawings —
только эталоны сверки, обозначения и смысл колонок SPEC-10/SPEC-11, неизмеримые величины,
примечания, формат. Расхождение 3D с эталоном больше tol или неизмеренный размер —
красный блок предупреждений на листе и строка в <ID>.techdraw.md.
Правила (z сечения, масштаб, сверка, легенда) — egm/cad/techdraw.py из репозитория.
Деталь ищется по метке-алиасу, как в tools/freecad_meta.py; форма — в системе детали.
Запуск: открыть <ID>.step; Макрос → Макросы… → этот файл → Выполнить → выбрать
<ID>.assy.json. Повторный запуск пересоздаёт листы (объекты со свойством egm_drw).
"""
import json
import math
import os
import re
import sys

import FreeCAD as App
import Part

GROUP = "EGM_TechDraw"
TAG = "egm_drw"
TEMPLATES = ("A3_Landscape_blank.svg", "A3_Landscape_ISO7200TD.svg")
DIRS = {"front": ((0, 0, 1), (1, 0, 0)),
        "side": ((0, -1, 0), (0, 0, 1)),
        "iso": ((1, -1, 1), (1, 1, 0))}
VTOL = 0.05                         # допуск поиска кромки на виде, мм


def _td(path):
    """egm/cad/techdraw.py: ищется вверх от макроса и от <ID>.assy.json."""
    starts = [os.path.dirname(os.path.abspath(path))]
    if "__file__" in globals():
        starts.insert(0, os.path.dirname(os.path.abspath(__file__)))
    for d in starts:
        while True:
            if os.path.exists(os.path.join(d, "egm", "cad", "techdraw.py")):
                if d not in sys.path:
                    sys.path.insert(0, d)
                from egm.cad import techdraw
                return techdraw
            up = os.path.dirname(d)
            if up == d:
                break
            d = up
    raise ImportError("не найден egm/cad/techdraw.py выше " + path)


def _strip(label):
    return re.sub(r"(?<=\))\d+$", "", label)


def _mark(o, pid):
    if TAG not in o.PropertiesList:
        o.addProperty("App::PropertyString", TAG, "EGM", "чертёж детали (Д-65)")
    setattr(o, TAG, pid)


def _clear(doc):
    def rank(o):
        t = o.TypeId
        return (0 if "Dimension" in t else 2 if t == "TechDraw::DrawPage"
                else 1 if t.startswith("TechDraw::") else 3)
    for name in [o.Name for o in sorted([o for o in doc.Objects if TAG in o.PropertiesList], key=rank)]:
        if doc.getObject(name) is not None:
            doc.removeObject(name)


def _template():
    base = os.path.join(App.getResourceDir(), "Mod", "TechDraw", "Templates")
    for name in TEMPLATES:
        if os.path.exists(os.path.join(base, name)):
            return os.path.join(base, name)
    for root, _, files in os.walk(base):
        for f in sorted(files):
            if f.startswith("A3_Landscape") and f.endswith(".svg"):
                return os.path.join(root, f)
    return None


def _sources(doc, wanted):
    """метка-алиас -> форма детали в её системе координат."""
    out = {}
    for o in doc.Objects:
        lab = _strip(o.Label)
        if lab not in wanted or lab in out:
            continue
        try:
            sh = Part.getShape(o, "", needSubElement=False, transform=False)
        except Exception:
            continue
        if not sh.isNull() and sh.Solids:
            out[lab] = sh.copy()
    return out


# ---------- измерение по 3D ----------
def _tn(o):
    return type(o).__name__


def _circ(w):
    """Замкнутый провод из дуг одной окружности -> (x, y, r), иначе None."""
    cs = [e.Curve for e in w.Edges]
    if not cs or any(_tn(c) != "Circle" for c in cs):
        return None
    c0 = cs[0]
    for c in cs[1:]:
        if (c.Center - c0.Center).Length > 1e-6 or abs(c.Radius - c0.Radius) > 1e-6:
            return None
    return c0.Center.x, c0.Center.y, c0.Radius


def _rho(w, step=0.05):
    out = []
    for e in w.Edges:
        n = max(16, int(e.Length / step) + 1)
        out += [math.hypot(p.x, p.y) for p in e.discretize(Number=n)]
    return out


def _section(shape, z):
    ws = shape.slice(App.Vector(0, 0, 1), z)
    if not ws:
        raise ValueError(f"сечение z = {z:g} пустое")
    oi = max(range(len(ws)), key=lambda i: ws[i].BoundBox.DiagonalLength)
    holes, inner = [], []
    for i, w in enumerate(ws):
        if i == oi:
            continue
        c = _circ(w)
        if c and math.hypot(c[0], c[1]) > 1e-3:
            holes.append(c)
        else:
            inner.append(w)
    inner.sort(key=lambda w: -w.BoundBox.DiagonalLength)
    return {"n": len(ws), "outer": ws[oi], "oc": _circ(ws[oi]), "holes": holes,
            "inner": inner[0] if inner else None}


def _value(c, sec, cyl, bb):
    k, v = c["kind"], c["value"]
    if k == "length":
        return bb.ZLength
    if k == "d_cyl":
        return 2 * min(cyl, key=lambda r: abs(2 * r - v)) if cyl else "нет цилиндрических граней"
    if sec is None or isinstance(sec, str):
        return sec or "нет сечения"
    if k == "windows":
        return sec["n"]
    oc = sec["oc"]
    if k == "d_out":
        return 2 * oc[2] if oc else 2 * max(_rho(sec["outer"]))
    if k == "center":
        return [oc[0], oc[1]] if oc else "наружный контур не окружность"
    if k in ("d_root", "d_tip"):
        if sec["inner"] is None:
            return "нет внутреннего контура"
        r = _rho(sec["inner"])
        return 2 * max(r) if k == "d_root" else 2 * min(r)
    hs = sec["holes"]
    if k == "n_holes":
        return len(hs)
    if not hs:
        return "нет отверстий в сечении"
    if k == "d_bc":
        return 2 * sum(math.hypot(x, y) for x, y, _ in hs) / len(hs)
    if k == "d_hole":
        return 2 * min((r for _, _, r in hs), key=lambda r: abs(2 * r - v))
    if k == "holes_xy":
        return max(min(math.hypot(x - px, y - py) for px, py, _ in hs) for x, y in c["ref"])
    return f"вид проверки {k} не поддержан"


def measure(shape, chk):
    """{sym: значение по 3D | строка-причина} для эталонов chk."""
    bb = shape.BoundBox
    cyl = sorted({round(f.Surface.Radius, 6) for f in shape.Faces if _tn(f.Surface) == "Cylinder"})
    secs, out = {}, {}
    for c in chk:
        z = c.get("z")
        if z is not None and z not in secs:
            try:
                secs[z] = _section(shape, z)
            except Exception as e:
                secs[z] = f"сечение z = {z:g}: {type(e).__name__}: {e}"
        try:
            out[c["sym"]] = _value(c, secs.get(z), cyl, bb)
        except Exception as e:
            out[c["sym"]] = f"{type(e).__name__}: {e}"
    return out


# ---------- лист ----------
def _title(tpl, pid, rec, sh):
    try:
        t = dict(tpl.EditableTexts)
    except Exception:
        return
    for k in t:
        kl = k.lower()
        if "scale" in kl:
            t[k] = sh["scale_txt"]
        elif "number" in kl or kl in ("dn", "doc_number"):
            t[k] = pid
        elif "title" in kl:
            t[k] = rec["name"] or rec["label"]
    tpl.EditableTexts = t


def _page(doc, pid, rec, sh, tpl_path):
    page = doc.addObject("TechDraw::DrawPage", "Page")
    page.Label = f"DRW {rec['label']}"
    _mark(page, pid)
    if tpl_path:
        tpl = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
        tpl.Template = tpl_path
        page.Template = tpl
        _mark(tpl, pid)
        _title(tpl, pid, rec, sh)
    return page


def _view(doc, page, pid, src, key, pos):
    d, xd = DIRS[key]
    v = doc.addObject("TechDraw::DrawViewPart", "View")
    page.addView(v)
    v.Source = [src]
    v.Direction = App.Vector(*d)
    if "XDirection" in v.PropertiesList:
        v.XDirection = App.Vector(*xd)
    v.ScaleType = "Custom"
    v.Scale = pos[2]
    v.X, v.Y = pos[0], pos[1]
    v.Label = f"{key} {pid.split('.', 1)[-1]}"
    _mark(v, pid)
    return v


def _edges(v):
    try:
        return list(enumerate(v.getVisibleEdges()))
    except Exception:
        return []


def _circle(v, r, s):
    circ = [(i, e.Curve.Radius) for i, e in _edges(v) if _tn(getattr(e, "Curve", None)) == "Circle"]
    for rr in (r * s, r):
        for i, rad in circ:
            if abs(rad - rr) < VTOL * max(1.0, s):
                return f"Edge{i}"
    return None


def _line(v, length, s):
    for ll in (length * s, length):
        for i, e in _edges(v):
            if _tn(getattr(e, "Curve", None)) not in ("Line", "LineSegment"):
                continue
            p0, p1 = e.Vertexes[0].Point, e.Vertexes[-1].Point
            if abs(p0.y - p1.y) < 1e-6 and abs(abs(p1.x - p0.x) - ll) < VTOL * max(1.0, s):
                return f"Edge{i}"
    return None


def _dim(doc, page, pid, v, ref, typ, fmt):
    d = doc.addObject("TechDraw::DrawViewDimension", "Dimension")
    d.Type = typ
    d.References2D = [(v, ref)]
    if "MeasureType" in d.PropertiesList:
        d.MeasureType = "Projected"
    d.FormatSpec = fmt
    page.addView(d)
    _mark(d, pid)


def _cosmetic(v, r):
    """Косметическая окружность вокруг оси (DВ, Dверш, Dотв) — масштаб API: OQ-20."""
    try:
        v.makeCosmeticCircle(App.Vector(0, 0, 0), r)
        return True
    except Exception:
        return False


def _legend(doc, page, pid, rec, rows, pos, grp):
    rows = [["Обозначение", "Значение", "Источник", "Смысл — колонки SPEC-10 / SPEC-11"]] + rows
    sh = doc.addObject("Spreadsheet::Sheet", "Legend")
    sh.Label = f"LEGEND {rec['label']}"
    grp.addObject(sh)
    _mark(sh, pid)
    for i, row in enumerate(rows, 1):
        for col, val in zip("ABCD", row):
            sh.set(f"{col}{i}", "'" + str(val))
    sh.recompute()
    v = doc.addObject("TechDraw::DrawViewSpreadsheet", "LegendView")
    v.Source = sh
    v.CellStart, v.CellEnd = "A1", f"D{len(rows)}"
    if "TextSize" in v.PropertiesList:
        v.TextSize = 3.0
    page.addView(v)
    v.X, v.Y = pos
    _mark(v, pid)


def _text(doc, page, pid, name, lines, pos, red=False):
    a = doc.addObject("TechDraw::DrawViewAnnotation", name)
    a.Text = lines
    a.TextSize = 3.5
    if red and "TextColor" in a.PropertiesList:
        a.TextColor = (1.0, 0.0, 0.0)
    page.addView(a)
    a.X, a.Y = pos
    _mark(a, pid)


def _stem(path):
    return re.sub(r"\.assy\.json$", "", path)


def _pdf(page, path, rec):
    if not App.GuiUp:
        return None
    try:
        import TechDrawGui
        out = _stem(path) + "-" + re.sub(r"[^\w.-]+", "_", rec["label"]).strip("_") + ".pdf"
        TechDrawGui.exportPageAsPdf(page, out)
        return out
    except Exception as e:
        App.Console.PrintWarning(f"EGM TechDraw: PDF {page.Label} не записан: {e}\n")
        return None


def _one(TD, doc, grp, tpl, pid, rec, shape, path, pdf):
    meas = measure(shape, rec["checks"])
    res = TD.compare(rec["checks"], meas, rec.get("tol", TD.TOL))
    bb = shape.BoundBox
    sh = TD.layout(max(bb.XLength, bb.YLength), bb.ZLength, rec["page"].get("scales"))
    src = doc.addObject("Part::Feature", "DrwSrc")
    src.Label = f"SRC {rec['label']}"
    src.Shape = shape
    src.Visibility = False
    grp.addObject(src)
    _mark(src, pid)
    page = _page(doc, pid, rec, sh, tpl)
    views = {k: _view(doc, page, pid, src, k, sh["views"][k]) for k in ("front", "side", "iso")}
    doc.recompute()
    s, put, noedge = sh["scale"], 0, []
    for r in res:
        v = r["step"]
        if v is None or isinstance(v, list):
            continue
        if r["kind"] in TD.ON_VIEW:
            ref = _circle(views["front"], v / 2, s)
            if ref:
                _dim(doc, page, pid, views["front"], ref, "Diameter", f"{r['sym']} ⌀%.2f")
                put += 1
            else:
                noedge.append(r["sym"])
        elif r["kind"] in TD.COSMETIC:
            if _cosmetic(views["front"], v / 2):
                put += 1
            else:
                noedge.append(r["sym"])
        elif r["kind"] == "length":
            ref = _line(views["side"], v, s)
            if ref:
                _dim(doc, page, pid, views["side"], ref, "DistanceX", f"{r['sym']} %.2f")
                put += 1
            else:
                noedge.append(r["sym"])
    _legend(doc, page, pid, rec, TD.legend_rows(rec, res), sh["legend"], grp)
    _text(doc, page, pid, "Notes", [f"{pid} — {rec['name']}", f"масштаб {sh['scale_txt']}",
                                    "размеры и значения «3D» — измерены по STEP (Д-65)"]
          + rec["notes"], sh["notes"])
    warn = TD.warnings(res)
    if warn:
        _text(doc, page, pid, "Warn", ["ПРЕДУПРЕЖДЕНИЯ: 3D (STEP) ≠ .assy.json (Д-65)"] + warn,
              sh["warn"], red=True)
    doc.recompute()
    out = _pdf(page, path, rec) if pdf else None
    head = (f"лист «{page.Label}», {rec['page']['format']} {sh['scale_txt']}; на листе {put}; "
            f"предупреждений {len(warn)}; без кромки на виде: {', '.join(noedge) or '—'}"
            + (f"; PDF {os.path.basename(out)}" if out else ""))
    return head, TD.md_table(res)


def _report(path, data, rep):
    out = _stem(path) + ".techdraw.md"
    lines = [f"# Чертежи TechDraw {data.get('id', '')} (Д-65; пишет макрос, НЕ ПРАВИТЬ РУКАМИ)",
             "", f"Источник геометрии: STEP; эталоны: {os.path.basename(path)} → drawings", ""]
    for pid, lab, head, table in rep:
        lines += [f"## {pid} — {lab}", "", head, ""] + table + [""]
        App.Console.PrintMessage(f"EGM TechDraw: {lab}: {head}\n")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    App.Console.PrintMessage(f"EGM TechDraw: {len(rep)} позиций, отчёт {out}\n")


def apply(path, doc=None, pdf=True):
    doc = doc or App.ActiveDocument
    TD = _td(path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    drw = data.get("drawings") or {}
    if not drw:
        App.Console.PrintError("EGM TechDraw: в .assy.json нет drawings — пересоздать: "
                               "python -m egm.cad <ID> --assy (CP-55)\n")
        return []
    _clear(doc)
    grp = doc.getObject(GROUP) or doc.addObject("App::DocumentObjectGroup", GROUP)
    src = _sources(doc, {r["label"] for r in drw.values() if "label" in r})
    tpl = _template()
    if tpl is None:
        App.Console.PrintWarning("EGM TechDraw: шаблон A3 не найден — листы без рамки\n")
    rep = []
    for pid, rec in drw.items():
        lab = rec.get("label", pid)
        if "error" in rec:
            rep.append((pid, lab, "пропущен: " + rec["error"], []))
        elif lab not in src:
            rep.append((pid, lab, "пропущен: нет объекта с такой меткой в документе", []))
        else:
            try:
                head, table = _one(TD, doc, grp, tpl, pid, rec, src[lab], path, pdf)
            except Exception as e:
                head, table = f"ошибка: {type(e).__name__}: {e}", []
            rep.append((pid, lab, head, table))
    _report(path, data, rep)
    return rep


def run():
    from PySide import QtGui
    path = QtGui.QFileDialog.getOpenFileName(None, "EGM TechDraw: <ID>.assy.json", "",
                                             "assy (*.assy.json)")[0]
    if path:
        apply(path)


if __name__ == "__main__":
    run()
