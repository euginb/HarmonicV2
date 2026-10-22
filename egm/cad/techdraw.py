"""Чертежи деталей во FreeCAD TechDraw (Д-65): правила листа без FreeCAD.

Геометрия чертежа — только из 3D (STEP): виды проецирует TechDraw, размеры и габарит
измеряет макрос tools/freecad_techdraw.py по форме детали. Здесь — то, что из формы не
измерить, и правила, общие для макроса и прогона main.py:
  record()      — запись drawings[<ID детали>] для <ID>.assy.json: эталоны проверок (checks)
                  из PartModel (Д-32), легенда (обозначения колонок SPEC-10/SPEC-11, смысл,
                  расчётные значения), примечания, формат, ряд масштабов, допуск;
  layout()      — масштаб ГОСТ 2.302 и положения видов по габариту ФОРМЫ из STEP;
  compare()     — сверка измеренного по 3D с эталоном -> предупреждения на листе;
  legend_rows() — легенда: геометрические значения — измеренные, прочие — из .assy.json.
Без внешних зависимостей: макрос импортирует модуль из репозитория (Python FreeCAD).
Координаты листа — мм от левого нижнего угла, Y вверх; X, Y вида — его центр (OQ-20).
"""
import math

SHEET = ("A3", 420.0, 297.0)              # формат, ширина, высота — альбомный
SCALES = (10.0, 5.0, 2.0, 1.0, 0.5, 0.2)  # ГОСТ 2.302: 10:1 … 1:5, по убыванию
TOL = 0.01                                # допуск сверки 3D / расчёт, мм
MARGIN, GAP = 15.0, 25.0                  # поле листа и промежуток между видами, мм
AREA_W, AREA_H = 250.0, 180.0             # поле видов по оси и сбоку
ISO_MAX = 100.0                           # наибольший размер ISO-вида на листе, мм
POS = {"legend": (345.0, 200.0), "iso": (345.0, 70.0), "notes": (115.0, 272.0),
       "warn": (115.0, 35.0)}
THICK = {"01": "B", "02": "B", "03": "t", "05": "h", "07": "t", "11": "h"}
LABEL_KIND = {"D": "d_out", "Dотв": "d_bc", "DВ": "d_root", "Dверш": "d_tip"}
KINDS = {"d_out": "наружный Ø: контур сечения",
         "center": "смещение центра наружного контура, мм",
         "d_root": "2·max ρ внутреннего контура сечения",
         "d_tip": "2·min ρ внутреннего контура сечения",
         "d_bc": "2·средний ρ центров отверстий сечения",
         "d_hole": "Ø отверстий сечения",
         "n_holes": "число отверстий в сечении",
         "holes_xy": "наибольшее смещение центров отверстий, мм",
         "d_cyl": "Ø ближайшей цилиндрической грани",
         "length": "габарит по оси z",
         "windows": "число окон в сечении ряда",
         "n_pins": "число радиальных отверстий (оси ⟂ z)",
         "d_pin": "Ø радиальных отверстий",
         "pin_z": "z осей радиальных отверстий, мм"}
ON_VIEW = ("d_out", "d_hole", "d_cyl")    # есть кромка-окружность на виде по оси
COSMETIC = ("d_root", "d_tip", "d_bc")    # кромки нет — косметическая окружность
COUNT = ("n_holes", "windows", "n_pins")
NOGEO = ("center", "holes_xy")            # проверки без строки легенды


def _fmt(v):
    if isinstance(v, float):
        v = round(v, 3)
    return f"{v:g}" if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v)


def _val(v):
    if isinstance(v, (list, tuple)):
        return "(" + "; ".join(_fmt(float(x)) for x in v) + ")"
    return _fmt(v)


def _r(v):
    return round(float(v), 4)


def scale_txt(s):
    """2.0 -> «2:1», 0.5 -> «1:2»."""
    return f"{s:g}:1" if s >= 1 else f"1:{1 / s:g}"


def extent(m):
    """Габарит детали по PartModel -> (Ø, z0, z1): основное тело и ступени Band add;
    вырезы (Band cut, окна) габарит не увеличивают (Д-66)."""
    add = [b for b in m.bands if b.op == "add"]
    zs = [0.0, m.thick] + [z for b in add for z in (b.z0, b.z0 + b.h)]
    d = max([m.d_out] + [2 * b.r_out for b in add])
    return d, min(zs), max(zs)


