"""Венец ПТК (.01): геометрия, STEP (CadQuery), SVG (Д-24, Д-30).

Система координат: впадина 0 на 0°, ось Z — ось редуктора, z = 0 — торец.
Внутренний контур — замкнутая цепочка сегментов `profile` (profile()), общая
для STEP и SVG. Профиль условный: z гнёзд Ø тела с центрами на окружности
центров (положение максимального вылета тела), между гнёздами — дуги этой
окружности. TODO(CP-08): точный профиль — эквидистанта траектории центра тела —
и повышение ptk.GEOM_REV.
"""
import math

from egm.cad import svg


def _pol(r, a):
    a = math.radians(a)
    return (r * math.cos(a), r * math.sin(a))


def profile(r_c, rho, z):
    """Контур впадин против часовой стрелки: [гнездо 0, дуга 0-1, гнездо 1, ...].

    Сегмент: {'kind': 'arc', 'c', 'r', 'p0', 'pm', 'p1', 'large'}; p0/p1 — концы,
    pm — средняя точка (для threePointArc), large — дуга больше 180°.
    Гнездо радиуса rho с центром на окружности r_c пересекает её в точках
    ±a от своего центра: a = 2·asin(rho / (2·r_c)).
    """
    if not 0 < rho < r_c or z < 3:
        raise ValueError(f"профиль венца: rho={rho:g}, r_c={r_c:g}, z={z}")
    a = math.degrees(2 * math.asin(rho / (2 * r_c)))
    p = 360 / z
    if 2 * a >= p:
        raise ValueError(f"гнёзда Ø{2 * rho:g} перекрываются: z={z}, "
                         f"Ø центров {2 * r_c:g}")
    ends = [(_pol(r_c, j * p - a), _pol(r_c, j * p + a)) for j in range(z)]
    segs = []
    for j in range(z):
        (q0, q1), nxt = ends[j], ends[(j + 1) % z][0]
        segs.append({"kind": "arc", "c": _pol(r_c, j * p), "r": rho, "p0": q0,
                     "pm": _pol(r_c + rho, j * p), "p1": q1, "large": True})
        segs.append({"kind": "arc", "c": (0.0, 0.0), "r": r_c, "p0": q1,
                     "pm": _pol(r_c, (j + 0.5) * p), "p1": nxt,
                     "large": p - 2 * a > 180})
    return segs


def ring_geom(cfg, part):
    g = cfg["geom"]
    d_body, z = g["body"]["d"], int(cfg["z_ring"])
    n, pins = int(g["ring_holes"]["n"]), int(g["ring_holes"]["pins"])
    s = part["s"]
    r_c = cfg["d_pitch"] / 2 + cfg["ecc"]                      # центры гнёзд
    r_bc = cfg["d_bc"] / 2
    gaps = sorted({round(i * n / pins) % n for i in range(pins)}) if pins else []
    return {
        "id": part["id"], "thick": g["body"]["l"], "d_out": cfg["d_out"],
        "d_centers": 2 * r_c, "d_root": cfg["d_root"], "d_bc": cfg["d_bc"],
        "profile": profile(r_c, d_body / 2, z), "r_pocket": d_body / 2,
        "bolts": [_pol(r_bc, s + j * 360 / n) for j in range(n)],
        "d_bolt": g["fastener"]["d_clear"], "bolt": g["ring_holes"]["bolt"],
        "pins": [_pol(r_bc, s + (k + 0.5) * 360 / n) for k in gaps],
        "d_pin": g["ring_holes"]["pin_d"], "s": s, "z": z, "n": n,
        "rows": part.get("rows", []),
    }


def step(geo, path):
    import cadquery as cq                                     # опционально
    segs = geo["profile"]
    w = cq.Workplane("XY").moveTo(*segs[0]["p0"])
    for sg in segs:
        w = w.threePointArc(sg["pm"], sg["p1"])
    cut = w.close().extrude(geo["thick"])
    wp = cq.Workplane("XY").circle(geo["d_out"] / 2).extrude(geo["thick"]).cut(cut)
    top = lambda w: w.faces(">Z").workplane()
    wp = top(wp).pushPoints(geo["bolts"]).hole(geo["d_bolt"])
    if geo["pins"]:
        wp = top(wp).pushPoints(geo["pins"]).hole(geo["d_pin"])
    cq.exporters.export(wp, str(path))


def drawing(geo):
    d = svg.Drawing(geo["d_out"], title=geo["id"])
    d.circle(0, 0, geo["d_out"] / 2, "part")
    d.path(geo["profile"], "part")
    d.circle(0, 0, geo["d_centers"] / 2, "axis")
    d.circle(0, 0, geo["d_bc"] / 2, "axis")
    for x, y in geo["bolts"]:
        d.circle(x, y, geo["d_bolt"] / 2, "part")
    for x, y in geo["pins"]:
        d.circle(x, y, geo["d_pin"] / 2, "part")
    d.dia(geo["d_out"], 0, "Ø{:g}")
    d.dia(geo["d_bc"], 1, "Ø{:g} окр. отв.")
    d.dia(geo["d_root"], 2, "Ø{:g} впадин")
    d.dia(geo["d_centers"], 3, "Ø{:g} центров гнёзд")
    d.note([f"{geo['n']} отв. Ø{geo['d_bolt']:g} ({geo['bolt']}), штифты {len(geo['pins'])}×Ø{geo['d_pin']:g} H7",
            f"z = {geo['z']}, сдвиг сверловки s = {geo['s']:g}° от впадины 0 (Д-19)",
            f"гнёзда {geo['z']}×R{geo['r_pocket']:g} — условный профиль до CP-08",
            f"толщина {geo['thick']:g} мм, ряды {geo['rows']}"])
    return d.render()


def self_test():
    """Контур замкнут и непрерывен, дуги на своих окружностях, перекрытие — ошибка."""
    segs = profile(18.64, 2.5, 20)                            # u = 20, ролик Ø5
    assert len(segs) == 40
    for s0, s1 in zip(segs, segs[1:] + segs[:1]):
        assert s0["p1"] == s1["p0"], (s0, s1)
    for sg in segs:
        for pt in (sg["p0"], sg["pm"], sg["p1"]):
            assert abs(math.dist(pt, sg["c"]) - sg["r"]) < 1e-9, sg
    assert abs(math.hypot(*segs[0]["pm"]) - 21.14) < 1e-9     # Ø впадин / 2
    try:
        profile(18.64, 5.0, 20)
        raise AssertionError("перекрытие гнёзд не обнаружено")
    except ValueError:
        pass
    d = svg.Drawing(60)
    d.path(segs, "part")
    assert d.render().count("A2.5000,2.5000") == 20
    return True
