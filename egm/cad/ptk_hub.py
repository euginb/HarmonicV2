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

from egm.cad.model import AxialHole, Band, Circle, Contour, Dim, KeySlot, PartModel, PinHole

N_PTS = 360


def _circle(r):
    return Contour([(r * math.cos(2 * math.pi * i / N_PTS), r * math.sin(2 * math.pi * i / N_PTS))
                    for i in range(N_PTS)])


def out_feats(cfg, z_hub, z_end, rb, z_in=None):
    """CP-90 этап 2b (Д-102 п. 1): элементы выхода ступицы (.12B; дно .02A — ptk_sep) в локальной z
    детали -> (bands, slots, legend, notes). Заплечик da .09 — от начала ступицы z_hub до торца
    внутреннего кольца (.09 в .07B на W + карман; z_in — начало локальной системы в системе
    корпуса, по умолчанию cup.z_in); da — vendor_prices.yaml → bearings (OQ-31), нет — не строится.
    Отверстие вала d_o и шпоночный паз b × t2 (KeySlot, 0° системы детали) — с наружного торца
    z_end на l_key + ax_gap."""
    lay = cfg.get("layout") or {}
    o, b09, cov = lay.get("output") or {}, lay.get("b09") or {}, lay.get("covers")
    zi = (lay.get("cup") or {}).get("z_in", 0.0) if z_in is None else z_in
    bands, slots, leg, notes = [], [], [], []
    if b09.get("da") and cov and cfg.get("sep"):
        h = round(cfg["sep"]["length"] + cov["pocket"][1] - zi - z_hub, 3)
        if h > 1e-6 and b09["da"] > b09["d"]:
            bands.append(Band(rb, b09["da"] / 2, z_hub, h))
            leg.append(("da", b09["da"], f"заплечик .09 {b09.get('id', '')} на {h:g} мм — упор внутреннего "
                                         "кольца со стороны пакета (Д-102, OQ-31)"))
    elif b09 and o:
        notes.append("заплечик .09 не построен: нет da в vendor_prices.yaml → bearings (OQ-31)")
    lb = (o.get("l_key") or 0.0) + (lay.get("ax_gap") or 0.0)
    if o.get("d") and lb > 0:
        r, k = o["d"] / 2, o.get("key")
        bands.append(Band(0.0, r, z_end - lb, lb + 1.0, "cut"))
        if k:
            slots.append(KeySlot(0.0, r - 1.0, r + k["t2"], k["b"], z_end - lb, lb + 1.0))
        kt = f", паз {k['b']:g} × t2 {k['t2']:g} на 0°" if k else ""
        leg.append(("d_o", o["d"], f"под выходной вал на {lb:g} мм{kt} (Д-102)"))
        notes.append(f"отверстие Ø{o['d']:g} под выходной вал с наружного торца на {lb:g} мм{kt} (CP-90)")
    g = (o.get("grooves") or {}).get("ext")       # CP-90 2b-3: канавка кольца ГОСТ 13942 за .09
    if g and b09.get("B") and cov and cfg.get("sep"):
        zg = round(cfg["sep"]["length"] + cov["pocket"][1] - zi + b09["B"], 3)
        if z_hub - 1e-6 <= zg and zg + g["m"] <= z_end + 1e-6:
            bands.append(Band(g["d2"] / 2, b09["d"] / 2 + 1.0, zg, g["m"], "cut"))
            leg.append(("канавка", g["d2"], f"кольцо {b09['d']:g} ГОСТ 13942: Ø{g['d2']:g} × m {g['m']:g} "
                                             f"на z {zg:g} — фиксация внутр. кольца .09 снаружи (Д-102)"))
        else:
            notes.append(f"канавка ГОСТ 13942 не помещается в ступицу (z {zg:g} + m {g['m']:g} > {z_end:g})")
    return bands, slots, leg, notes


