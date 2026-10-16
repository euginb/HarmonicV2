"""Конструктивы ПТК, шаг 2 (Д-55, CP-42): опоры .09/.10, кольца .11, крышки .07, заготовка .02.

Конструктив — набор деталей из products.yaml → PTK.layouts. Реализована схема
fixed = ring, output = cage: выход — сепаратор (стакан .02 в L1, обечайка .02 + ступица .12 в L2).
Ступица выхода полая: снаружи .09, внутри .10 (опора входного вала); кручение
τ = 16·M/(π·d³·(1 − β⁴)), β = D.10/d.09. Нагрузки опор по C0 не проверяются (OQ-17).
"""
import math
import re

from egm import materials as MAT

SUP = {"tau_allow": 25.0, "hub_wall": 2.0, "seat_wall": 2.0, "ring_w": 2.0,
       "lip": 1.0, "cup_t": 2.0, "ax_gap": 0.5, "nut_h": 4.0, "out_ext": 2.0}
HEAD = ("| Проработка | Конструктив | Детали | .09 d×D×B | τ ступицы / [τ], МПа | .10 d×D×B | "
        ".11 n × h, мм | Крышки tA / tB, мм | Дно .02 z / t, мм; ступица | Длина, мм | Заготовка .02: марка, формы |")
RULE = "|---" * 11 + "|"
TOOL_HEAD = "| Проработка | Оснастка (Д-57) | Деталь | Размер | Маршрут |"
TOOL_RULE = "|---" * 5 + "|"


def bolt_clear(cid):
    """Ø отверстия под болт по ID (сегмент крепления 8M4P2) — ISO 273 средний ряд, ≈ 1.1·M + 0.1."""
    m = re.search(r"-\d+M(\d+)P", cid)
    return 1.1 * float(m.group(1)) + 0.1 if m else 0.0


def _brgs(bears):
    return sorted(((v["D"], v["d"], k) for k, v in bears.items() if isinstance(v, dict)))


def pick_brg(bears, d_min):
    """Наименьший подшипник с d ≥ d_min -> {'id', d, D, B, ...} | None."""
    for _, d, k in _brgs(bears):
        if d >= d_min - 1e-9:
            return {"id": k, **bears[k]}
    return None


def hub_brg(bears, M, D10, o, D_max):
    """.09 на полой ступице: d ≥ D.10 + 2·hub_wall, D ≤ D_max, τ ≤ [τ] -> (подшипник, τ) | (None, None)."""
    for _, d, k in _brgs(bears):
        if d < D10 + 2 * o["hub_wall"] - 1e-9 or bears[k]["D"] > D_max + 1e-9:
            continue
        tau = 16 * M * 1e3 / (math.pi * d ** 3 * (1 - (D10 / d) ** 4))
        if tau <= o["tau_allow"] + 1e-9:
            return {"id": k, **bears[k]}, tau
    return None, None


def _fit(forms, Dn, Dv, need):
    """Формы одной марки -> (труба | None, лист | None, пруток | None)."""
    tubes = sorted((t for t in forms.get("tubes", [])
                    if t["D"] >= Dn - 1e-9 and t["D"] - 2 * t["s"] <= Dv + 1e-9),
                   key=lambda t: (t["D"], t["s"]))
    sheets = sorted(s for s in forms.get("sheets", []) if s >= need - 1e-9)
    bars = sorted(b for b in forms.get("bars", []) if b >= Dn - 1e-9)
    return tubes[0] if tubes else None, sheets[0] if sheets else None, bars[0] if bars else None


def blanks(r_in, r_out, stock, mats=None):
    """Заготовка .02 из stock.yaml (Д-56, Д-67): марки — по порядку mats (products.yaml →
    PTK.parts."02".material); берётся первая марка с подходящей формой: труба, лист
    (обечайка со швом), пруток (стакан монолитом); прочие подходящие — alt.
    Без mats — все марки stock.yaml; старый формат без марок — марка None."""
    if not stock:
        return None
    ta, sa = float(stock.get("tube_allow", 0.5)), float(stock.get("sheet_allow", 0.3))
    Dn, Dv, need = 2 * r_out + 2 * ta, 2 * r_in - 2 * ta, r_out - r_in + 2 * sa
    by = MAT.stock_by_material(stock)
    tried = [str(m) for m in mats] if mats else [m for m in by if m is not None]
    order = [None] if None in by else [m for m in tried if m in by]
    fits = {}
    for m in order:
        f = _fit(by[m], Dn, Dv, need)
        if any(x is not None for x in f):
            fits[m] = f
    pick = next(iter(fits), None)
    tube, sheet, bar = fits.get(pick, (None, None, None))
    return {"material": pick, "alt": [m for m in fits if m != pick], "tried": tried,
            "tube": tube, "tube_need": [round(Dn, 2), round(Dv, 2)],
            "sheet": sheet, "sheet_need": round(need, 2),
            "sheet_len": round(math.pi * (r_in + r_out), 1), "bar": bar}


