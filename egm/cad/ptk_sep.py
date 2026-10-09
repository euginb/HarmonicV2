"""Сепаратор ПТК (.02): PartModel из ptk_configs.json → sep (Д-46).

Втулка dс/Dс × B с прямыми радиальными окнами; SVG — развёртка по Dm = 2RΣ с окнами
всех рядов, размеры — сносками в легенде (Д-47); STEP — все ряды. Углы — система
корпуса, 0° — впадина 0 венца ряда 1.
"""
import math

from egm.cad.model import Circle, Contour, Dim, PartModel, Window


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
    return True
