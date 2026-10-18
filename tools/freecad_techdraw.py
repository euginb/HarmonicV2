"""Макрос FreeCAD (Д-65, Д-66): чертежи деталей TechDraw из 3D-геометрии STEP.

Виды — проекции формы детали из открытого <ID>.step; размеры на видах и геометрические
значения легенды измеряются по этой же форме: сечение плоскостью z (наружный, внутренний
контур, отверстия, окна), цилиндрические грани, BoundBox. Из <ID>.assy.json → drawings —
эталоны сверки, обозначения и смысл колонок SPEC-10/SPEC-11, неизмеримые величины,
примечания, ряд масштабов. Расхождение или неизмеренный размер — красный блок на листе
и строка в <ID>.techdraw.md.
Лист (Д-66): шаблон A3 <ID>.A3.svg, зоны, легенда/примечания/предупреждения как SVG-символы —
egm/cad/techdraw_sheet.py; Spreadsheet/LegendView и аннотации не создаются. Размеры: D,
Ø цилиндров и отверстий — на кромках вида по оси; DВ, Dверш, Dотв — на технических
(косметических) окружностях радиусом, измеренным по 3D; толщина/длина — на виде сбоку.
Штатный запуск — tools/freecad_egm.py. Отдельно: открыть <ID>.step, Макрос → этот файл →
выбрать <ID>.assy.json. Повторный запуск пересоздаёт листы (объекты со свойством egm_drw).
"""
import datetime
import importlib
import json
import math
import os
import re
import sys

import FreeCAD as App
import Part

GROUP = "EGM_TechDraw"
TAG = "egm_drw"
DIRS = {"front": ((0, 0, 1), (1, 0, 0)),
        "side": ((0, -1, 0), (0, 0, 1)),
        "iso": ((1, -1, 1), (1, 1, 0))}
VTOL = 0.05                                     # допуск поиска кромки на виде, мм
STYLE = {"d_root": 2, "d_tip": 2, "d_bc": 4}    # LineStyle: 2 — штрих, 4 — штрихпунктир
ANGLES = (45, 135, 225, 315, 20, 160, 200, 340)  # углы выносок диаметров на виде по оси
MAX_EDGES = 20000


def _repo(path):
    starts = [os.path.dirname(os.path.abspath(path))]
    if "__file__" in globals():
        starts.insert(0, os.path.dirname(os.path.abspath(__file__)))
    for d in starts:
        while True:
            if os.path.exists(os.path.join(d, "egm", "cad", "techdraw_sheet.py")):
                return d
            up = os.path.dirname(d)
            if up == d:
                break
            d = up
    raise ImportError("не найден egm/cad/techdraw_sheet.py выше " + path)


def _td(path):
    """egm/cad/techdraw.py и techdraw_sheet.py из репозитория (reload — правки без перезапуска)."""
    root = _repo(path)
    if root not in sys.path:
        sys.path.insert(0, root)
    from egm.cad import techdraw, techdraw_sheet
    techdraw = importlib.reload(techdraw)
    return techdraw, importlib.reload(techdraw_sheet)


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


def _ns(default):
    """Пространство имён freecad: из установленных шаблонов TechDraw (версии FreeCAD различаются)."""
    base = os.path.join(App.getResourceDir(), "Mod", "TechDraw", "Templates")
    for root, _, files in os.walk(base):
        for f in sorted(files):
            if not f.endswith(".svg"):
                continue
            try:
                with open(os.path.join(root, f), encoding="utf-8") as fh:
                    m = re.search(r'xmlns:freecad="([^"]+)"', fh.read(4000))
            except Exception:
                continue
            if m:
                return m.group(1)
    return default


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


# == измерение по 3D ==
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


def _split(ws):
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