def axial(width, row_gap, b09, b10, r_out, cfg, o, covers):
    """Осевая компоновка (Д-57); z = 0 — торец пакета со стороны входа, W — длина пакета.

    .07A [−tA, 0]: гнездо .10, tA = B.10 + lip. Гайка пакета эксцентриков — за последним рядом,
    поэтому дно стакана изнутри на z_b = max(W, W − row_gap + nut_h) + ax_gap. .07B [W, W + tB]:
    карман под дно Ø 2(r_out + ax_gap) глубиной z_b + cup_t + ax_gap − W, за ним гнездо .09
    и буртик: tB = карман + B.09 + lip. Ступица d.09, длина ax_gap + B.09 + lip + out_ext;
    отверстие ступицы D.10 сквозь дно — второй .10 на конце входного вала."""
    warn = []
    B09, B10 = (b09 or {}).get("B", 0.0), (b10 or {}).get("B", 0.0)
    D10 = (b10 or {}).get("D", 0.0)
    z_b = max(width, width - row_gap + o["nut_h"]) + o["ax_gap"]
    pocket = z_b + o["cup_t"] + o["ax_gap"] - width
    hub_l = o["ax_gap"] + B09 + o["lip"] + o["out_ext"]
    if B10 > o["cup_t"] + hub_l + 1e-9:
        warn.append(f".10 в ступице: B = {B10:g} > длины отверстия {o['cup_t'] + hub_l:g} мм")
    cov = None
    if covers:
        r_pk = r_out + o["ax_gap"]
        r_lim = float(cfg["d_bc"]) / 2 - bolt_clear(cfg["id"]) / 2 - o["seat_wall"]
        if r_pk > r_lim + 1e-9:
            warn.append(f".07B: карман под дно .02 r {r_pk:.2f} > {r_lim:.2f} мм — "
                        f"стенка до отверстий крепежа < seat_wall")
        cov = {"tA": round(B10 + o["lip"], 2), "tB": round(pocket + B09 + o["lip"], 2),
               "D": cfg["d_out"], "seat_A": D10, "seat_B": (b09 or {}).get("D"),
               "pocket": [round(2 * r_pk, 2), round(pocket, 2)]}
    cup = {"z_in": round(z_b, 2), "t": o["cup_t"], "hub_d": (b09 or {}).get("d"),
           "hub_bore": D10, "hub_l": round(hub_l, 2)}
    length = (cov["tA"] + cov["tB"] if cov else 0.0) + width + o["out_ext"]
    return {"covers": cov, "cup": cup, "length": round(length, 2)}, warn


def tooling(rec, cfg, r_in, r_out):
    """Оснастка (Д-57) -> [{fx, part, size, route}]: требования калькулятора, не конструкция FX."""
    out = [{"fx": "разжимная оправка", "part": ".02",
            "size": f"Ø{2 * r_in:.2f} по dc, длина ≥ {float(cfg['width']):g}",
            "route": "точение Dc, окна, контроль — все маршруты тонкой стенки"}]
    if rec["parts"].get("02") == "sleeve":
        t = (rec.get("blank") or {}).get("sheet")
        rm = (r_in + r_out) / 2
        out += [{"fx": "вальцовка", "part": ".02",
                 "size": (f"лист {t:g}, " if t else "") + f"r ср {rm:.2f}", "route": "weld: из листа"},
                {"fx": "сварочная оправка с медной подкладкой", "part": ".02",
                 "size": f"Ø{2 * r_in:.2f} − 2·sheet_allow", "route": "weld: стык на канавке подкладки"},
                {"fx": "калибровочная оправка (раздача)", "part": ".02",
                 "size": f"Ø{2 * r_in:.2f} − 2·sheet_allow", "route": "weld: после сварки, до отпуска"}]
    var = {}
    for ph in cfg["phasing"]:
        v = ph.get("variant", "A")
        var[v] = var.get(v, 0) + 1
    pk = ", ".join(f"{k}×{n}" for k, n in sorted(var.items()))
    out.append({"fx": "пакетная оправка венцов", "part": ".01",
                "size": f"по отв. Dотв {float(cfg['d_bc']):g} (Д-16); пакеты {pk}",
                "route": ("профиль ЭЭС пакетом в сборе" if len(var) == 1 else
                          f"профиль ЭЭС пакетами по вариантам ({len(var)}); 1 вариант — Д-57")})
    return out