def free_z(m):
    """z сечения основного тела без окон и ступеней — середина наибольшего свободного
    промежутка в [0, thick]; нет такого — thick/2."""
    busy = sorted([(w.z0, w.z0 + w.h) for w in m.windows] + [(b.z0, b.z0 + b.h) for b in m.bands]
                  + [(p.z - p.d / 2, p.z + p.d / 2) for p in m.pins])
    gaps, cur = [], 0.0
    for a, b in busy:
        if a > cur:
            gaps.append((cur, min(a, m.thick)))
        cur = max(cur, b)
    if cur < m.thick:
        gaps.append((cur, m.thick))
    gaps = [g for g in gaps if g[1] - g[0] > 1e-3]
    if not gaps:
        return m.thick / 2
    a, b = max(gaps, key=lambda g: g[1] - g[0])
    return (a + b) / 2


def _kind(m, d, rho, bc):
    """Вид проверки размера без обозначения в LABEL_KIND — по совпадению с моделью."""
    if abs(d - m.d_out) < TOL / 2:
        return "d_out"
    if bc is not None and abs(d - bc) < TOL / 2:
        return "d_bc"
    if rho and abs(d - 2 * max(rho)) < 0.05:
        return "d_root"
    if rho and abs(d - 2 * min(rho)) < 0.05:
        return "d_tip"
    if any(abs(d - h.d) < TOL / 2 for h in m.holes):
        return "d_hole"
    return "d_cyl"


def checks(m, nn):
    """Эталоны проверок 3D из PartModel: {"sym", "kind", "value", "z"[, "ref"]};
    z — сечение формы (None — без сечения: длина, цилиндрические грани)."""
    zs = _r(free_z(m))
    rho = [math.hypot(x, y) for x, y in (m.cut.pts if m.cut else [])]
    hr = [math.hypot(h.x, h.y) for h in m.holes]
    bc = 2 * sum(hr) / len(hr) if hr and max(hr) - min(hr) < TOL else None
    out = []
    for dm in m.dims:
        k = LABEL_KIND.get(dm.label) or _kind(m, dm.d, rho, bc)
        out.append({"sym": dm.label, "kind": k, "value": _r(dm.d),
                    "z": None if k == "d_cyl" else zs})
    if "d_out" not in {c["kind"] for c in out}:
        out.append({"sym": "D", "kind": "d_out", "value": _r(m.d_out), "z": zs})
    out.append({"sym": "центр D", "kind": "center", "value": [_r(m.cx[0]), _r(m.cx[1])], "z": zs})
    if m.holes:
        out.append({"sym": "n отв", "kind": "n_holes", "value": len(m.holes), "z": zs})
        for d in sorted({_r(h.d) for h in m.holes}):
            if not any(c["kind"] == "d_hole" and abs(c["value"] - d) < 1e-6 for c in out):
                out.append({"sym": f"Ø отв {d:g}", "kind": "d_hole", "value": d, "z": zs})
        out.append({"sym": "отв xy", "kind": "holes_xy", "value": 0.0, "z": zs,
                    "ref": [[_r(h.x), _r(h.y)] for h in m.holes]})
    if m.pins:                                    # CP-63: радиальные отверстия штифтов (Д-76)
        out.append({"sym": "n шт", "kind": "n_pins", "value": len(m.pins), "z": None})
        for d in sorted({_r(p.d) for p in m.pins}):
            out.append({"sym": f"Ø шт {d:g}", "kind": "d_pin", "value": d, "z": None})
        out.append({"sym": "z шт", "kind": "pin_z", "z": None,
                    "value": _r(sum(p.z for p in m.pins) / len(m.pins))})
    _, z0, z1 = extent(m)
    sym = THICK.get(nn, "B") if abs((z1 - z0) - m.thick) < 1e-9 else "L"
    out.append({"sym": sym, "kind": "length", "value": _r(z1 - z0), "z": None})
    rows = {}
    for w in m.windows:
        rows.setdefault((_r(w.z0), _r(w.h)), []).append(w)
    for (wz, wh), ws in sorted(rows.items()):
        zc = _r(wz + wh / 2)
        out.append({"sym": f"окна z {zc:g}", "kind": "windows", "value": len(ws), "z": zc})
    return out


def record(pid, nn, m, label, name):
    """Запись drawings[pid] для .assy.json из PartModel m (геометрию листа даёт STEP)."""
    notes = list(m.notes)
    if m.view == "unroll":
        notes.append("развёртка втулки — только в SVG (Д-47); здесь виды по оси, сбоку, ISO")
    return {"label": label, "name": name, "nn": nn, "tol": TOL,
            "page": {"format": SHEET[0], "size": [SHEET[1], SHEET[2]], "scales": list(SCALES)},
            "checks": checks(m, nn),
            "legend": [[str(sy), _fmt(v), str(t)] for sy, v, t in m.legend],
            "notes": notes}