def _section(shape, z):
    """Сечение z: slice; нет внутреннего контура (сплайн впадин) — section + sortEdges."""
    ws = shape.slice(App.Vector(0, 0, 1), z)
    sec = _split(ws) if ws else None
    if sec is None or sec["inner"] is None:
        L = 4 * shape.BoundBox.DiagonalLength
        pl = Part.makePlane(L, L, App.Vector(-L / 2, -L / 2, z))
        cross = shape.section(pl)
        ws2 = []
        for grp in Part.sortEdges(cross.Edges):
            try:
                ws2.append(Part.Wire(grp))
            except Exception:
                pass
        if ws2:
            s2 = _split(ws2)
            if sec is None or (s2["inner"] is not None):
                sec = s2
    if sec is None:
        raise ValueError(f"сечение z = {z:g} пустое")
    return sec


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


# == лист ==
def _page(doc, pid, rec, sh, tpl_path, fields):
    page = doc.addObject("TechDraw::DrawPage", "Page")
    page.Label = f"DRW {rec['label']}"
    _mark(page, pid)
    tpl = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
    tpl.Template = tpl_path
    page.Template = tpl
    _mark(tpl, pid)
    try:
        t = dict(tpl.EditableTexts)
        for k in t:
            if k in fields:
                t[k] = fields[k]
        tpl.EditableTexts = t
    except Exception as e:
        App.Console.PrintWarning(f"EGM TechDraw: основная надпись не заполнена: {e}\n")
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


def _symbol(doc, page, pid, b, scale):
    s = doc.addObject("TechDraw::DrawViewSymbol", b["name"])
    s.Symbol = b["svg"]
    page.addView(s)
    if "Scale" in s.PropertiesList:
        s.ScaleType = "Custom"
        s.Scale = scale
    s.X, s.Y = b["x"], b["y"]
    _mark(s, pid)


def _edges(v):
    """[(«EdgeN», кромка)] в нумерации ссылок размеров (getEdgeByIndex), с косметикой."""
    out = []
    for i in range(MAX_EDGES):
        try:
            e = v.getEdgeByIndex(i)
        except Exception:
            break
        if e is None:
            break
        out.append((f"Edge{i}", e))
    return out


def _circle(v, r, s, used=()):
    circ = [(n, e.Curve.Radius) for n, e in _edges(v)
            if _tn(getattr(e, "Curve", None)) == "Circle" and n not in used]
    for rr in (r * s, r):
        for n, rad in circ:
            if abs(rad - rr) < VTOL * max(1.0, s):
                return n
    return None


def _line(v, length, s):
    for ll in (length * s, length):
        for n, e in _edges(v):
            if _tn(getattr(e, "Curve", None)) not in ("Line", "LineSegment"):
                continue
            p0, p1 = e.Vertexes[0].Point, e.Vertexes[-1].Point
            if abs(p0.y - p1.y) < 1e-6 and abs(abs(p1.x - p0.x) - ll) < VTOL * max(1.0, s):
                return n
    return None


def _dim(doc, page, pid, v, ref, typ, fmt, k, s, r):
    d = doc.addObject("TechDraw::DrawViewDimension", "Dimension")
    d.Type = typ
    d.References2D = [(v, ref)]
    if "MeasureType" in d.PropertiesList:
        d.MeasureType = "Projected"
    d.FormatSpec = fmt
    page.addView(d)
    if typ == "Diameter":                       # выноски по кругу, чтобы тексты не сходились
        a = math.radians(ANGLES[k % len(ANGLES)])
        d.X, d.Y = (r * s + 8.0) * math.cos(a), (r * s + 8.0) * math.sin(a)
    else:
        d.X, d.Y = 0.0, -(r * s / 2 + 8.0)
    if App.GuiUp:
        try:
            d.ViewObject.Font = "Arial"
            d.ViewObject.Fontsize = 3.5
        except Exception:
            pass
    _mark(d, pid)


def _cosmetic(v, r, style):
    """Техническая окружность вокруг оси радиусом r (мм детали) — OQ-20: система координат."""
    try:
        tag = v.makeCosmeticCircle(App.Vector(0, 0, 0), r)
    except Exception:
        return False
    try:
        ce = v.getCosmeticEdge(tag)
        fmt = ce.Format
        fmt.Style = style
        ce.Format = fmt
    except Exception:
        pass
    return True


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