def md_tool(name, r):
    """Строки таблицы «Оснастка» SPEC-11."""
    return [f"| {name} | {t['fx']} | {t['part']} | {t['size']} | {t['route']} |"
            for t in r.get("tooling", [])]


def cad_parts(cfg, name, rec):
    """Детали конструктива для egm.cad (CP-45): .02A стакан | .02B обечайка, .07A/.07B, .11.

    ID — <ID>.<NN><вар>-<проработка>, base — без суффикса (Д-48); покупные .09/.10 — в rec."""
    cid = cfg["id"]
    rows = [ph.get("row", k + 1) for k, ph in enumerate(cfg["phasing"])]
    sfx, out, v02 = (f"-{name}" if name else ""), [], rec["parts"].get("02")
    if v02 in ("cup", "sleeve"):
        base = f"{cid}.02{'A' if v02 == 'cup' else 'B'}"
        out.append({"id": base + sfx, "base": base, "rows": rows,
                    **({"cup": rec["cup"]} if v02 == "cup" else {})})
    if rec.get("covers"):
        out += [{"id": f"{cid}.07{s}{sfx}", "base": f"{cid}.07{s}", "rows": rows, "side": s}
                for s in "AB"]
    if rec.get("r11"):
        out.append({"id": f"{cid}.11{sfx}", "base": f"{cid}.11", "rows": rows})
    return out


def layout(cfg, d, ecc, shaft_d, row_gap, prods=None, bears=None, stock=None):
    """Конструктив проработки -> (запись | None, ошибки, предупреждения)."""
    code = d.get("layout", "L1")
    lay = (prods or {}).get("PTK", {}).get("layouts", {}).get(code)
    if lay is None:
        return None, [f"конструктив {code}: нет в products.yaml → PTK.layouts (Д-55)"], []
    if lay.get("fixed") != "ring" or lay.get("output") != "cage":
        return None, [f"конструктив {code}: реализован только fixed = ring, output = cage"], []
    err, warn = [], ["нагрузки опор .09/.10 по C0 не проверяются (OQ-17)"]
    o, bears = {**SUP, **d.get("supports", {})}, bears or {}
    pr = {k: v for k, v in lay.get("parts", {}).items() if v}
    M, rows, a = float(cfg.get("M") or 0.0), len(cfg["phasing"]), float(cfg["a_w"])
    b10 = pick_brg(bears, shaft_d)
    if b10 is None:
        err.append(f".10: нет подшипника с d ≥ {shaft_d:g} мм в vendor_prices.yaml → bearings")
    D10 = b10["D"] if b10 else shaft_d
    D_max = float(cfg["d_bc"]) - bolt_clear(cfg["id"]) - 2 * o["seat_wall"]
    b09, tau = hub_brg(bears, M, D10, o, D_max)
    if b09 is None:
        err.append(f".09: нет подшипника с d ≥ {D10 + 2 * o['hub_wall']:g}, D ≤ {D_max:.1f} мм "
                   f"(гнездо в .07B внутри крепежа Ø{float(cfg['d_bc']):g}) и τ ступицы ≤ "
                   f"{o['tau_allow']:g} МПа в vendor_prices.yaml → bearings")
    width = float(cfg["width"])
    pitch = (width - (rows + 1) * row_gap) / rows
    r11 = None
    if "11" in pr:
        d11 = min(shaft_d + 2 * o["ring_w"], ecc["De"] - 2 * a - 1.0)
        r11 = {"n": rows - 1, "h": round(row_gap + pitch - ecc["t"], 2), "d_in": shaft_d,
               "d_out": round(d11, 2)}
        if d11 < shaft_d + 1.0:
            warn.append(f".11: Ø нар. {d11:.2f} — опорный поясок меньше 0.5 мм")
    if "12" in pr:
        warn.append(f"{code}: соединение .02–.12 (сварка | винты | штифты) не считается (OQ-12)")
    sep = cfg.get("sep") or {}
    r_in = float(sep.get("r_in", cfg["R_sum"] - 1.1 * a))
    r_out = float(sep.get("r_out", cfg["R_sum"] + 1.1 * a))
    ax, aw = axial(width, row_gap, b09, b10, r_out, cfg, o, "07" in pr)
    warn += aw
    bl = blanks(r_in, r_out, stock, MAT.part_materials(prods, "PTK", "02"))
    if bl is not None and not (bl["tube"] or bl["sheet"] or bl["bar"]):
        warn.append(".02: нет заготовки" + (f" из {', '.join(bl['tried'])}" if bl["tried"] else "")
                    + f" в stock.yaml (труба Ø ≥ {bl['tube_need'][0]:g} с отв. ≤ "
                    f"{bl['tube_need'][1]:g}, лист ≥ {bl['sheet_need']:g}, пруток Ø ≥ {bl['tube_need'][0]:g})")
    rec = {"code": code, "name": lay.get("name", ""), "parts": pr, "b09": b09, "b10": b10,
           "tau_hub": round(tau, 1) if tau is not None else None, "tau_allow": o["tau_allow"],
           "r11": r11, "covers": ax["covers"], "cup": ax["cup"], "length": ax["length"],
           "blank": bl}
    rec["tooling"] = tooling(rec, cfg, r_in, r_out)
    rec.update(shaft_d=shaft_d, ax_gap=o["ax_gap"])
    rec["cad_parts"] = cad_parts(cfg, d.get("name", ""), rec)
    return rec, err, warn


