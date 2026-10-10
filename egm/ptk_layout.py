"""Конструктивы ПТК, шаг 2 (Д-55, CP-42): опоры .09/.10, кольца .11, крышки .07, заготовка .02.

Конструктив — набор деталей из products.json → PTK.layouts. Реализована схема
fixed = ring, output = cage: выход — сепаратор (стакан .02 в L1, обечайка .02 + ступица .12 в L2).
Ступица выхода полая: снаружи .09, внутри .10 (опора входного вала); кручение
τ = 16·M/(π·d³·(1 − β⁴)), β = D.10/d.09. Нагрузки опор по C0 не проверяются (OQ-17).
"""
import math
import re

SUP = {"tau_allow": 25.0, "hub_wall": 2.0, "seat_wall": 2.0, "cover_t": 5.0, "ring_w": 2.0}
HEAD = ("| Проработка | Конструктив | Детали | .09 d×D×B | τ ступицы / [τ], МПа | .10 d×D×B | "
        ".11 n × h, мм | Крышки t, мм | Длина, мм | Заготовка .02 |")


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


def blanks(r_in, r_out, stock):
    """Заготовка .02 из stock.json: труба, лист (обечайка со швом), пруток (стакан монолитом)."""
    if not stock:
        return None
    ta, sa = float(stock.get("tube_allow", 0.5)), float(stock.get("sheet_allow", 0.3))
    Dn, Dv, need = 2 * r_out + 2 * ta, 2 * r_in - 2 * ta, r_out - r_in + 2 * sa
    tubes = sorted((t for t in stock.get("tubes", [])
                    if t["D"] >= Dn - 1e-9 and t["D"] - 2 * t["s"] <= Dv + 1e-9),
                   key=lambda t: (t["D"], t["s"]))
    sheets = sorted(s for s in stock.get("sheets", []) if s >= need - 1e-9)
    bars = sorted(b for b in stock.get("bars", []) if b >= Dn - 1e-9)
    return {"tube": tubes[0] if tubes else None, "tube_need": [round(Dn, 2), round(Dv, 2)],
            "sheet": sheets[0] if sheets else None, "sheet_need": round(need, 2),
            "sheet_len": round(math.pi * (r_in + r_out), 1), "bar": bars[0] if bars else None}


