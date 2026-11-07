"""Кольцо-бурт .14 конструктива L4 (CP-81, Д-93 п. 5, Д-96): PartModel из join (ptk_layout.join_cad).

Кольцо r0…r_in × L_r входит в выходной торец обечайки .02C; радиальные отверстия штифтов обечайка →
кольцо по осям окон последнего ряда (одна установка SM-1, ось C) — сквозь кольцо: штифт выбивается
изнутри (OQ-29); осевые сквозные отверстия лист .13 → кольцо на r_ja между радиальными.
Локальная система: z = 0 — торец со стороны пакета, z = L_r — торец под дно-лист .13.
"""
import math

from egm.cad.model import AxialHole, Circle, Contour, Dim, PartModel, PinHole


def _circle(r, n=360):
    return Contour([(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)])


def build(cfg, part, row=None):
    j = part.get("join") or {}
    rg, a = j.get("ring"), j.get("ax") or {}
    if not rg:
        raise ValueError(f"{part['id']}: нет кольца-бурта — строится только с --design для L4 (CP-81)")
    r0, r1, L = rg["r0"], rg["r1"], rg["L"]
    m = PartModel(part["id"], L, round(2 * r1, 3), _circle(r0))
    m.pins = [PinHole(x, round(L / 2, 3), j["pin_d"], r0 - 1.0, r1 + 1.0) for x in j["pin_a"]]
    m.axial = [AxialHole(x, a["r_j"], a["pin_d"], -1.0, L + 2.0) for x in a["pin_a"]] if a else []
    m.axes = [Circle(a["r_j"])] if a else [Circle(r0)]
    m.dims = [Dim(round(2 * r1, 3), "Dк"), Dim(round(2 * r0, 3), "dк")]
    pl = f"×{j['pin_l']:g}" if j.get("pin_l") else ""
    al = f"×{a['pin_l']:g}" if a.get("pin_l") else ""
    if j.get("seat"):                          # CP-90 2b-3 ч. 2, Д-102 п. 2 / Д-96: осевых штифтов и листа нет
        m.notes = [f"кольцо-бурт Ø{2 * r1:g}/Ø{2 * r0:g} × {L:g} в выходном торце обечайки .02C (L4, Д-96); "
                   f"в отверстии Ø{2 * r0:g} — опорный обод ступицы .12A (посадка по цилиндру)",
                   f"радиальные {j['pin_n']}×Ø{j['pin_d']:g}{pl} на z {L / 2:g} по делению окон — насквозь .02C + "
                   "кольцо в гнёзда обода .12A, сверловка в сборе с одной установки SM-1 (ось C)"]
        m.legend = [("Dк", round(2 * r1, 3), "наружный Ø = отверстие обечайки dс"),
                    ("dк", round(2 * r0, 3), "отверстие = Ø опорного обода .12A"),
                    ("w", rg["w"], "ширина: max(t_tech, k_fit·d) — посадочная длина штифта (Д-96)"),
                    ("L_r", L, "длина: 2·edge_k·d"),
                    ("рад.", f"{j['pin_n']}×Ø{j['pin_d']:g}{pl}", "обечайка + кольцо + обод, по делению окон (ось C)")]
        return m
    m.notes = [f"кольцо-бурт Ø{2 * r1:g}/Ø{2 * r0:g} × {L:g} в торце обечайки .02C (L4, Д-96); "
               "к торцу z = L — дно-лист .13",
               f"радиальные {j['pin_n']}×Ø{j['pin_d']:g}{pl} на z {L / 2:g} по осям окон последнего ряда — "
               "сверловка с обечайкой в одну установку SM-1 (ось C); сквозь кольцо — выбивка изнутри (OQ-29)",
               f"осевые {a['pin_n']}×Ø{a['pin_d']:g}{al} сквозные на r {a['r_j']:g}, между радиальными; H7"]
    m.legend = [("Dк", round(2 * r1, 3), "наружный Ø = отверстие обечайки dс (посадка H7/k6, TECH-01)"),
                ("dк", round(2 * r0, 3), "внутренний Ø: dс − 2·w"),
                ("w", rg["w"], "ширина: max(гнездо + pin_wall, 2·edge_k·d_a)"),
                ("L_r", L, "длина: max(2·edge_k·d_r, h_b осевых)"),
                ("рад.", f"{j['pin_n']}×Ø{j['pin_d']:g}{pl}", "обечайка–кольцо, по делению окон (ось C)"),
                ("гнездо", j["hole12"], "глубина посадки радиального штифта в кольце, мм"),
                ("ос.", f"{a['pin_n']}×Ø{a['pin_d']:g}{al}", "лист–кольцо, ГОСТ 24296-93"),
                ("r_ja", a["r_j"], "окружность осевых: r_in − edge_k·d_a")]
    return m


def self_test():
    from egm.cad import svg
    j = {"pin_d": 3.0, "pin_n": 10, "pin_l": 8.0, "hole12": 5.0, "pin_a": [36.0 * k for k in range(10)],
         "ring": {"r0": 24.06, "r1": 33.06, "L": 9.0, "w": 9.0},
         "ax": {"r_j": 28.56, "pin_d": 3.0, "pin_n": 10, "pin_l": 12.0,
                "pin_a": [36.0 * k + 18.0 for k in range(10)]}}
    m = build({}, {"id": "PTK-T.14-K", "rows": [1], "join": j})
    assert m.thick == 9.0 and m.d_out == 66.12 and len(m.pins) == 10 and len(m.axial) == 10, m
    assert "Легенда" in svg.render(m)
    js = {k: j[k] for k in ("pin_d", "pin_n", "pin_l", "hole12", "pin_a")}                  # Д-102 п. 2
    ms = build({}, {"id": "PTK-T.14-K", "rows": [1], "join": {**js, "seat": True,
                    "ring": {"r0": 30.06, "r1": 33.06, "L": 9.0, "w": 3.0}}})
    assert len(ms.pins) == 10 and not ms.axial and ms.d_out == 66.12, ms
    try:
        build({}, {"id": "PTK-T.14", "rows": [1], "join": {}})
    except ValueError:
        return True
    raise AssertionError("кольцо без join должно давать ValueError")