def _b(b):
    return f"{b['id']} {b['d']:g}×{b['D']:g}×{b['B']:g}" if b else "нет"


def md_row(name, r):
    """Строка таблицы «Конструктив» SPEC-11."""
    bl, s = r["blank"], []
    if bl:
        s += [f"труба {bl['tube']['D']:g}×{bl['tube']['s']:g}"] if bl["tube"] else []
        s += [f"лист {bl['sheet']:g}, L {bl['sheet_len']:g}"] if bl["sheet"] else []
        s += [f"пруток Ø{bl['bar']:g}"] if bl["bar"] else []
        if bl.get("material") and s:
            s = [f"{bl['material']}: {s[0]}"] + s[1:]
        if bl.get("alt"):
            s.append("также " + ", ".join(bl["alt"]))
    tau = f"{r['tau_hub']:g} / {r['tau_allow']:g}" if r["tau_hub"] is not None else "—"
    r11 = f"{r['r11']['n']} × {r['r11']['h']:g}" if r["r11"] else "—"
    cov = f"{r['covers']['tA']:g} / {r['covers']['tB']:g}" if r["covers"] else "—"
    c = r["cup"]
    cup = f"{c['z_in']:g} / {c['t']:g}" + (f"; Ø{c['hub_d']:g}×{c['hub_l']:g}" if c["hub_d"] else "")
    return (f"| {name} | {r['code']} — {r['name']} | {', '.join('.' + k for k in sorted(r['parts']))} | "
            f"{_b(r['b09'])} | {tau} | {_b(r['b10'])} | {r11} | {cov} | {cup} | {r['length']:g} | "
            f"{'; '.join(s) or ('нет stock.yaml' if bl is None else 'нет')} |")