WAIT_S = 180.0                                  # предел ожидания HLR видов листа, с (Д-70)


def _ready(v):
    """У вида есть проекция (HLR TechDraw — в фоновом потоке, Д-70)."""
    try:
        return v.getEdgeByIndex(0) is not None
    except Exception:
        return False


def _coarse(v):
    """Запасной HLR (Д-70): полигональная проекция, если точная не пришла за WAIT_S."""
    try:
        v.CoarseView = True
        return True
    except Exception:
        return False


def _wait(views, timeout=WAIT_S, times=None, t0=None):
    """recompute() возвращается раньше фонового HLR (Д-70). Ждём кромки у видов,
    прокачивая очередь Qt; times[k] — секунды от t0 до готовности вида k (Д-71);
    возвращает (виды без геометрии, секунды ожидания)."""
    import time
    try:
        from PySide import QtCore
        pump = QtCore.QCoreApplication.processEvents
    except Exception:
        def pump():
            return None
    start = time.time()
    t0 = start if t0 is None else t0
    left = [k for k, v in views.items() if v is not None]
    while True:
        pump()
        still = []
        for k in left:
            if _ready(views[k]):
                if times is not None:
                    times[k] = time.time() - t0
            else:
                still.append(k)
        left = still
        if not left or time.time() - start > timeout:
            return left, time.time() - start
        time.sleep(0.1)


HEAVY_FACES = 300           # граней больше — вид по оси строится по слою 3D (Д-71)
SLAB_H = 0.5                # полутолщина слоя, мм


def _free_z(rec):
    """z сечения без окон и ступеней — из эталона «центр D» (Д-65)."""
    for c in rec["checks"]:
        if c.get("kind") == "center" and c.get("z") is not None:
            return c["z"]
    return None


def _slab(shape, z, h=SLAB_H):
    """Слой формы z ± h — источник вида по оси у тяжёлых деталей (Д-71). По оси кромки
    сотен окон сепаратора вырождаются на окружности стенки: HLR не даёт геометрии
    (InsertKnots), а смысла в них на этом виде нет. Слой — часть той же формы STEP."""
    bb = shape.BoundBox
    z0, z1 = max(bb.ZMin, z - h), min(bb.ZMax, z + h)
    if z1 - z0 < 1e-3:
        return None
    L = 2 * bb.DiagonalLength
    c = bb.Center
    box = Part.makeBox(L, L, z1 - z0, App.Vector(c.x - L / 2, c.y - L / 2, z0))
    try:
        sl = shape.common(box)
    except Exception:
        return None
    return sl if not sl.isNull() and sl.Solids else None


def _src(doc, grp, pid, label, shape):
    o = doc.addObject("Part::Feature", "DrwSrc")
    o.Label = label
    o.Shape = shape
    o.Visibility = False
    grp.addObject(o)
    _mark(o, pid)
    return o


def _span(v, length, s):
    """Длина по крайним вершинам вида (Д-71): у сепаратора образующая разорвана окнами,
    цельной кромки длиной L нет. Возвращает пару («VertexI», «VertexJ») или None."""
    pts = []
    for i in range(MAX_EDGES):
        try:
            p = v.getVertexByIndex(i)
        except Exception:
            break
        if p is None:
            break
        pts.append((f"Vertex{i}", p.Point))
    if len(pts) < 2:
        return None
    a = min(pts, key=lambda t: (t[1].x, -t[1].y))
    b = max(pts, key=lambda t: (t[1].x, t[1].y))
    for ll in (length * s, length):
        if abs(abs(b[1].x - a[1].x) - ll) < VTOL * max(1.0, s):
            return a[0], b[0]
    return None


