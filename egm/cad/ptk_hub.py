"""Ступица выхода ПТК .12 (CP-63, Д-72, Д-73, Д-76): PartModel из cfg["layout"] → cad_parts[].join.

.12A (L2, collar): поясок Ø 2·r_j × Lп входит в отверстие бурта .02B; за пояском — ступица d.09.
.12B (L3, insert): дно-вставка Ø dс × Lп внутри обечайки .02C, за ней бурт Ø Dс × f — упор
в торец обечайки; за буртом — ступица d.09.
Гнёзда штифтов — радиально от наружной поверхности пояска / вставки на глубину hole12
(l − t + pin_gap, Д-74), на z = Lп/2, углы — оси окон последнего ряда .02 (Д-76).
Отверстие Ø D.10 сквозное — второй .10 на конце входного вала (как у стакана L1).
Локальная z = 0 — внутренний торец (в сборке — cup.z_in, ptk_layout.axial).
"""
import math

from egm.cad.model import Band, Circle, Contour, Dim, PartModel, PinHole

N_PTS = 360


def _circle(r):
    return Contour([(r * math.cos(2 * math.pi * i / N_PTS), r * math.sin(2 * math.pi * i / N_PTS))
                    for i in range(N_PTS)])


def build(cfg, part, row=None):
    j = part.get("join")
    if not j:
        raise ValueError(f"{part['id']}: нет соединения .02–.12 — строится только с --design (CP-63)")
    ins = j["scheme"] == "insert"
    r0, rb, L = (j["r_in"] if ins else j["r_j"]), (j["hub_bore"] or 0.0) / 2, j["L"]
    if rb <= 0:
        raise ValueError(f"{part['id']}: нет .10 — отверстие ступицы не задано (CP-63)")
    m = PartModel(part["id"], L, 2 * r0, _circle(rb))
    z = L
    if ins and j["f"] > 0:
        m.bands.append(Band(rb, j["r_out"], L, j["f"]))
        z += j["f"]
    m.bands.append(Band(rb, j["hub_d"] / 2, z, j["hub_l"]))
    m.pins = [PinHole(a, L / 2, j["pin_d"], r0 - j["hole12"], r0 + 1.0) for a in j["pin_a"]]
    lab = "dс" if ins else "dпояс"
    m.axes = [Circle(j["hub_d"] / 2)]
    m.dims = [Dim(round(2 * r0, 3), lab), Dim(j["hub_d"], "d.09"), Dim(round(2 * rb, 3), "dотв")]
    pl = f"×{j['pin_l']:g}" if j.get("pin_l") else ""
    m.notes = [(f"дно-вставка Ø{2 * r0:g} × {L:g} в обечайке .02C, бурт Ø{2 * j['r_out']:g} × "
                f"{j['f']:g} — упор в торец" if ins else
                f"поясок Ø{2 * r0:g} × {L:g} в отверстии бурта .02B") + f" ({j['scheme']}, Д-73)",
               f"ступица Ø{j['hub_d']:g} × {j['hub_l']:g} под .09; отверстие Ø{2 * rb:g} под .10 сквозное",
               f"гнёзда штифтов {j['pin_n']} × Ø{j['pin_d']:g} глубиной {j['hole12']:g} на z {L / 2:g}, "
               "по осям окон последнего ряда .02 (Д-76); на виде по оси не видны",
               "посадка штифта N7/M7, сборка — TECH-01 «Сборка на штифтах» (OQ-26)"]
    m.legend = [("L", round(z + j["hub_l"], 3),
                 "длина .12: пояс Lп" + (" + бурт f" if ins else "") + " + ступица"),
                (lab, round(2 * r0, 3), "Ø дна-вставки = dс .02C (H7/k6)" if ins
                 else "Ø пояска = отверстие бурта .02B"),
                ("Lп", L, "осевая длина пояса 2·edge_k·d (Д-72)"),
                ("d.09", j["hub_d"], "ступица: посадка .09"),
                ("ступица", j["hub_l"], "длина ступицы, мм"),
                ("dотв", round(2 * rb, 3), "сквозное под .10 — опору конца входного вала"),
                ("штифты", f"{j['pin_n']}×Ø{j['pin_d']:g}{pl}", "ГОСТ 24296-93, гнёзда N7/M7 (TECH-01)"),
                ("гнездо", j["hole12"], "глубина: l − t + pin_gap (Д-74)"),
                ("стенка", round(r0 - j["hole12"] - rb, 2), "под гнездом до отверстия, ≥ pin_wall (Д-76)"),
                ("угол шт. 1", j["pin_a"][0], "ось окна последнего ряда .02, ° (Д-76)")]
    if ins:
        m.legend.insert(3, ("Dб", round(2 * j["r_out"], 3), f"бурт-упор в торец .02C, f = {j['f']:g} мм"))
    return m


def self_test():
    """.12A: поясок + ступица, 10 гнёзд на Lп/2; .12B: вставка + бурт + ступица; эталоны TechDraw; SVG."""
    from egm.cad import svg, techdraw
    j = {"scheme": "collar", "z": 36.5, "L": 9.0, "f": 0.0, "r_in": 33.06, "r_out": 33.94,
         "r_j": 32.06, "D": 69.88, "d": 64.12, "pin_d": 3.0, "pin_n": 10, "pin_l": 8.0,
         "hole12": 5.62, "pin_z": 41.0, "pin_a": [36.0 * k for k in range(10)],
         "hub_d": 30.0, "hub_bore": 19.0, "hub_l": 10.5, "weld": None}
    a = build({}, {"id": "PTK-T.12A-K", "rows": [1], "join": j})
    assert a.d_out == 64.12 and a.thick == 9.0 and len(a.pins) == 10, a
    assert [(b.z0, b.h) for b in a.bands] == [(9.0, 10.5)], a.bands
    assert abs(a.pins[0].r0 - 26.44) < 1e-9 and a.pins[0].z == 4.5, a.pins[0]
    assert techdraw.extent(a)[1:] == (0.0, 19.5), techdraw.extent(a)
    k = {c["sym"]: c for c in techdraw.checks(a, "12")}
    assert k["n шт"]["value"] == 10 and k["z шт"]["value"] == 4.5 and k["L"]["value"] == 19.5, k
    b = build({}, {"id": "PTK-T.12B-K", "rows": [1], "join": {
        **j, "scheme": "insert", "f": 2.0, "hole12": 7.62, "pin_n": 8,
        "pin_a": [45.0 * k for k in range(8)]}})
    assert b.d_out == 66.12 and [(x.z0, x.h) for x in b.bands] == [(9.0, 2.0), (11.0, 10.5)], b.bands
    assert techdraw.extent(b) == (67.88, 0.0, 21.5), techdraw.extent(b)
    for m in (a, b):
        assert "Легенда" in svg.render(m), m.id
    return True