def self_test():
    """L1 для PTK-050/61810: .10 = 61800, .09 = 61806 (τ ступицы), .11 1×3 шт; заготовки; ошибки."""
    bears = {"_comment": "x", "61800": {"d": 10.0, "D": 19.0, "B": 5.0},
             "61804": {"d": 20.0, "D": 32.0, "B": 7.0}, "61805": {"d": 25.0, "D": 37.0, "B": 7.0},
             "61806": {"d": 30.0, "D": 42.0, "B": 7.0}, "61810": {"d": 50.0, "D": 65.0, "B": 7.0}}
    prods = {"PTK": {"layouts": {
        "L1": {"name": "стакан", "fixed": "ring", "output": "cage",
               "parts": {"02": "cup", "07": "side", "09": "out", "10": "in", "11": "ring", "12": None}},
        "L2": {"name": "обечайка", "fixed": "ring", "output": "cage",
               "parts": {"02": "sleeve", "07": "side", "09": "out", "10": "in", "11": "ring", "12": "hub"}}}}}
    stock = {"tubes": [{"D": 70.0, "s": 5.0}, {"D": 70.0, "s": 2.5}, {"D": 68.0, "s": 1.0}],
             "sheets": [1.0, 1.2, 1.5, 2.0], "bars": [65.0, 70.0, 75.0]}
    cfg = {"id": "PTK-T-8M4P2-AAAAAA", "M": 100.0, "phasing": [{"row": k + 1} for k in range(4)],
           "a_w": 0.4, "R_sum": 33.5,
           "d_bc": 80.0, "d_out": 90.0, "width": 33.0}
    ecc = {"De": 50.0, "t": 7.0}
    r, e, w = layout(cfg, {"layout": "L1"}, ecc, 10.0, 1.0, prods, bears, stock)
    assert not e, e
    assert r["b10"]["id"] == "61800" and r["b09"]["id"] == "61806", (r["b09"], r["b10"])
    assert abs(r["tau_hub"] - 22.5) < 0.2, r["tau_hub"]
    assert r["r11"] == {"n": 3, "h": 1.0, "d_in": 10.0, "d_out": 14.0}, r["r11"]
    assert r["length"] == 55.0 and "12" not in r["parts"], r["length"]
    assert r["covers"]["tA"] == 6.0 and r["covers"]["tB"] == 14.0, r["covers"]
    assert r["cup"]["z_in"] == 36.5 and r["cup"]["hub_l"] == 10.5, r["cup"]
    assert [t["fx"] for t in r["tooling"]] == ["разжимная оправка", "пакетная оправка венцов"], \
        r["tooling"]
    assert "пакетом в сборе" in r["tooling"][-1]["route"] and len(md_tool("K10", r)) == 2
    b = r["blank"]
    assert b["tube"] == {"D": 70.0, "s": 2.5} and b["sheet"] == 1.5 and b["bar"] == 70.0, b
    st2 = {"tube_allow": 0.5, "sheet_allow": 0.3,
           "materials": {"08пс": {"sheets": [3.0]}, "40Х": {"bars": [70.0]},
                         "40ХН2МА": {"tubes": [{"D": 73.0, "s": 14.0}]}}}
    b2 = blanks(32.5, 34.0, st2, ["40ХН2МА", "40Х"])
    assert (b2["material"], b2["tube"]["D"], b2["alt"], b2["sheet"]) == \
        ("40ХН2МА", 73.0, ["40Х"], None), b2
    b3 = blanks(32.5, 34.0, st2, ["20ХН3А"])
    assert b3["material"] is None and not (b3["tube"] or b3["sheet"] or b3["bar"]), b3
    b4 = blanks(32.5, 34.0, st2)
    assert b4["material"] == "08пс" and b4["sheet"] == 3.0, b4
    assert "61806" in md_row("K10", r)
    ids = [q["id"] for q in r["cad_parts"]]                                   # CP-45
    assert ids == ["PTK-T-8M4P2-AAAAAA.02A", "PTK-T-8M4P2-AAAAAA.07A", "PTK-T-8M4P2-AAAAAA.07B",
                   "PTK-T-8M4P2-AAAAAA.11"], ids
    assert r["cad_parts"][0]["rows"] == [1, 2, 3, 4] and r["cad_parts"][0]["cup"] == r["cup"]
    assert cad_parts({"id": "X", "phasing": [{}] * 2}, "K", r)[1]["id"] == "X.07A-K"
    r2, e2, w2 = layout(cfg, {"layout": "L2"}, ecc, 10.0, 1.0, prods, bears, stock)
    assert not e2 and any("OQ-12" in x for x in w2), w2
    assert any("медной" in t["fx"] for t in r2["tooling"]), r2["tooling"]
    assert any(t["fx"] == "вальцовка" and "лист 1.5" in t["size"] for t in r2["tooling"])
    _, e3, _ = layout({**cfg, "d_bc": 40.0}, {"layout": "L1"}, ecc, 10.0, 1.0, prods, bears, stock)
    assert any(".09" in x for x in e3), e3
    _, e4, _ = layout(cfg, {"layout": "L9"}, ecc, 10.0, 1.0, prods, bears, stock)
    assert e4 and "L9" in e4[0], e4
    assert layout(cfg, {}, ecc, 10.0, 1.0, prods, bears, None)[0]["blank"] is None
    return True