def _dim_span(doc, page, pid, v, refs, fmt, s, r):
    """Размер DistanceX по двум вершинам (Д-71)."""
    d = doc.addObject("TechDraw::DrawViewDimension", "Dimension")
    d.Type = "DistanceX"
    d.References2D = [(v, n) for n in refs]
    if "MeasureType" in d.PropertiesList:
        d.MeasureType = "Projected"
    d.FormatSpec = fmt
    page.addView(d)
    d.X, d.Y = 0.0, -(r * s / 2 + 8.0)
    if App.GuiUp:
        try:
            d.ViewObject.Font = "Arial"
            d.ViewObject.Fontsize = 3.5
        except Exception:
            pass
    _mark(d, pid)


def _start(TD, TS, doc, grp, tpl, pid, rec, shape):
    """Проход 1 (Д-71): замеры по 3D, лист и виды без размеров. HLR не ждём —
    он запускается общим recompute для всех листов сразу (_run)."""
    meas = measure(shape, rec["checks"])
    res = TD.compare(rec["checks"], meas, rec.get("tol", TD.TOL))
    warn = TD.warnings(res)
    bb = shape.BoundBox
    notes = [n for n in rec["notes"]] + ["размеры и значения «3D» измерены по STEP (Д-65)"]
    src = _src(doc, grp, pid, f"SRC {rec['label']}", shape)
    srcs, z = {}, _free_z(rec)
    if len(shape.Faces) > HEAVY_FACES and z is not None:
        sl = _slab(shape, z)
        if sl is not None:
            srcs["front"] = _src(doc, grp, pid, f"SRC {rec['label']} z{z:g}", sl)
            notes.append(f"вид по оси — слой 3D z = {z:g} ± {SLAB_H:g} мм, окна на нём "
                         f"не показаны (Д-71)")
    sh = TS.layout(max(bb.XLength, bb.YLength), bb.ZLength, TD.legend_rows(rec, res),
                   notes, warn, rec["page"].get("scales"))
    fields = TS.title_fields(pid, rec, sh, datetime.date.today().strftime("%d.%m.%y"))
    page = _page(doc, pid, rec, sh, tpl, fields)
    views = {k: _view(doc, page, pid, srcs.get(k, src), k, p) for k, p in sh["views"].items() if p}
    return {"pid": pid, "rec": rec, "res": res, "warn": warn, "sh": sh, "page": page,
            "views": views, "slab": "front" in srcs,
            "head": "ошибка: лист не завершён", "table": TD.md_table(res)}


def _guard(j, fn):
    try:
        fn()
    except Exception as e:
        j["error"] = f"{type(e).__name__}: {e}"


def _legend(TS, doc, j):
    for b in j["sh"]["blocks"]:
        _symbol(doc, j["page"], j["pid"], b, TS.SYM_SCALE)


def _cosmetics(TD, j, late):
    front = j["views"]["front"]
    cos = [r for r in j["res"] if r["kind"] in TD.COSMETIC
           and not isinstance(r["step"], (list, str)) and r["step"] is not None]
    j["nocos"] = [r["sym"] for r in cos if (j["pid"], "front") in late
                  or not _cosmetic(front, r["step"] / 2, STYLE[r["kind"]])]


def _dims(TD, doc, j):
    page, pid, sh, views = j["page"], j["pid"], j["sh"], j["views"]
    front, s = views["front"], sh["scale"]
    put, noedge, used, k = 0, [], set(), 0
    for r in j["res"]:
        v = r["step"]
        if v is None or isinstance(v, (list, str)):
            continue
        if r["kind"] in TD.ON_VIEW or r["kind"] in TD.COSMETIC:
            ref = _circle(front, v / 2, s, used)
            if ref:
                used.add(ref)
                txt = f"{r['sym']}" if r["kind"] != "d_hole" else f"отв. {r['sym']}"
                _dim(doc, page, pid, front, ref, "Diameter", f"⌀%.2f ({txt})", k, s, v / 2)
                put, k = put + 1, k + 1
            else:
                noedge.append(r["sym"])
        elif r["kind"] == "length" and "side" in views:
            ref = _line(views["side"], v, s)
            if ref:
                _dim(doc, page, pid, views["side"], ref, "DistanceX", f"%.2f ({r['sym']})",
                     0, s, sh["d"] / 2)
                put += 1
                continue
            refs = _span(views["side"], v, s)
            if refs:
                _dim_span(doc, page, pid, views["side"], refs, f"%.2f ({r['sym']})",
                          s, sh["d"] / 2)
                put += 1
            else:
                noedge.append(r["sym"])
    j["put"], j["noedge"] = put, noedge


