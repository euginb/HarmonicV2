"""Венец ПТК (.01): геометрия, STEP (CadQuery), SVG.

Система координат: впадина 0 на 0°, ось Z — ось редуктора, z = 0 — торец.
Профиль впадин — условный (дуги Ø тела на окружности центров тел),
TODO(CP-08): точный профиль + повышение ptk.GEOM_REV.
"""
import math

from egm.cad import svg


def ring_geom(cfg, part):
    g = cfg["geom"]
    d_body, z = g["body"]["d"], int(cfg["z_ring"])
    n, pins = int(g["ring_holes"]["n"]), int(g["ring_holes"]["pins"])
    s = part["s"]
    r_c = cfg["d_pitch"] / 2 + cfg["ecc"]                      # центры впадин
    r_bc = cfg["d_bc"] / 2
    pol = lambda r, a: (round(r * math.cos(math.radians(a)), 4),
                        round(r * math.sin(math.radians(a)), 4))
    gaps = sorted({round(i * n / pins) % n for i in range(pins)}) if pins else []
    return {
        "id": part["id"], "thick": g["body"]["l"], "d_out": cfg["d_out"],
        "d_bore": 2 * r_c, "d_root": cfg["d_root"], "d_bc": cfg["d_bc"],
        "pockets": [pol(r_c, j * 360 / z) for j in range(z)], "d_pocket": d_body,
        "bolts": [pol(r_bc, s + j * 360 / n) for j in range(n)],
        "d_bolt": g["fastener"]["d_clear"], "bolt": g["ring_holes"]["bolt"],
        "pins": [pol(r_bc, s + (k + 0.5) * 360 / n) for k in gaps],
        "d_pin": g["ring_holes"]["pin_d"], "s": s, "z": z, "n": n,
        "rows": part.get("rows", []),
    }


def step(geo, path):
    import cadquery as cq                                     # опционально
    wp = cq.Workplane("XY").circle(geo["d_out"] / 2).extrude(geo["thick"])
    top = lambda w: w.faces(">Z").workplane()
    wp = top(wp).hole(geo["d_bore"])
    wp = top(wp).pushPoints(geo["pockets"]).hole(geo["d_pocket"])
    wp = top(wp).pushPoints(geo["bolts"]).hole(geo["d_bolt"])
    if geo["pins"]:
        wp = top(wp).pushPoints(geo["pins"]).hole(geo["d_pin"])
    cq.exporters.export(wp, str(path))


def drawing(geo):
    d = svg.Drawing(geo["d_out"], title=geo["id"])
    d.circle(0, 0, geo["d_out"] / 2, "part")
    d.circle(0, 0, geo["d_bore"] / 2, "part")
    for x, y in geo["pockets"]:
        d.circle(x, y, geo["d_pocket"] / 2, "part")
    d.circle(0, 0, geo["d_bc"] / 2, "axis")
    for x, y in geo["bolts"]:
        d.circle(x, y, geo["d_bolt"] / 2, "part")
    for x, y in geo["pins"]:
        d.circle(x, y, geo["d_pin"] / 2, "part")
    d.dia(geo["d_out"], 0, "Ø{:g}")
    d.dia(geo["d_bc"], 1, "Ø{:g} окр. отв.")
    d.dia(geo["d_root"], 2, "Ø{:g} впадин")
    d.note([f"{geo['n']} отв. Ø{geo['d_bolt']:g} ({geo['bolt']}), штифты {len(geo['pins'])}×Ø{geo['d_pin']:g} H7",
            f"z = {geo['z']}, сдвиг сверловки s = {geo['s']:g}° от впадины 0 (Д-19)",
            f"толщина {geo['thick']:g} мм, ряды {geo['rows']}"])
    return d.render()
