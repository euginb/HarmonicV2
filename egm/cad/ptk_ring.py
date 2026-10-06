"""Венец ПТК (.01): построение PartModel (Д-24, Д-31, Д-32).

Профиль — эквидистанта траектории центра тела (egm/ptk_profile.py). Система
координат профиля: впадина 0 на 0°; сверловка повёрнута на s (Д-19).
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
    d, z = g["body"]["d"], int(cfg["z_ring"])
    h = g["ring_holes"]
    n, pins = int(h["n"]), int(h["pins"])
    s = part["s"]
    rows = {r["row"]: r for r in cfg["phasing"]}
    k = part["rows"][0] if row is None else row
    if k not in part["rows"]:
        raise ValueError(f"{part['id']}: ряд {k} собирается из варианта другого венца")
    rw = rows[k]
    R0, e, rho = cfg["d_pitch"] / 2, cfg["ecc"], d / 2
    d_tip = cfg.get("d_tip") or 2 * (R0 - e + rho)
    r_bc = cfg["d_bc"] / 2
    gaps = sorted({round(i * n / pins) % n for i in range(pins)}) if pins else []
    m = PartModel(part["id"], g["body"]["l"], cfg["d_out"],
                  Contour(ptk_profile.profile_points(e, R0, rho, z)))
    m.holes = [Hole(*_pol(r_bc, s + j * 360 / n), g["fastener"]["d_clear"]) for j in range(n)]
    m.holes += [Hole(*_pol(r_bc, s + (j + 0.5) * 360 / n), h["pin_d"], "pin") for j in gaps]
    m.axes = [Circle(R0), Circle(r_bc)]
    m.dims = [Dim(cfg["d_out"], "Øнар"), Dim(cfg["d_bc"], "Ø окр. отв."),
              Dim(cfg["d_root"], "Ø впадин"), Dim(d_tip, "Ø вершин"),
              Dim(cfg["d_pitch"], "Ø дел.")]
    m.marks = [Mark(0, d_tip / 2, cfg["d_root"] / 2 + 2, "впадина 0"),
               Mark(s, r_bc + 3, r_bc + 6, f"отв. 1, s = {s:g}°"),
               Mark(rw["phi"] + s, 0, R0 - rho, f"e ряда {k}, φ = {rw['phi']:g}°")]
    m.notes = [f"ряды {part['rows']}; чертёж для ряда {k} (φ = {rw['phi']:g}°, вход 0°)",
               f"профиль: эквидистанта траектории центра тела, ρ = {rho:g} (Д-31)",
               f"толщина B венца = {g['body']['l']:g} мм; штифты H7"]
    m.legend = [("u", cfg["u"], "передаточное число, u = n = z − 1 (Д-31)"),
                ("z", z, "число впадин венца"),
                ("n тел", cfg["n_bodies"], "тел в ряду"),
                ("Ø тела", d, "мм, ρ = Ø тела/2"),
                ("e", e, "эксцентриситет, мм"),
                ("e max", cfg.get("e_max", "—"), "предел подреза профиля, мм"),
                ("Ø дел.", cfg["d_pitch"], "2·R0, окр. центров тел при e = 0"),
                ("Ø впадин", cfg["d_root"], "Ø дел. + Ø тела + 2e"),
                ("Ø вершин", round(d_tip, 2), "Ø дел. + Ø тела − 2e"),
                ("Ø окр. отв.", cfg["d_bc"], "окружность центров отверстий"),
                ("Øнар", cfg["d_out"], "наружный Ø венца"),
                ("Отверстия", cfg["holes"], "болты и штифты венца"),
                ("Крепление", cfg.get("mount", "—"), "ключ ring_mounts (Д-33)"),
                ("gap_k", cfg.get("gap_k", "—"), "шаг тел / Ø тела, подобран (Д-34)"),
                ("γ max", cfg.get("gamma_max", "—"), "наибольший угол профиля, °"),
                ("η", cfg.get("eta", "—"), "КПД тела, оценка (Д-34)"),
                ("s", s, "сдвиг сверловки от впадины 0, ° (Д-19)"),
                ("φ", rw["phi"], f"фаза эксцентрика ряда {k}, ° (Д-08)")]
    return m


def self_test():
    """Модель строится, контур в пределах Ø вершин…Ø впадин, легенда в SVG."""
    e = 0.27
    cfg = {"u": 19, "z_ring": 20, "n_bodies": 19, "ecc": e, "e_max": 0.33, "d_pitch": 34.78,
           "d_root": 34.78 + 5 + 2 * e, "d_bc": 52.8, "d_out": 65.3, "holes": "8×M4+2шт Ø4",
           "mount": "M4x8P2",
           "geom": {"body": {"d": 5.0, "l": 8.0},
                    "ring_holes": {"n": 8, "pins": 2, "pin_d": 4.0},
                    "fastener": {"d_clear": 4.5}},
           "phasing": [{"row": 1, "phi": 0, "s": 0}, {"row": 2, "phi": 90, "s": 0}]}
    part = {"id": "PTK-019-T.01A", "s": 0.0, "rows": [1, 2]}
    m = build(cfg, part, row=2)
    rs = [math.hypot(*p) for p in m.cut.pts]
    assert len(rs) == 20 * 24 and len(m.holes) == 10
    assert cfg["d_root"] / 2 + 1e-6 >= max(rs) and min(rs) >= (34.78 - 2 * e + 5) / 2 - 1e-3
    out = svg.render(m)
    assert "Ø впадин" in out and "Легенда" in out and "φ = 90°" in out
    try:
        build(cfg, part, row=3)
        raise AssertionError("ряд чужого варианта принят")
    except (ValueError, KeyError):
        pass
    return True
