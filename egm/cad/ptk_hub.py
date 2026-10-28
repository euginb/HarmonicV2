"""Ступица выхода ПТК .12 (CP-63, Д-72, Д-73, Д-76): PartModel из cfg["layout"] → cad_parts[].join.

.12A (L2, collar): поясок Ø 2·r_j × Lп входит в отверстие бурта .02B; за пояском — ступица d.09.
.12B (L3, insert): дно-вставка Ø dс × Lп внутри обечайки .02C, за ней бурт Ø Dс × f — упор
в торец обечайки; за буртом — ступица d.09.
Гнёзда штифтов — радиально от наружной поверхности пояска / вставки на глубину hole12
(l − t + pin_gap, Д-74), на z = Lп/2, углы — оси окон последнего ряда .02 (Д-76).
Отверстие Ø D.10 сквозное — второй .10 на конце входного вала (как у стакана L1).
Локальная z = 0 — внутренний торец (в сборке — cup.z_in, ptk_layout.axial).
CP-80 (Д-93): collar с осевыми штифтами — .12A — фланец Dф × h_f + ступица d.09, к дну-листу .13
осевыми сквозными штифтами на r_h; дно-лист .13 — build_leaf: диск Ø D бурта × t_s, отверстия
штифтов бурта (r_j) и ступицы (r_h). Прежние .12A (поясок) и .12B — без изменений.
"""
import math

from egm.cad.model import AxialHole, Band, Circle, Contour, Dim, PartModel, PinHole

N_PTS = 360


def _circle(r):
    return Contour([(r * math.cos(2 * math.pi * i / N_PTS), r * math.sin(2 * math.pi * i / N_PTS))
                    for i in range(N_PTS)])


def build(cfg, part, row=None):
    j = part.get("join")
    if not j:
        raise ValueError(f"{part['id']}: нет соединения .02–.12 — строится только с --design (CP-63)")
    if j.get("axial") and j.get("hub"):          # CP-80, Д-93: ступица с фланцем к дну-листу .13
        return _flange(part, j)
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


def _ang(n):
    return [round(k * 360.0 / n, 4) for k in range(n)]


def _flange(part, j):
    """.12A по Д-93 (CP-80): фланец Dф × h_f, осевые сквозные штифты на r_h; ступица d.09; отв. под .10."""
    h, rb = j["hub"], (j["hub_bore"] or 0.0) / 2
    if rb <= 0:
        raise ValueError(f"{part['id']}: нет .10 — отверстие ступицы не задано (CP-63)")
    m = PartModel(part["id"], h["h_f"], 2 * h["r_f"], _circle(rb))
    fl = bool(h.get("flush"))                  # OQ-28, Д-94: фланец в отверстии бурта, ступица сквозь лист .13
    hl = round(j["hub_l"] + (j["t_s"] if fl else 0.0), 3)
    m.bands.append(Band(rb, j["hub_d"] / 2, h["h_f"], hl))
    m.axial = [AxialHole(a, h["r_h"], h["d"], -1.0, h["h_f"] + 2.0) for a in _ang(h["n"])]
    m.axes = [Circle(h["r_h"])]
    m.dims = [Dim(round(2 * h["r_f"], 3), "Dф"), Dim(j["hub_d"], "d.09"), Dim(round(2 * rb, 3), "dотв")]
    pl = f"×{h['l']:g}" if h.get("l") else ""
    m.notes = [f"фланец Ø{2 * h['r_f']:g} × {h['h_f']:g} к дну-листу .13; ступица Ø{j['hub_d']:g} × "
               f"{j['hub_l']:g} под .09; отверстие Ø{2 * rb:g} под .10 сквозное (Д-93)",
               f"штифты {h['n']} × Ø{h['d']:g}{pl} осевые сквозные (фланец + лист) на r {h['r_h']:g}, "
               "через 360/n; посадка H7 (OQ-27)"]
    if fl:
        m.notes.append(f"фланец утоплен в отверстие бурта .02B (r_f ≤ r0 − fl_gap), прижат к дну-листу "
                       f"изнутри; ступица проходит сквозь лист .13 (+t_s {j['t_s']:g}) — Д-94")
    m.legend = [("L", round(h["h_f"] + hl, 3), "длина .12: фланец h_f + ступица"),
                ("Dф", round(2 * h["r_f"], 3), "фланец r_h + edge_k·d_h; не закрывает штифты бурта"),
                ("h_f", h["h_f"], "толщина фланца: max(pin_depth_k·d_h, смятие)"),
                ("d.09", j["hub_d"], "ступица: посадка .09"),
                ("ступица", hl, "длина ступицы, мм" + (" (+t_s — сквозь лист, Д-94)" if fl else "")),
                ("dотв", round(2 * rb, 3), "сквозное под .10 — опору конца входного вала"),
                ("штифты", f"{h['n']}×Ø{h['d']:g}{pl}", "ГОСТ 24296-93, H7, ступица–лист (Д-93)"),
                ("r_h", h["r_h"], "окружность штифтов: d.09/2 + edge_k·d_h")]
    return m