def _head(j, out, times, coarse, late):
    pid, sh = j["pid"], j["sh"]
    c = [k for p, k in coarse if p == pid]
    lt = [k for p, k in late if p == pid]
    t = max([times.get((pid, k), 0.0) for k in j["views"]] or [0.0])
    return (f"лист «{j['page'].Label}», A3 {sh['scale_txt']}; размеров на листе {j.get('put', 0)}; "
            f"предупреждений {len(j['warn'])}; без кромки на виде: "
            f"{', '.join(j.get('noedge', [])) or '—'}"
            f"; HLR {t:.1f} с" + (f" (грубый: {', '.join(c)})" if c else "")
            + (f"; без геометрии видов: {', '.join(lt)}" if lt else "")
            + ("; вид по оси — слой z (Д-71)" if j["slab"] else "")
            + (f"; косметика не добавлена: {', '.join(j['nocos'])}" if j.get("nocos") else "")
            + (f"; компоновка: {'; '.join(sh['overflow'])}" if sh["overflow"] else "")
            + (f"; ошибка: {j['error']}" if j.get("error") else "")
            + (f"; PDF {os.path.basename(out)}" if out else ""))


def _run(TD, TS, doc, jobs, path, pdf):
    """Проходы 2–4 (Д-71): один recompute запускает HLR всех видов всех листов; пока он
    идёт — легенды и примечания; затем общее ожидание, косметика, размеры, PDF."""
    import time
    t0 = time.time()
    doc.recompute()
    for j in jobs:
        _guard(j, lambda: _legend(TS, doc, j))
    allv = {(j["pid"], k): v for j in jobs for k, v in j["views"].items()}
    times = {}
    late, _ = _wait(allv, WAIT_S, times, t0)
    coarse = [key for key in late if _coarse(allv[key])]
    if coarse:
        doc.recompute()
        late, _ = _wait({key: allv[key] for key in late}, 60.0, times, t0)
    for j in jobs:
        _guard(j, lambda: _cosmetics(TD, j, late))
    doc.recompute()
    _wait({key: v for key, v in allv.items() if key not in late}, 60.0)
    for j in jobs:
        _guard(j, lambda: _dims(TD, doc, j))
    doc.recompute()
    for j in jobs:
        out = _pdf(j["page"], path, j["rec"]) if pdf else None
        j["head"] = _head(j, out, times, coarse, late)
        j["table"] = TD.md_table(j["res"])


def _report(path, data, rep):
    out = _stem(path) + ".techdraw.md"
    lines = [f"# Чертежи TechDraw {data.get('id', '')} (Д-65, Д-66; пишет макрос, НЕ ПРАВИТЬ РУКАМИ)",
             "", f"Источник геометрии: STEP; эталоны: {os.path.basename(path)} → drawings", ""]
    for pid, lab, head, table in rep:
        lines += [f"## {pid} — {lab}", "", head, ""] + table + [""]
        App.Console.PrintMessage(f"EGM TechDraw: {lab}: {head}\n")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    App.Console.PrintMessage(f"EGM TechDraw: {len(rep)} позиций, отчёт {out}\n")