def flange_holes(cfg, z_end):
    """CP-90 этап 2b-2, Д-104: резьбовые отверстия фланца (Ø под резьбу, глубина depth) и штифты
    между ними — с наружного торца ступицы z_end; данные — layout.output.flange."""
    f = ((cfg.get("layout") or {}).get("output") or {}).get("flange")
    if not f:
        return []
    out = [AxialHole(a, f["r"], f["d_tap"], z_end - f["depth"], f["depth"] + 1.0) for a in _ang(f["n"])]
    if f.get("n_p"):
        st = f["n"] // f["n_p"]
        out += [AxialHole(round((j * st + 0.5) * 360.0 / f["n"], 4), f["r"], f["pin_d"],
                          z_end - f["pin_depth"], f["pin_depth"] + 1.0) for j in range(f["n_p"])]
    return out


def build(cfg, part, row=None):
    j = part.get("join")
    if not j:
        raise ValueError(f"{part['id']}: нет соединения .02–.12 — строится только с --design (CP-63)")
    if j.get("seat"):                            # CP-90 2b-3, Д-102 п. 2: L2/L4 без дна-листа .13
        return _seat(cfg, part, j)
    if j.get("axial") and j.get("hub"):          # CP-80, Д-93: ступица с фланцем к дну-листу .13
        if j["hub"].get("mode") == "direct":     # CP-83: без фланца, лист — к торцу ступицы
            return _direct(part, j)
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
    fb, fs, fl, fn = out_feats(cfg, z, z + j["hub_l"], rb)   # CP-90 этап 2b: заплечик da, вал d_o, паз
    m.bands += fb
    m.slots = fs
    m.axial = list(getattr(m, "axial", None) or []) + flange_holes(cfg, z + j["hub_l"])   # Д-104
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
    m.legend += fl
    m.notes += fn
    return m


def _ang(n):
    return [round(k * 360.0 / n, 4) for k in range(n)]


