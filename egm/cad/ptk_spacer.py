"""Межрядная шайба ПТК (.05<вар>): PartModel из ptk_configs.json → spacer (Д-53).

Кольцо dвн / D толщиной h в пакете венцов: у торцов пакета и между рядами.
Отверстия — как у венцов в системе корпуса (Д-19): болты на j·360/N от впадины 0 венца
ряда 1, штифты в тех же промежутках; dвн = DВ + 2·spacer_gap — тела и сепаратор не касаются.
"""
import math

from egm.cad.model import Circle, Contour, Dim, Hole, Mark, PartModel

N_PTS = 360


def _pol(r, a):
    a = math.radians(a)
    return r * math.cos(a), r * math.sin(a)


def build(cfg, part, row=None):
    s, g = cfg["spacer"], cfg["geom"]
    h = g["ring_holes"]
    n, pins = int(h["n"]), int(h["pins"])
    r, r_bc = s["r_in"], cfg["d_bc"] / 2
    m = PartModel(part["id"], part["h"], s["d_out"],
                  Contour([_pol(r, 360 * i / N_PTS) for i in range(N_PTS)]))
    gaps = sorted({round(i * n / pins) % n for i in range(pins)}) if pins else []
    m.holes = [Hole(*_pol(r_bc, j * 360 / n), g["fastener"]["d_clear"]) for j in range(n)]
    m.holes += [Hole(*_pol(r_bc, (j + 0.5) * 360 / n), h["pin_d"], "pin") for j in gaps]
    m.axes = [Circle(r_bc)]
    m.dims = [Dim(s["d_out"], "D"), Dim(cfg["d_bc"], "Dотв"), Dim(round(2 * r, 3), "dвн")]
    m.marks = [Mark(0, r_bc + 3, r_bc + 6, "отв. 1, 0°")]
    last = len(cfg["phasing"])
    where = ", ".join("торец" if j in (0, last) else f"ряды {j}–{j + 1}" for j in part["pos"])
    m.notes = [f"межрядная шайба, {len(part['pos'])} шт: {where}",
               f"h = {part['h']:g} мм; отверстия — как у венцов, 0° — впадина 0 венца ряда 1",
               "болты пакета сквозные; посадка штифтов в шайбе — уточнить (Д-53)"]
    m.legend = [("h", part["h"], "толщина: row_gap + (шаг − l)/2 у торца, row_gap + шаг − l между рядами"),
                ("dвн", round(2 * r, 3), "внутренний Ø: DВ + 2·spacer_gap"),
                ("DВ", cfg["d_root"], "диаметр впадин венца"),
                ("D", s["d_out"], "наружный Ø = D венца"),
                ("Dотв", cfg["d_bc"], "окружность центров отверстий"),
                ("Отверстия", cfg["holes"], "болты и штифты, как у венца"),
                ("перемычка", s["web"], "от dвн до отверстия болта, мм")]
    return m


def self_test():
    """Кольцо dвн, 8 болтов + 2 штифта, легенда в SVG."""
    from egm.cad import svg
    cfg = {"d_bc": 80.0, "d_root": 69.8, "holes": "8×M4+2шт Ø4", "phasing": [{}] * 4,
           "spacer": {"r_in": 35.4, "d_out": 88.0, "web": 2.35},
           "geom": {"ring_holes": {"n": 8, "pins": 2, "pin_d": 4.0},
                    "fastener": {"d_clear": 4.5}}}
    m = build(cfg, {"id": "PTK-T.05A", "h": 2.4, "pos": [0, 4], "rows": [1, 4]})
    assert len(m.holes) == 10 and len(m.cut.pts) == N_PTS, (len(m.holes), len(m.cut.pts))
    assert abs(math.hypot(*m.cut.pts[0]) - 35.4) < 1e-9
    out = svg.render(m)
    assert "dвн" in out and "Легенда" in out and "торец" in out, "подписи шайбы"
    return True