def layout(cfg, d, ecc, shaft_d, row_gap, prods=None, bears=None, stock=None):
    """Конструктив проработки -> (запись | None, ошибки, предупреждения)."""
    code = d.get("layout", "L1")
    lay = (prods or {}).get("PTK", {}).get("layouts", {}).get(code)
    if lay is None:
        return None, [f"конструктив {code}: нет в products.json → PTK.layouts (Д-55)"], []
    if lay.get("fixed") != "ring" or lay.get("output") != "cage":
        return None, [f"конструктив {code}: реализован только fixed = ring, output = cage"], []
    err, warn = [], ["нагрузки опор .09/.10 по C0 не проверяются (OQ-17)"]
    o, bears = {**SUP, **d.get("supports", {})}, bears or {}
    pr = {k: v for k, v in lay.get("parts", {}).items() if v}
    M, rows, a = float(cfg.get("M") or 0.0), len(cfg["phasing"]), float(cfg["a_w"])
    b10 = pick_brg(bears, shaft_d)
    if b10 is None:
        err.append(f".10: нет подшипника с d ≥ {shaft_d:g} мм в vendor_prices.json → bearings")
    D10 = b10["D"] if b10 else shaft_d
    D_max = float(cfg["d_bc"]) - bolt_clear(cfg["id"]) - 2 * o["seat_wall"]
    b09, tau = hub_brg(bears, M, D10, o, D_max)
    if b09 is None:
        err.append(f".09: нет подшипника с d ≥ {D10 + 2 * o['hub_wall']:g}, D ≤ {D_max:.1f} мм "
                   f"(гнездо в .07B внутри крепежа Ø{float(cfg['d_bc']):g}) и τ ступицы ≤ "
                   f"{o['tau_allow']:g} МПа в vendor_prices.json → bearings")
    width = float(cfg["width"])
    pitch = (width - (rows + 1) * row_gap) / rows
    r11 = None
    if "11" in pr:
        d11 = min(shaft_d + 2 * o["ring_w"], ecc["De"] - 2 * a - 1.0)
        r11 = {"n": rows - 1, "h": round(row_gap + pitch - ecc["t"], 2), "d_in": shaft_d,
               "d_out": round(d11, 2)}
        if d11 < shaft_d + 1.0:
            warn.append(f".11: Ø нар. {d11:.2f} — опорный поясок меньше 0.5 мм")
    cov = None
    if "07" in pr:
        cov = {"t": o["cover_t"], "D": cfg["d_out"], "seat_A": D10, "seat_B": b09["D"] if b09 else None}
    if "12" in pr:
        warn.append(f"{code}: соединение .02–.12 (сварка | винты | штифты) не считается (OQ-12)")
    sep = cfg.get("sep") or {}
    r_in = float(sep.get("r_in", cfg["R_sum"] - 1.1 * a))
    r_out = float(sep.get("r_out", cfg["R_sum"] + 1.1 * a))
    bl = blanks(r_in, r_out, stock)
    if bl is not None and not (bl["tube"] or bl["sheet"] or bl["bar"]):
        warn.append(f".02: нет заготовки в stock.json (труба Ø ≥ {bl['tube_need'][0]:g} с отв. ≤ "
                    f"{bl['tube_need'][1]:g}, лист ≥ {bl['sheet_need']:g}, пруток Ø ≥ {bl['tube_need'][0]:g})")
    rec = {"code": code, "name": lay.get("name", ""), "parts": pr, "b09": b09, "b10": b10,
           "tau_hub": round(tau, 1) if tau is not None else None, "tau_allow": o["tau_allow"],
           "r11": r11, "covers": cov, "length": round(width + 2 * o["cover_t"] * bool(cov), 2),
           "blank": bl}
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
    tau = f"{r['tau_hub']:g} / {r['tau_allow']:g}" if r["tau_hub"] is not None else "—"
    r11 = f"{r['r11']['n']} × {r['r11']['h']:g}" if r["r11"] else "—"
    cov = f"{r['covers']['t']:g}" if r["covers"] else "—"
    return (f"| {name} | {r['code']} — {r['name']} | {', '.join('.' + k for k in sorted(r['parts']))} | "
            f"{_b(r['b09'])} | {tau} | {_b(r['b10'])} | {r11} | {cov} | {r['length']:g} | "
            f"{'; '.join(s) or ('нет stock.json' if bl is None else 'нет')} |")


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
    cfg = {"id": "PTK-T-8M4P2-AAAAAA", "M": 100.0, "phasing": [{}] * 4, "a_w": 0.4, "R_sum": 33.5,
           "d_bc": 80.0, "d_out": 90.0, "width": 33.0}
    ecc = {"De": 50.0, "t": 7.0}
    r, e, w = layout(cfg, {"layout": "L1"}, ecc, 10.0, 1.0, prods, bears, stock)
    assert not e, e
    assert r["b10"]["id"] == "61800" and r["b09"]["id"] == "61806", (r["b09"], r["b10"])
    assert abs(r["tau_hub"] - 22.5) < 0.2, r["tau_hub"]
    assert r["r11"] == {"n": 3, "h": 1.0, "d_in": 10.0, "d_out": 14.0}, r["r11"]
    assert r["length"] == 43.0 and "12" not in r["parts"], r
    b = r["blank"]
    assert b["tube"] == {"D": 70.0, "s": 2.5} and b["sheet"] == 1.5 and b["bar"] == 70.0, b
    assert "61806" in md_row("K10", r)
    r2, e2, w2 = layout(cfg, {"layout": "L2"}, ecc, 10.0, 1.0, prods, bears, stock)
    assert not e2 and any("OQ-12" in x for x in w2), w2
    _, e3, _ = layout({**cfg, "d_bc": 40.0}, {"layout": "L1"}, ecc, 10.0, 1.0, prods, bears, stock)
    assert any(".09" in x for x in e3), e3
    _, e4, _ = layout(cfg, {"layout": "L9"}, ecc, 10.0, 1.0, prods, bears, stock)
    assert e4 and "L9" in e4[0], e4
    assert layout(cfg, {}, ecc, 10.0, 1.0, prods, bears, None)[0]["blank"] is None
    return True