def _seat(cfg, part, j):
    """.12A по Д-102 п. 2 (CP-90 этап 2b-3), L2/L4 при designs[].output: дна-листа .13 нет — фланец
    Ø D × t_f (t_f = t_s, критерии Д-93 п. 3) торцом к бурту .02B (L2) | кольцу .14 (L4), осевые штифты
    радиальными штифтами со стороны окон сепаратора (по делению окон); ступица d.09 × hub_l охватывает
    .09: заплечик da, канавка ГОСТ 13942, торец вровень с .07B (Д-103); отверстия фланца под гайку .16
    (Д-104). z = 0 — торец к бурту/кольцу (сборка: z_in + h_b)."""
    # z = 0 — торец фланца, прижимаемый к бурту .02B / кольцу .14 (сборка: z_in + h_b);
    # t = t_f = t_s (толщина бывшего листа, критерии Д-93 п. 3), hl = hub_l (ax_gap + B.09 + lip_B —
    # ступица вровень с .07B, Д-103). Расширение (фланец Ø D) + ступица d.09 — единая деталь .12A.
    rb, t, hl = (j.get("hub_bore") or 0.0) / 2, j["t_s"], j["hub_l"]
    if rb <= 0:
        raise ValueError(f"{part['id']}: нет .10 — отверстие ступицы не задано (CP-63)")
    m = PartModel(part["id"], t, j["D"], _circle(rb))
    # Band(rb → hub_d/2) — ступица ЗА фланцем (z от t до t + hl), охватывает .09.
    m.bands.append(Band(rb, j["hub_d"] / 2, t, hl))
    zi = ((cfg.get("layout") or {}).get("cup") or {}).get("z_in", 0.0) + j.get("h_b", 0.0)
    fb, fs, fl, fn = out_feats(cfg, t, t + hl, rb, zi)
    m.bands += fb
    m.slots = fs
    # CP-90, Д-102 п. 2 (уточнение 2026-11-06): крепление фланца к бурту .02B / кольцу .14 —
    # РАДИАЛЬНЫМИ штифтами СО СТОРОНЫ ОКОН сепаратора (по делению окон, одна установка SM-1, ось C —
    # как кольцо к обечайке в Д-96), а НЕ осевыми через лист (лист .13 отменён, Д-94/95/97 — CANCELLED).
    # Углы pin_a обязан передавать join_cad выровненными по окнам (n окон % pin_n == 0 — проверяется
    # в ptk_layout); штифт: от j["D"]/2 − 2·pin_d (перемычка 2·pin_d со стороны ступицы) наружу сквозь
    # фланец; r_j (радиус осевых штифтов прежней схемы) в seat-ветке НЕ используется.
    dr = round(2.0 * j["pin_d"], 3)
    m.pins = [PinHole(a, t / 2, j["pin_d"], j["D"] / 2 - dr, j["D"] / 2 + 1.0) for a in j["pin_a"]]
    # Осевые отверстия во фланце — ТОЛЬКО под гайку-опцию .16 (Д-104: flange из layout.output);
    # посадочные/штифтовые гнёзда прежней листовой схемы здесь запрещены.
    m.axial = flange_holes(cfg, t + hl)
    m.axes = [Circle(j["D"] / 2)]
    m.dims = [Dim(j["D"], "Dф"), Dim(j["hub_d"], "d.09"), Dim(round(2 * rb, 3), "dотв")]
    to = "кольца .14 (L4)" if j.get("scheme") == "ring" else "бурта .02B (L2)"
    crit = f"; критерий — {j['crit']}" if j.get("crit") else ""
    pl = f"×{j['pin_l']:g}" if j.get("pin_l") else ""
    m.notes = [f"фланец Ø{j['D']:g} × {t:g} к торцу {to}; ступица Ø{j['hub_d']:g} × {hl:g} охватывает .09, "
               "торец вровень с .07B; дно-листа .13 нет (Д-102 п. 2)",
               f"штифты {j['pin_n']} × Ø{j['pin_d']:g}{pl} радиальные со стороны окон сепаратора "
               f"(фланец + {to.split()[0]}), по делению окон; посадка H7 (Д-102 п. 2)",
               f"отверстие Ø{2 * rb:g} под .10 сквозное"]
    m.legend = [("L", round(t + hl, 3), "длина .12: фланец t_f + ступица (вровень с .07B, Д-103)"),
                ("Dф", j["D"], f"фланец = Ø {to}"),
                ("t_f", t, f"толщина фланца — критерии бывшего листа (Д-93 п. 3){crit}"),
                ("d.09", j["hub_d"], "ступица: посадка .09"),
                ("ступица", hl, "ax_gap + B.09 + lip_B"),
                ("dотв", round(2 * rb, 3), "сквозное под .10 — опору конца входного вала"),
                ("штифты", f"{j['pin_n']}×Ø{j['pin_d']:g}{pl} радиальные", "ГОСТ 24296-93, со стороны окон, к бурту/кольцу")]
    m.legend += fl
    m.notes += fn
    return m