def apply(path, doc=None, pdf=True):
    doc = doc or App.ActiveDocument
    if doc is None:
        raise RuntimeError("нет открытого документа: открыть <ID>.step или запустить "
                           "tools/freecad_egm.py (откроет STEP сам)")
    TD, TS = _td(path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    drw = data.get("drawings") or {}
    if not drw:
        App.Console.PrintError("EGM TechDraw: в .assy.json нет drawings — пересоздать: "
                               "python -m egm.cad <ID> --assy (CP-55)\n")
        return []
    _clear(doc)
    tpl = _stem(path) + ".A3.svg"
    with open(tpl, "w", encoding="utf-8", newline="\n") as f:
        f.write(TS.template_svg(_ns(TS.NS)))
    grp = doc.getObject(GROUP) or doc.addObject("App::DocumentObjectGroup", GROUP)
    src = _sources(doc, {r["label"] for r in drw.values() if "label" in r})
    miss = sorted({r["label"] for r in drw.values() if "label" in r} - set(src))
    if miss:
        have = sorted({_strip(o.Label) for o in doc.Objects})
        App.Console.PrintWarning("EGM TechDraw: нет формы для меток: " + ", ".join(miss)
                                 + "\n  метки в документе (первые 30): " + ", ".join(have[:30]) + "\n")
    rep, jobs = [], []
    for pid, rec in drw.items():
        lab = rec.get("label", pid)
        if "error" in rec:
            rep.append((pid, lab, "пропущен: " + rec["error"], []))
        elif lab not in src:
            rep.append((pid, lab, "пропущен: нет объекта с такой меткой в документе", []))
        else:
            try:
                jobs.append(_start(TD, TS, doc, grp, tpl, pid, rec, src[lab]))
                rep.append((pid, lab, None, []))
            except Exception as e:
                rep.append((pid, lab, f"ошибка: {type(e).__name__}: {e}", []))
    _run(TD, TS, doc, jobs, path, pdf)
    done = {j["pid"]: j for j in jobs}
    rep = [(p, lab, done[p]["head"], done[p]["table"]) if h is None else (p, lab, h, t)
           for p, lab, h, t in rep]
    _report(path, data, rep)
    _show(doc)
    return rep


def _show(doc):
    """Открыть первый лист во вкладке: иначе листы есть только в дереве (DRW …)."""
    if not App.GuiUp:
        return
    pg = next((o for o in doc.Objects if o.TypeId == "TechDraw::DrawPage"
               and TAG in o.PropertiesList), None)
    if pg is not None:
        try:
            pg.ViewObject.doubleClicked()
        except Exception:
            pass


def summary(path, rep):
    """Итог для окна сообщения: сколько листов, где отчёт, что не построено."""
    bad = [f"{lab}: {head}" for _, lab, head, _ in rep if head.startswith(("пропущен", "ошибка"))]
    return (f"Чертежей: {len(rep) - len(bad)} из {len(rep)}; листы — объекты «DRW …» в дереве.\n"
            f"Отчёт: {_stem(path)}.techdraw.md"
            + (("\nНе построены:\n" + "\n".join(bad[:10])) if bad else ""))


def box(title, text, error=False):
    """Сообщение в Report view и окном — результат виден, даже если панель отчёта закрыта."""
    (App.Console.PrintError if error else App.Console.PrintMessage)(text + "\n")
    if App.GuiUp:
        try:
            from PySide import QtGui
            (QtGui.QMessageBox.critical if error else QtGui.QMessageBox.information)(
                None, title, text)
        except Exception:
            pass


def run():
    from PySide import QtGui
    App.Console.PrintMessage(f"EGM TechDraw: старт (__name__ = {__name__}, FreeCAD "
                             f"{'.'.join(App.Version()[:3])}, Python {sys.version.split()[0]})\n")
    path = QtGui.QFileDialog.getOpenFileName(None, "EGM TechDraw: <ID>.assy.json", "",
                                             "assy (*.assy.json)")[0]
    if not path:
        App.Console.PrintMessage("EGM TechDraw: файл не выбран\n")
        return
    try:
        rep = apply(path)
    except Exception:
        import traceback
        box("EGM TechDraw — ошибка", traceback.format_exc(), True)
        return
    box("EGM TechDraw", summary(path, rep))


if __name__ != "freecad_techdraw":         # макрос FreeCAD (Д-66); при импорте из freecad_egm — нет
    run()