def build_leaf(cfg, part, row=None):
    """Дно-лист .13 (CP-80, Д-93): диск Ø D бурта × t_s из прутка 40Х; осевые сквозные отверстия —
    штифты бурта .02B на r_j и штифты ступицы .12 на r_h; отверстие Ø D.10 в центре."""
    j = part.get("join") or {}
    h = j.get("hub")
    if not (j.get("axial") and h):
        raise ValueError(f"{part['id']}: дно-лист .13 — только collar с осевыми штифтами и ступицей (CP-80)")
    fl = bool(h.get("flush"))                  # Д-94: сквозь лист проходит ступица .12 — отверстие d.09
    rb, t = ((j.get("hub_d") or 0.0) if fl else (j.get("hub_bore") or 0.0)) / 2, j["t_s"]
    if rb <= 0:
        raise ValueError(f"{part['id']}: нет .10 — отверстие дна-листа не задано (CP-80)")
    m = PartModel(part["id"], t, j["D"], _circle(rb))
    m.axial = ([AxialHole(a, j["r_j"], j["pin_d"], -1.0, t + 2.0) for a in j["pin_a"]]
               + [AxialHole(a, h["r_h"], h["d"], -1.0, t + 2.0) for a in _ang(h["n"])])
    m.axes = [Circle(j["r_j"]), Circle(h["r_h"])]
    m.dims = [Dim(j["D"], "D"), Dim(round(2 * rb, 3), "dотв")]
    crit = f"; критерий — {j['crit']}" if j.get("crit") else ""
    tmin = f"{j['t_s_min']:g}" if j.get("t_s_min") is not None else "—"
    m.notes = [f"дно-лист Ø{j['D']:g} × {t:g} — точение из прутка 40Х (Д-93); к торцу бурта .02B, "
               + ("фланец .12 — в отверстии бурта под листом, ступица d.09 сквозь лист (Д-94)" if fl
                  else "со стороны выхода — фланец .12"),
               f"отверстия: {j['pin_n']} × Ø{j['pin_d']:g} на r {j['r_j']:g} (бурт), {h['n']} × Ø{h['d']:g} "
               f"на r {h['r_h']:g} (ступица); сквозные H7, через 360/n"]
    m.legend = [("t_s", t, f"толщина листа{crit}; t_s_min {tmin} (Д-93, OQ-27)"),
                ("D", j["D"], "Ø листа = Ø бурта .02B"),
                ("dотв", round(2 * rb, 3), "под ступицу d.09 (Д-94)" if fl else "под .10"),
                ("шт. бурта", f"{j['pin_n']}×Ø{j['pin_d']:g} r {j['r_j']:g}", "осевые сквозные (CP-79)"),
                ("шт. ступицы", f"{h['n']}×Ø{h['d']:g} r {h['r_h']:g}", "осевые сквозные (CP-80)")]
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
    jx = {**j, "L": 7.5, "dir": "in", "axial": True, "h_b": 4.5, "t_s": 3.0, "crit": "k_fit",
          "t_s_min": 3.0, "r_j": 28.56, "D": 69.88, "d": 46.12, "pin_n": 8,
          "pin_a": [45.0 * k for k in range(8)],
          "hub": {"d": 3.0, "n": 10, "r_h": 19.5, "r_f": 24.0, "h_f": 4.5, "l": 8.0}}      # CP-80
    f = build({}, {"id": "PTK-T.12A-K", "rows": [1], "join": jx})
    assert f.d_out == 48.0 and f.thick == 4.5 and len(f.axial) == 10 and not f.pins, f
    assert [(x.z0, x.h) for x in f.bands] == [(4.5, 10.5)], f.bands
    assert techdraw.extent(f) == (48.0, 0.0, 15.0), techdraw.extent(f)
    s = build_leaf({}, {"id": "PTK-T.13-K", "rows": [1], "join": jx})
    assert s.d_out == 69.88 and s.thick == 3.0 and len(s.axial) == 18 and not s.bands, s
    assert techdraw.extent(s) == (69.88, 0.0, 3.0), techdraw.extent(s)
    for m in (f, s):
        assert "Легенда" in svg.render(m), m.id
    jf = {**jx, "hub_d": 26.0, "hub": {"d": 3.0, "n": 12, "r_h": 17.5, "r_f": 22.0, "h_f": 4.5, "l": 8.0,
                                      "flush": True}}                                   # OQ-28, Д-94
    f2 = build({}, {"id": "PTK-T.12A-K", "rows": [1], "join": jf})
    s2 = build_leaf({}, {"id": "PTK-T.13-K", "rows": [1], "join": jf})
    assert f2.d_out == 44.0 and [(x.z0, x.h) for x in f2.bands] == [(4.5, 13.5)], f2.bands
    assert techdraw.extent(f2) == (44.0, 0.0, 18.0), techdraw.extent(f2)
    assert s2.thick == 3.0 and len(s2.axial) == 20, s2
    assert "Легенда" in svg.render(f2) and "Легенда" in svg.render(s2)
    return True