def _direct(part, j):
    """.12 без фланца (CP-83): ступица d.09 × hub_l торцом к дну-листу .13; штифты из листа в глухие
    гнёзда обода на r_h через 360/n; отверстие под .10 сквозное."""
    h, rb = j["hub"], (j["hub_bore"] or 0.0) / 2
    if rb <= 0:
        raise ValueError(f"{part['id']}: нет .10 — отверстие ступицы не задано (CP-63)")
    nest = h.get("nest") or h["depth"]
    m = PartModel(part["id"], j["hub_l"], j["hub_d"], _circle(rb))
    m.axial = [AxialHole(a, h["r_h"], h["d"], -1.0, nest + 1.0) for a in _ang(h["n"])]   # глухие, z 0…nest
    m.axes = [Circle(h["r_h"])]
    m.dims = [Dim(j["hub_d"], "d.09"), Dim(round(2 * rb, 3), "dотв")]
    pl = f"×{h['l']:g}" if h.get("l") else ""
    m.notes = [f"ступица Ø{j['hub_d']:g} × {j['hub_l']:g} под .09, торцом к дну-листу .13 — без фланца "
               f"(CP-83); отверстие Ø{2 * rb:g} под .10 сквозное",
               f"гнёзда {h['n']} × Ø{h['d']:g} глубиной {nest:g} на r {h['r_h']:g} через 360/n — штифты {pl[1:] or ''} "
               "через лист .13; посадка H7; извлечение из глухого гнезда — OQ-29"]
    m.legend = [("L", j["hub_l"], "длина .12 = длина ступицы (ax_gap + B.09 + lip + out_ext)"),
                ("d.09", j["hub_d"], "ступица: посадка .09; выбран с ободом под штифты (CP-83)"),
                ("обод", round(j["hub_d"] / 2 - rb, 2), "(d.09 − D.10)/2 ≥ 2·edge_k·d_h"),
                ("dотв", round(2 * rb, 3), "сквозное под .10 — опору конца входного вала"),
                ("штифты", f"{h['n']}×Ø{h['d']:g}{pl}", "ГОСТ 24296-93, H7, лист–ступица (CP-83)"),
                ("гнездо", nest, "глубина: l − t_s + pin_gap; + pin_wall ≤ L"),
                ("r_h", h["r_h"], "окружность штифтов: d.09/2 − edge_k·d_h")]
    return m


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
    ring = j.get("scheme") == "ring"           # CP-84, Д-97: L4 — лист в расточке обечайки на торце кольца .14
    seat = ("в расточке обечайки .02C на торце кольца .14, заподлицо с торцом обечайки (Д-97); " if ring
            else "к торцу бурта .02B, ")
    m.notes = [f"дно-лист Ø{j['D']:g} × {t:g} — точение из прутка 40Х (Д-93); {seat}"
               + ("фланец .12 — в отверстии бурта под листом, ступица d.09 сквозь лист (Д-94)" if fl
                  else "со стороны выхода — ступица .12 торцом, штифты в гнёзда обода (CP-83)"
                  if h.get("mode") == "direct" else "со стороны выхода — фланец .12"),
               f"отверстия: {j['pin_n']} × Ø{j['pin_d']:g} на r {j['r_j']:g} (бурт), {h['n']} × Ø{h['d']:g} "
               f"на r {h['r_h']:g} (ступица); сквозные H7, через 360/n"]
    m.legend = [("t_s", t, f"толщина листа{crit}; t_s_min {tmin} (Д-93, OQ-27)"),
                ("D", j["D"], f"Ø листа = Ø расточки обечайки .02C, посадка {j.get('fit') or '—'} (Д-97)"
                 if ring else "Ø листа = Ø бурта .02B"),
                ("dотв", round(2 * rb, 3), "под ступицу d.09 (Д-94)" if fl else "под .10"),
                ("шт. кольца" if ring else "шт. бурта", f"{j['pin_n']}×Ø{j['pin_d']:g} r {j['r_j']:g}",
                 "осевые сквозные, сверловка с кольцом .14 в сборе (Д-97)" if ring else "осевые сквозные (CP-79)"),
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
    lo = {"layout": {"ax_gap": 0.5, "output": {"d": 34.0, "l_key": 27.0,
                                               "key": {"b": 10, "h": 8, "t1": 5.0, "t2": 3.3}}}}  # CP-90, Д-102
    bo = build(lo, {"id": "PTK-T.12B-K", "rows": [1], "join": {
        **j, "scheme": "insert", "f": 2.0, "hole12": 7.62, "hub_d": 45.0, "hub_l": 34.5,
        "pin_n": 8, "pin_a": [45.0 * k for k in range(8)]}})
    assert (bo.bands[-1].r_out, bo.bands[-1].z0, bo.bands[-1].op) == (17.0, 18.0, "cut"), bo.bands
    assert len(bo.slots) == 1 and abs(bo.slots[0].r1 - 20.3) < 1e-9 and bo.slots[0].z0 == 18.0, bo.slots
    lo2 = {"sep": {"length": 33.0}, "layout": {**lo["layout"], "covers": {"pocket": [68.9, 15.0]},
           "cup": {"z_in": 36.5}, "b09": {"id": "61809", "d": 45.0, "D": 58.0, "B": 7.0, "da": 47.0}}}
    fb, fs, fl, _ = out_feats(lo2, 11.0, 45.5, 9.5)                                     # CP-90 этап 2b
    assert (fb[0].r_out, fb[0].z0, fb[0].h, fb[0].op) == (23.5, 11.0, 0.5, "add") and len(fs) == 1, fb
    assert [x[0] for x in fl] == ["da", "d_o"], fl
    lf = {"layout": {"output": {"flange": {"n": 6, "r": 16.0, "d_tap": 4.2, "depth": 8.5,
                                            "n_p": 3, "pin_d": 4.0, "pin_depth": 8.0}}}}   # Д-104
    fh = flange_holes(lf, 10.0)
    assert len(fh) == 9 and fh[0].r == 16.0 and abs(fh[6].angle - 30.0) < 1e-9, fh
    assert flange_holes({}, 10.0) == []
    lg = {**lo2, "layout": {**lo2["layout"], "output": {**lo2["layout"]["output"],
          "grooves": {"ext": {"s": 1.7, "m": 1.9, "d2": 42.5}}}}}                        # 2b-3: ГОСТ 13942
    gb = out_feats(lg, 11.0, 45.5, 9.5)[0]
    assert (gb[-1].r_out, gb[-1].z0, gb[-1].h, gb[-1].op) == (23.5, 18.5, 1.9, "cut"), gb
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
    jd = {**jx, "hub_d": 40.0, "hub": {"mode": "direct", "d": 3.0, "n": 12, "r_h": 15.5, "r_f": 20.0,
                                      "h_f": 0.0, "depth": 4.5, "nest": 5.0, "l": 8.0}}    # CP-83
    f3 = build({}, {"id": "PTK-T.12A-K", "rows": [1], "join": jd})
    s3 = build_leaf({}, {"id": "PTK-T.13-K", "rows": [1], "join": jd})
    assert f3.d_out == 40.0 and f3.thick == 10.5 and len(f3.axial) == 12 and not f3.bands, f3
    assert techdraw.extent(f3) == (40.0, 0.0, 10.5), techdraw.extent(f3)
    assert len(s3.axial) == 20 and "Легенда" in svg.render(f3) and "Легенда" in svg.render(s3)
    jl = {**jx, "scheme": "ring", "D": 66.12, "fit": "H7/js6", "r_j": 28.56, "pin_n": 10,
          "pin_a": [36.0 * k + 18.0 for k in range(10)]}                                    # CP-84, Д-97: L4
    s4 = build_leaf({}, {"id": "PTK-T.13-K", "rows": [1], "join": jl})
    assert s4.d_out == 66.12 and len(s4.axial) == 20 and "Д-97" in s4.notes[0], s4
    assert techdraw.extent(s4) == (66.12, 0.0, 3.0), techdraw.extent(s4)
    js = {**jx, "seat": True, "hub_d": 45.0, "hub_l": 10.5}                                # 2b-3, Д-102 п. 2
    g5 = build({}, {"id": "PTK-T.12A-K", "rows": [1], "join": js})
    assert g5.thick == 3.0 and g5.d_out == 69.88 and len(g5.pins) == 8 and not g5.axial, g5
    assert [(x.z0, x.h) for x in g5.bands] == [(3.0, 10.5)], g5.bands
    assert techdraw.extent(g5) == (69.88, 0.0, 13.5) and "Легенда" in svg.render(g5), techdraw.extent(g5)
    return True
