"""Сепаратор ПТК (.02): PartModel из ptk_configs.json → sep (Д-46).

Втулка dс/Dс × B с прямыми радиальными окнами; SVG — вид по оси с окнами ряда k,
STEP — все ряды. Углы — система корпуса, 0° — впадина 0 венца ряда 1.
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
    m.axes = [Circle(cfg["R_sum"])]
    m.dims = [Dim(2 * s["r_out"], "Dс"), Dim(2 * s["r_in"], "dс")]
    m.notes = [f"сепаратор, ряды {part['rows']}; вид — окна ряда {k}",
               f"окна {s['n']} × ({s['w']:g} × {s['h']:g}), прямые радиальные (Д-36, Д-46)",
               f"длина B = {s['length']:g}; соединение с выходом — OQ-12"]
    m.legend = [("n", s["n"], "окон в ряду = тел в ряду"),
                ("RΣ", cfg["R_sum"], "окружность центров тел"),
                ("Dс", 2 * s["r_out"], "наружный Ø: 2(RΣ + 1.1aω)"),
                ("dс", 2 * s["r_in"], "внутренний Ø: 2(RΣ − 1.1aω)"),
                ("w", s["w"], "ширина окна: Dш + sep_gap"),
                ("h", s["h"], "высота окна: l + sep_gap"),
                ("перемычка", s["web"], "по dс между окнами, мм"),
                ("cage", w["cage"], f"поворот окон ряда {k}, ° (Д-46)"),
                ("z0", w["z0"], f"начало окон ряда {k} от торца, мм"),
                ("B", s["length"], "длина втулки = ширина пакета")]
    return m