def pick_scale(d, l, scales=SCALES):
    """Наибольший масштаб, при котором вид по оси и вид сбоку помещаются в поле видов."""
    for s in scales:
        if d * s <= AREA_H and (d + l) * s + GAP <= AREA_W:
            return s
    return scales[-1]


def layout(d, l, scales=None):
    """Масштаб и центры видов по габариту формы из STEP: d — max(X, Y), l — Z."""
    scales = tuple(scales or SCALES)
    s = pick_scale(d, l, scales)
    iso = next((q for q in scales if q <= s and d * q <= ISO_MAX), scales[-1])
    cy = MARGIN + 30.0 + AREA_H / 2
    sh = {"scale": s, "scale_txt": scale_txt(s),
          "views": {"front": [MARGIN + d * s / 2, cy, s],
                    "side": [MARGIN + d * s + GAP + l * s / 2, cy, s],
                    "iso": [POS["iso"][0], POS["iso"][1], iso]}}
    sh.update({k: list(v) for k, v in POS.items() if k != "iso"})
    return sh


def compare(chk, meas, tol=TOL):
    """Сверка: meas {sym: значение по 3D | строка-причина}. -> [{"sym", "kind", "calc",
    "step", "delta", "ok", "msg"}]; неизмеренное — не ok."""
    res = []
    for c in chk:
        sym, kind, calc = c["sym"], c["kind"], c["value"]
        v = meas.get(sym)
        r = {"sym": sym, "kind": kind, "calc": calc, "step": None, "delta": None, "ok": False}
        if v is None or isinstance(v, str):
            r["msg"] = f"{sym}: не измерено по 3D" + (f" — {v}" if v else "")
        else:
            if kind == "center":
                dlt = math.hypot(v[0] - calc[0], v[1] - calc[1])
            else:
                dlt = abs(float(v) - float(calc))
            ok = dlt < 0.5 if kind in COUNT else dlt <= tol + 1e-9
            r.update(step=v, delta=round(dlt, 4), ok=ok)
            r["msg"] = "" if ok else (f"{sym}: 3D {_val(v)} ≠ расчёт {_val(calc)}"
                                      + ("" if kind in COUNT else f" (Δ {dlt:.3f} > {tol:g} мм)"))
        res.append(r)
    return res


def warnings(res):
    return [r["msg"] for r in res if not r["ok"]]


def _geo(r, txt):
    if r["step"] is None:
        return [r["sym"], _val(r["calc"]), "расчёт ⚠ не измерено по 3D", txt]
    src = "3D" if r["ok"] else f"3D ⚠ расчёт {_val(r['calc'])}"
    return [r["sym"], _val(r["step"]), src, txt]


def legend_rows(rec, res):
    """Легенда листа [обозн., значение, источник, смысл]: геометрия — по 3D, прочее — .assy.json;
    измеренные размеры без строки в легенде дописываются в конец."""
    st = {r["sym"]: r for r in res if r["kind"] not in NOGEO}
    rows, seen = [], set()
    for sym, val, txt in rec["legend"]:
        r = st.get(sym)
        if r is None:
            rows.append([sym, val, ".assy.json", txt])
        else:
            seen.add(sym)
            rows.append(_geo(r, txt))
    rows += [_geo(r, KINDS[r["kind"]]) for s, r in st.items() if s not in seen]
    return rows


def md_table(res):
    """Строки таблицы сверки для <ID>.techdraw.md."""
    out = ["| Обозн. | Что измерено по 3D | Расчёт | 3D | Δ | Статус |",
           "|---|---|---|---|---|---|"]
    for r in res:
        st = "OK" if r["ok"] else ("не измерено" if r["step"] is None else "⚠ расхождение")
        out.append(f"| {r['sym']} | {KINDS[r['kind']]} | {_val(r['calc'])} | "
                   f"{'—' if r['step'] is None else _val(r['step'])} | "
                   f"{'—' if r['delta'] is None else _fmt(r['delta'])} | {st} |")
    return out


