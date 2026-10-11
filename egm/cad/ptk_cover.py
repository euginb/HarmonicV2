"""Крышки .07A/.07B и дистанционные кольца .11 ПТК (CP-45): PartModel конструктива шага 2.

Данные — cfg["layout"] (ptk_designs.json → layout; подставляет ptk_design.apply, Д-55, Д-57).
Локальная z = 0: у .07A — наружный торец (деталь на [−tA, 0]), у .07B — торец со стороны
пакета (деталь на [W, W + tB]).
.07A (вход): диск D × tA, гнездо .10 со стороны пакета, буртик lip, отверстие вала.
.07B (выход): диск D × tB, карман под дно стакана .02, гнездо .09, буртик, отверстие ступицы;
резьба под болты пакета (болты — от .07A через .01 и .05). Отверстия — как у венцов (Д-19).
.11: кольцо dвн = Ø вала, dнар, h — между эксцентриками соседних рядов.
"""
import math
import re

from egm.cad.model import Band, Circle, Contour, Dim, Hole, Mark, PartModel

N_PTS = 360
TAP = {3: 2.5, 4: 3.3, 5: 4.2, 6: 5.0, 8: 6.8, 10: 8.5}   # Ø под резьбу, крупный шаг


def _pol(r, a):
    a = math.radians(a)
    return r * math.cos(a), r * math.sin(a)


def _circle(r):
    return Contour([_pol(r, 360 * i / N_PTS) for i in range(N_PTS)])


def bolt_m(cid):
    """Номинал болта по ID (сегмент крепления 8M4P2) -> 4; 0 — не найден."""
    m = re.search(r"-\d+M(\d+)P", cid)
    return int(m.group(1)) if m else 0


def _holes(cfg, tap):
    g = cfg["geom"]
    h = g["ring_holes"]
    n, pins, r_bc, M = int(h["n"]), int(h["pins"]), cfg["d_bc"] / 2, bolt_m(cfg["id"])
    d = TAP.get(M, round(0.85 * M, 1)) if tap and M else g["fastener"]["d_clear"]
    gaps = sorted({round(i * n / pins) % n for i in range(pins)}) if pins else []
    out = [Hole(*_pol(r_bc, j * 360 / n), d) for j in range(n)]
    out += [Hole(*_pol(r_bc, (j + 0.5) * 360 / n), h["pin_d"], "pin") for j in gaps]
    return out, d


def _cover(cfg, part):
    lay, sd = cfg["layout"], part["side"]
    c, b09, b10 = lay["covers"], lay.get("b09") or {}, lay.get("b10") or {}
    t, gap = c["t" + sd], lay.get("ax_gap", 0.5)
    holes, dh = _holes(cfg, sd == "B")
    if sd == "A":
        r_h = lay["shaft_d"] / 2 + gap
        bands = [Band(0.0, b10["D"] / 2, t - b10["B"], b10["B"] + 1.0, "cut")] if b10 else []
        lip = t - b10.get("B", 0.0)
        what = f"гнездо .10 {b10.get('id', '—')} Ø{b10.get('D', 0):g}×{b10.get('B', 0):g} со стороны пакета"
    else:
        pD, pH = c["pocket"]
        r_h = b09.get("d", lay["shaft_d"]) / 2 + gap
        bands = [Band(0.0, pD / 2, -1.0, pH + 1.0, "cut")]
        if b09:
            bands.append(Band(0.0, b09["D"] / 2, pH - 0.5, b09["B"] + 0.5, "cut"))
        lip = t - pH - b09.get("B", 0.0)
        what = (f"карман Ø{pD:g}×{pH:g} под дно .02, гнездо .09 {b09.get('id', '—')} "
                f"Ø{b09.get('D', 0):g}×{b09.get('B', 0):g}")
    m = PartModel(part["id"], t, c["D"], _circle(r_h), holes=holes, bands=bands)
    m.axes = [Circle(cfg["d_bc"] / 2)] + [Circle(b.r_out) for b in bands]
    m.dims = [Dim(c["D"], "D"), Dim(cfg["d_bc"], "Dотв"), Dim(round(2 * r_h, 2), "dотв")]
    m.marks = [Mark(0, cfg["d_bc"] / 2 + 3, cfg["d_bc"] / 2 + 6, "отв. 1, 0°")]
    M = bolt_m(cfg["id"])
    m.notes = [f"крышка {'входа' if sd == 'A' else 'выхода'} .07{sd}, t = {t:g} мм; {what}",
               f"буртик {lip:g} мм; отверстие {'вала' if sd == 'A' else 'ступицы .02'} Ø{2 * r_h:g}",
               (f"болты M{M}: резьба, Ø{dh:g} под резьбу" if sd == "B" else
                f"болты M{M}: сквозные Ø{dh:g}") + "; отверстия как у венцов (Д-19)"]
    m.legend = [("t", t, "толщина: B.10 + lip (A) | карман + B.09 + lip (B)"),
                ("D", c["D"], "наружный Ø = D венца"),
                ("Dотв", cfg["d_bc"], "окружность центров отверстий"),
                ("гнездо", c["seat_" + sd], "Ø гнезда подшипника"),
                ("dотв", round(2 * r_h, 2), "сквозное: вал | ступица .02 + 2·ax_gap"),
                ("буртик", round(lip, 2), "lip, мм")]
    if sd == "B":
        m.legend.insert(4, ("карман", f"Ø{c['pocket'][0]:g}×{c['pocket'][1]:g}", "под дно стакана .02"))
    return m


