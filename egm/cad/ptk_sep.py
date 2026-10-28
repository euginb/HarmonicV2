"""Сепаратор ПТК (.02): PartModel из ptk_configs.json → sep (Д-46).

Втулка dс/Dс × B с прямыми радиальными окнами; SVG — развёртка по Dm = 2RΣ с окнами
всех рядов, размеры — сносками в легенде (Д-47); STEP — все ряды. Углы — система
корпуса, 0° — впадина 0 венца ряда 1.
"""
import math

from egm.cad.model import AxialHole, Band, Circle, Contour, Dim, PartModel, PinHole, Window


def build(cfg, part, row=None):
    s = cfg["sep"]
    k = row or part["rows"][0]
    w = next(x for x in s["rows"] if x["row"] == k)
    N = 360
    pts = [(s["r_in"] * math.cos(2 * math.pi * i / N), s["r_in"] * math.sin(2 * math.pi * i / N))
           for i in range(N)]
    m = PartModel(part["id"], s["length"], 2 * s["r_out"], Contour(pts))
    m.windows = [Window(x["cage"] + j * 360 / s["n"], s["r_in"], s["r_out"], s["w"], x["z0"],
                        s["h"], x["row"]) for x in s["rows"] for j in range(s["n"])]
    m.row = k
    m.view = "unroll"
    Dc, dc, Dm = 2 * s["r_out"], 2 * s["r_in"], s["r_out"] + s["r_in"]
    m.notes = [f"сепаратор, ряды {part['rows']}; развёртка по Dm = {Dm:g}, ряд {k} — основной линией",
               f"окна {s['n']} × ({s['w']:g} × {s['h']:g}) в ряду, прямые радиальные (Д-36, Д-46)",
               "x — дуга по Dm от 0° (впадина 0 венца ряда 1) по отсчёту углов, y — от торца",
               "Dс, dс, толщина, длины окружностей — в легенде (Д-47); соединение с выходом — OQ-12"]
    m.legend = [("n", s["n"], "окон в ряду = тел в ряду"),
                ("RΣ", cfg["R_sum"], "окружность центров тел"),
                ("Dс", round(Dc, 3), "наружный Ø: 2(RΣ + 1.1aω)"),
                ("dс", round(dc, 3), "внутренний Ø: 2(RΣ − 1.1aω)"),
                ("hс", round(s["r_out"] - s["r_in"], 3), "толщина стенки: (Dс − dс)/2 = 2.2aω"),
                ("Dm", round(Dm, 3), "средний Ø = 2RΣ, по нему развёртка"),
                ("π·Dс", round(math.pi * Dc, 2), "длина окружности по Dс, мм"),
                ("π·dс", round(math.pi * dc, 2), "длина окружности по dс, мм"),
                ("π·Dm", round(math.pi * Dm, 2), "длина окружности по Dm = длина развёртки, мм"),
                ("t", round(math.pi * Dm / s["n"], 3), "шаг окон по Dm: π·Dm / n, мм"),
                ("w", s["w"], "ширина окна: Dш + sep_gap"),
                ("h", s["h"], "высота окна: l + sep_gap"),
                ("перемычка", s["web"], "по dс между окнами, мм"),
                (f"cage{k}", w["cage"], f"поворот окон ряда {k}, ° (Д-46)"),
                (f"z0{k}", w["z0"], f"начало окон ряда {k} от торца, мм"),
                ("B", s["length"], "длина втулки = ширина пакета")]
    cup = part.get("cup") or {}
    if cup.get("hub_d"):                 # CP-45: стакан L1 (.02A) — дно и ступица выхода
        rb, z = (cup.get("hub_bore") or 0.0) / 2, cup["z_in"]
        m.thick = z
        m.bands = [Band(rb, s["r_out"], z, cup["t"]),
                   Band(rb, cup["hub_d"] / 2, z + cup["t"], cup["hub_l"])]
        m.notes.append(f"стакан: дно z {z:g}…{z + cup['t']:g}, ступица Ø{cup['hub_d']:g}"
                       f"×{cup['hub_l']:g}, отв. Ø{2 * rb:g} — в STEP; на развёртке не показаны")
        m.legend += [("z дна", z, "внутренний торец дна от торца пакета, мм (Д-81)"),
                     ("t дна", cup["t"], "толщина дна, мм"),
                     ("ступица", f"Ø{cup['hub_d']:g}×{cup['hub_l']:g}", "посадка .09, длина"),
                     ("отв. ступицы", 2 * rb, "под .10 — опору конца входного вала")]
    jn = part.get("join") or {}
    if jn:                               # CP-63: .02B — бурт (collar), .02C — стенка под .12B (insert)
        W, z, L = s["length"], jn["z"], jn["L"]
        ins = jn["scheme"] == "insert"
        end = z + L if ins else z
        if end > W + 1e-9:
            m.bands.append(Band(s["r_in"], s["r_out"], W, end - W))
        r0, r1 = (s["r_in"], s["r_out"]) if ins else (jn["d"] / 2, jn["D"] / 2)
        ax = bool(jn.get("axial"))           # CP-79, Д-93: бурт h_b, осевые сквозные штифты на r_j
        if not ins:
            m.bands.append(Band(r0, r1, z, jn["h_b"] if ax else L))
        if ax:
            m.axial = [AxialHole(a, jn["r_j"], jn["pin_d"], z - 1.0, jn["h_b"] + 2.0) for a in jn["pin_a"]]
            m.notes.append(f"CP-79: бурт {'наружу' if jn['dir'] == 'out' else 'внутрь'} z {z:g}…"
                           f"{z + jn['h_b']:g}, дно-лист t_s {jn['t_s']:g} к торцу; штифты {jn['pin_n']}×"
                           f"Ø{jn['pin_d']:g} осевые сквозные на r {jn['r_j']:g}, через 360/n (Д-93)")
        else:
            m.pins = [PinHole(a, jn["pin_z"], jn["pin_d"], r0 - 1.0, r1 + 1.0) for a in jn["pin_a"]]
        pl = f"×{jn['pin_l']:g}" if jn.get("pin_l") else ""
        m.notes.append((f"обечайка .02C без бурта: стенка до z {end:g} под дно-вставку .12B" if ins else
                        f"бурт .02B Ø{2 * r0:g}/Ø{2 * r1:g} на z {z:g}…{z + L:g}: поясок .12A — в отверстии")
                       + f"; штифты {jn['pin_n']}×Ø{jn['pin_d']:g}{pl} радиально на z {jn['pin_z']:g}, "
                       "по осям окон последнего ряда (Д-76) — в STEP; на развёртке не показаны")
        m.legend += [("z стыка", z, "начало пояса / дна .12 от торца пакета, мм (Д-76)"),
                     ("Lп", L, "осевая длина пояса: 2·edge_k·d (Д-72)"),
                     ("штифты", f"{jn['pin_n']}×Ø{jn['pin_d']:g}{pl}", "ГОСТ 24296-93; в .02 — H7 до ХТО (TECH-01)"),
                     ("z штифтов", jn["pin_z"], "ось отверстий от торца пакета, мм"),
                     ("угол шт. 1", jn["pin_a"][0], "ось окна последнего ряда, ° (Д-76)")]
        if not ins:
            m.legend += [("dб", jn["d"], "отверстие бурта: dс − 2·c_in"),
                         ("Dб", jn["D"], "наружный Ø бурта: Dс + 2·c_out")]
        w = jn.get("weld") or {}
        if w.get("seam") is not None:
            m.notes.append(f"маршрут weld: лист {w['sheet']:g}, шов по образующей на {w['seam']:g}° — "
                           "перемычка ряда 1, мимо штифтов (TECH-01, Д-76)")
    return m