def self_test():
    """Без FreeCAD: эталоны, z сечения, сверка, легенда, масштаб."""
    from egm.cad.model import Band, Contour, Dim, Hole, PartModel, Window
    pts = [((31.0 if i % 2 == 0 else 30.0) * math.cos(i * math.pi / 4),
            (31.0 if i % 2 == 0 else 30.0) * math.sin(i * math.pi / 4)) for i in range(8)]
    holes = [Hole(40.0, 0.0, 4.5), Hole(0.0, 40.0, 4.5), Hole(-40.0, 0.0, 4.5), Hole(0.0, -40.0, 4.5)]
    m = PartModel("X.01A", 4.2, 88.0, Contour(pts), holes=holes,
                  dims=[Dim(88.0, "D"), Dim(80.0, "Dотв"), Dim(62.0, "DВ"), Dim(60.0, "Dверш")],
                  legend=[("u", 50, "передаточное число"), ("D", 88.0, "наружный диаметр")])
    rec = record("X.01A", "01", m, "RING (.01A)", "венец")
    kinds = {c["sym"]: c["kind"] for c in rec["checks"]}
    assert kinds == {"D": "d_out", "Dотв": "d_bc", "DВ": "d_root", "Dверш": "d_tip",
                     "центр D": "center", "n отв": "n_holes", "Ø отв 4.5": "d_hole",
                     "отв xy": "holes_xy", "B": "length"}, kinds
    assert all(c["z"] == 2.1 for c in rec["checks"] if c["z"] is not None), rec["checks"]
    meas = {"D": 88.0, "Dотв": 80.0, "DВ": 62.0, "Dверш": 60.0, "центр D": [0.0, 0.0],
            "n отв": 4, "Ø отв 4.5": 4.5, "отв xy": 0.0, "B": 4.2}
    assert not warnings(compare(rec["checks"], meas)), warnings(compare(rec["checks"], meas))
    bad = dict(meas, D=88.03, **{"n отв": 3})
    bad.pop("Dверш")
    w = warnings(compare(rec["checks"], bad))
    assert len(w) == 3 and "88.03" in w[0] and "не измерено" in " ".join(w), w
    rows = legend_rows(rec, compare(rec["checks"], bad))
    assert rows[0] == ["u", "50", ".assy.json", "передаточное число"], rows[0]
    assert rows[1][:2] == ["D", "88.03"] and rows[1][2].startswith("3D ⚠"), rows[1]
    assert any(r[0] == "Dверш" and "не измерено" in r[2] for r in rows), rows
    assert len(md_table(compare(rec["checks"], meas))) == 2 + len(rec["checks"])
    sh = layout(88.0, 4.2)
    assert sh["scale"] == 2.0 and sh["scale_txt"] == "2:1", sh
    (fx, _, s), sx = sh["views"]["front"], sh["views"]["side"][0]
    assert fx + 88.0 * s / 2 + GAP <= sx - 4.2 * s / 2 + 1e-6, ("виды перекрываются", sh)
    assert pick_scale(14.0, 1.0) == 10.0 and pick_scale(300.0, 4.0) == 0.5
    c = Contour([(1.0, 0.0), (0.0, 1.0), (-1.0, 0.0)])
    sep = PartModel("X.02", 10.0, 68.0, c, view="unroll",
                    windows=[Window(0.0, 30.0, 32.0, 2.0, 1.0, 3.0),
                             Window(180.0, 30.0, 32.0, 2.0, 1.0, 3.0),
                             Window(0.0, 30.0, 32.0, 2.0, 6.0, 3.0)])
    assert free_z(sep) == 5.0, free_z(sep)
    win = [(c_["value"], c_["z"]) for c_ in checks(sep, "02") if c_["kind"] == "windows"]
    assert win == [(2, 2.5), (1, 7.5)], win
    assert record("X.02", "02", sep, "CAGE (.02)", "")["notes"][-1].startswith("развёртка")
    cov = PartModel("X.07B", 14.0, 88.0, c, bands=[Band(0.0, 21.0, -6.0, 6.0, "cut")])
    ln = [c_ for c_ in checks(cov, "07") if c_["kind"] == "length"][0]
    assert (ln["sym"], ln["value"], free_z(cov)) == ("t", 14.0, 7.0), (ln, free_z(cov))
    hub = PartModel("X.02", 10.0, 68.0, c, bands=[Band(0.0, 21.0, -6.0, 6.0, "add")])
    lh = [c_ for c_ in checks(hub, "02") if c_["kind"] == "length"][0]
    assert (lh["sym"], lh["value"]) == ("L", 16.0), lh
    ecc = PartModel("X.03B", 7.0, 50.0, c, cx=(0.4, 0.0))
    ce = [c_ for c_ in checks(ecc, "03") if c_["kind"] == "center"]
    assert compare(ce, {"центр D": [0.4, 0.005]})[0]["ok"], ce
    return True