def _dist(cfg, part):
    r = cfg["layout"]["r11"]
    m = PartModel(part["id"], r["h"], r["d_out"], _circle(r["d_in"] / 2))
    m.dims = [Dim(r["d_out"], "dнар"), Dim(r["d_in"], "dвн")]
    m.notes = [f"дистанционное кольцо эксцентриков, {r['n']} шт, h = {r['h']:g} мм",
               "между эксцентриками соседних рядов; пакет стягивается гайкой (Д-54)"]
    m.legend = [("h", r["h"], "row_gap + шаг − t эксцентрика"),
                ("dвн", r["d_in"], "Ø вала"),
                ("dнар", r["d_out"], "Ø вала + 2·ring_w, не более Dэ − 2aω − 1")]
    return m


def build(cfg, part, row=None):
    if not cfg.get("layout"):
        raise ValueError(f"{part['id']}: нет конструктива — строится только с --design (CP-45)")
    return _dist(cfg, part) if part["id"].split(".", 1)[1][:2] == "11" else _cover(cfg, part)


def self_test():
    """Крышки: сквозные в .07A, резьба в .07B, ступени гнезда и кармана; кольцо .11; SVG."""
    from egm.cad import svg
    lay = {"covers": {"tA": 6.0, "tB": 14.0, "D": 88.0, "seat_A": 19.0, "seat_B": 42.0,
                      "pocket": [68.9, 6.0]},
           "b09": {"id": "61806", "d": 30.0, "D": 42.0, "B": 7.0},
           "b10": {"id": "61800", "d": 10.0, "D": 19.0, "B": 5.0},
           "r11": {"n": 3, "h": 1.0, "d_in": 10.0, "d_out": 14.0}, "shaft_d": 10.0, "ax_gap": 0.5}
    cfg = {"id": "PTK-T-8M4P2-X", "d_bc": 80.0, "layout": lay,
           "geom": {"ring_holes": {"n": 8, "pins": 2, "pin_d": 4.0}, "fastener": {"d_clear": 4.5}}}
    a = build(cfg, {"id": "PTK-T.07A-K", "side": "A", "rows": [1]})
    b = build(cfg, {"id": "PTK-T.07B-K", "side": "B", "rows": [1]})
    assert {h.d for h in a.holes if h.kind == "bolt"} == {4.5}, "сквозные в .07A"
    assert {h.d for h in b.holes if h.kind == "bolt"} == {3.3}, "резьба M4 в .07B"
    assert [(x.z0, x.h) for x in a.bands] == [(1.0, 6.0)], a.bands
    assert len(b.bands) == 2 and b.bands[1].z0 + b.bands[1].h == 13.0, b.bands
    assert abs(math.hypot(*b.cut.pts[0]) - 15.5) < 1e-9
    r = build(cfg, {"id": "PTK-T.11-K", "rows": [1]})
    assert r.thick == 1.0 and abs(math.hypot(*r.cut.pts[0]) - 5.0) < 1e-9
    for m in (a, b, r):
        assert "Легенда" in svg.render(m), m.id
    return True
