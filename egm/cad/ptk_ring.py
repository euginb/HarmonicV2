"""Венец ПТК (.01): построение PartModel (Д-24, Д-32, Д-37, Д-38).

Профиль — эквидистанта траектории центра тела (6) Янгулова (egm/ptk_profile.py).
Система координат профиля: впадина 0 на 0°; сверловка повёрнута на s (Д-19).
"""
import math

from egm import ptk_profile
from egm.cad import svg
from egm.cad.model import Circle, Contour, Dim, Hole, Mark, PartModel


def _pol(r, a):
    a = math.radians(a)
    return r * math.cos(a), r * math.sin(a)


def build(cfg, part, row=None):
    g = cfg["geom"]
    D, z = cfg["Drol"], int(cfg["z"])
    h = g["ring_holes"]
    n, pins = int(h["n"]), int(h["pins"])
    s = part["s"]
    rows = {r["row"]: r for r in cfg["phasing"]}
    k = part["rows"][0] if row is None else row
    if k not in part["rows"]:
        raise ValueError(f"{part['id']}: ряд {k} собирается из варианта другого венца")
    rw = rows[k]
    R, a = cfg["R_sum"], cfg["a_w"]
    r_bc = cfg["d_bc"] / 2
    gaps = sorted({round(i * n / pins) % n for i in range(pins)}) if pins else []
    m = PartModel(part["id"], g["roller"]["l"], cfg["d_out"],
                  Contour(ptk_profile.profile_points(a, R, D, z)))
    m.holes = [Hole(*_pol(r_bc, s + j * 360 / n), g["fastener"]["d_clear"]) for j in range(n)]
    m.holes += [Hole(*_pol(r_bc, s + (j + 0.5) * 360 / n), h["pin_d"], "pin") for j in gaps]
    m.axes = [Circle(R), Circle(r_bc)]
    m.dims = [Dim(cfg["d_out"], "D"), Dim(cfg["d_bc"], "Dотв"),
              Dim(cfg["d_root"], "DВ"), Dim(cfg["d_tip"], "Dверш")]
    m.marks = [Mark(0, cfg["d_tip"] / 2, cfg["d_root"] / 2 + 2, "впадина 0"),
               Mark(s, r_bc + 3, r_bc + 6, f"отв. 1, s = {s:g}°"),
               Mark(rw["phi"] + s, 0, R - D / 2, f"aω ряда {k}, φ = {rw['phi']:g}°")]
    m.notes = [f"ряды {part['rows']}; чертёж для ряда {k} (φ = {rw['phi']:g}°, вход 0°)",
               f"профиль: эквидистанта траектории (6) на Dш/2 = {D / 2:g} (Д-38)",
               f"толщина B венца = {g['roller']['l']:g} мм; штифты H7"]
    m.legend = [("u", cfg["u"], "передаточное число, u = n = z − 1"),
                ("z", z, "число впадин венца"),
                ("n", cfg["n"], "тел в ряду"),
                ("Dш", D, "диаметр тела качения, мм"),
                ("aω", a, "эксцентриситет генератора, мм"),
                ("RΣ", R, f"0.5(Dг + Dш), задан: {cfg.get('R_by', '—')}"),
                ("Dг", cfg["Dgen"], "диаметр генератора, мм"),
                ("α max", cfg["alpha_max"], "угол передачи движения, °"),
                ("DВ", cfg["d_root"], "диаметр впадин: 2(RΣ + aω) + Dш"),
                ("Dверш", cfg["d_tip"], "диаметр вершин: 2(RΣ − aω) + Dш"),
                ("Dотв", cfg["d_bc"], "окружность центров отверстий"),
                ("D", cfg["d_out"], "наружный диаметр"),
                ("Отверстия", cfg["holes"], "болты и штифты"),
                ("Крепление", cfg.get("mount", "—"), "ключ ring_mounts (Д-33)"),
                ("s", s, "сдвиг сверловки от впадины 0, ° (Д-19)"),
                ("φ", rw["phi"], f"фаза эксцентрика ряда {k}, ° (Д-08)")]
    return m


def self_test():
    """Модель строится, контур в пределах Dверш…DВ, легенда в SVG."""
    a, R, D = 1.0, 31.3, 5.0
    cfg = {"u": 19, "z": 20, "n": 19, "a_w": a, "R_sum": R, "R_by": "подрез",
           "Drol": D, "Dgen": 2 * R - D, "alpha_max": 32.0,
           "d_root": 2 * (R + a) + D, "d_tip": 2 * (R - a) + D, "d_bc": 82.0,
           "d_out": 95.0, "holes": "8×M4+2шт Ø4", "mount": "M4x8P2",
           "geom": {"roller": {"d": D, "l": 8.0},
                    "ring_holes": {"n": 8, "pins": 2, "pin_d": 4.0},
                    "fastener": {"d_clear": 4.5}},
           "phasing": [{"row": 1, "phi": 0, "s": 0}, {"row": 2, "phi": 90, "s": 0}]}
    part = {"id": "PTK-019-T.01A", "s": 0.0, "rows": [1, 2]}
    m = build(cfg, part, row=2)
    rs = [math.hypot(*p) for p in m.cut.pts]
    assert len(rs) == 20 * 24 and len(m.holes) == 10
    assert cfg["d_root"] / 2 + 1e-6 >= max(rs) and min(rs) >= cfg["d_tip"] / 2 - 1e-3
    out = svg.render(m)
    assert "DВ" in out and "Легенда" in out and "φ = 90°" in out
    try:
        build(cfg, part, row=3)
        raise AssertionError("ряд чужого варианта принят")
    except (ValueError, KeyError):
        pass
    return True