def self_test():
    """Развёртка: окна всех рядов, шов 0° делит окно на две части, сноски с длинами окружностей."""
    from egm.cad import svg
    rows = [{"row": k + 1, "cage": c, "z0": 1.375 + 8 * k}
            for k, c in enumerate((0.0, 3.6, 0.0, 3.6))]
    cfg = {"R_sum": 33.5, "sep": {"n": 50, "r_in": 33.06, "r_out": 33.94, "w": 2.05, "h": 4.25,
                                  "length": 33.0, "web": 2.102, "rows": rows}}
    m = build(cfg, {"id": "PTK-T.02", "rows": [1, 2, 3, 4]}, 2)
    assert m.view == "unroll" and len(m.windows) == 200, len(m.windows)
    out = svg.render(m)
    n = out.count("<rect")
    assert n == 2 + 200 + 2, ("фон, контур, 200 окон, 2 части окон на шве 0°", n)
    leg = {a: b for a, b, _ in m.legend}
    assert abs(leg["π·Dm"] - 210.49) < 0.01 and leg["hс"] == 0.88, leg
    assert "π·Dm = 210.49" in out and "ряд 4: z0" in out, "подписи развёртки"
    jn = {"scheme": "collar", "z": 36.5, "L": 7.5, "h_b": 4.5, "t_s": 3.0, "axial": True,
          "dir": "in", "r_j": 28.56, "D": 69.88, "d": 46.12, "pin_d": 3.0, "pin_n": 6,
          "pin_l": 8.0, "pin_z": 40.25, "pin_a": [60.0 * k for k in range(6)]}
    m2 = build(cfg, {"id": "PTK-T.02B", "rows": [1, 2, 3, 4], "join": jn}, 1)
    assert not m2.pins and len(m2.axial) == 6 and m2.bands[-1].h == 4.5, (m2.pins, m2.bands)
    return True
