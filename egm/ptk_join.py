"""Соединение обечайки .02B со ступицей выхода .12, конструктив L2 (Д-72, OQ-12).

Схемы:
  collar — бурт на обечайке .02B (толстостенная труба): поясок .12 входит в отверстие бурта,
           радиальные штифты через бурт в поясок;
  insert — обечайка без бурта (стенка как у окон): дно-ступица .12 вставляется внутрь обечайки,
           бурт — на .12 (упор в торец обечайки); радиальные штифты через стенку обечайки в дно —
           на той же поверхности, что и окна, по делению окон (одна установка SM-1, ось C).
Момент передают штифты (100 %); натяг / анаэробный фиксатор — резерв, в расчёт не входит.
F = M / r_j; τ = F / (n·π·d²/4); σсм стенки = F / (n·d·t); σсм ступицы = F / (n·d·h), h = pin_depth_k·d;
срез стенки к торцу τe = F / (n·2·(e − d/2)·t), e = edge_k·d; длина пояса L = 2·e.
Схема выбирается по доступности труб: марки .02 по порядку, для марки — первая схема join_order.
"""
import math

from egm import materials as MAT

JOIN = {"join": "auto", "join_order": ["collar", "insert"], "pin_d": [3.0, 4.0, 5.0],
        "pin_n": [4, 6, 8, 10, 12, 16], "edge_k": 1.5, "pin_depth_k": 1.5, "pin_web": 2.0,
        "tau_pin": 80.0, "sig_wall": 150.0, "sig_hub": 150.0, "c_in": 1.0, "c_out": 1.0}
SCHEMES = ("collar", "insert")


def tube_ok(t, Dn, Dv, st=None):
    """Труба покрывает деталь с припуском (Dn, Dv) с учётом допусков ГОСТ из stock.yaml:
    D·(1 − tube_tol_D) ≥ Dn и отв. max = D·(1 + tube_tol_D) − 2·s·(1 − tube_tol_s) ≤ Dv."""
    st = st or {}
    td, ts = float(st.get("tube_tol_D", 0.0)), float(st.get("tube_tol_s", 0.0))
    return (t["D"] * (1 - td) >= Dn - 1e-9
            and t["D"] * (1 + td) - 2 * t["s"] * (1 - ts) <= Dv + 1e-9)


def geometry(scheme, r_in, r_out, o):
    """Схема -> {r_j — радиус стыка, t — стенка под штифтом, D, d — габарит .02B в зоне стыка}."""
    if scheme == "collar":
        d_in, d_out = 2 * r_in - 2 * o["c_in"], 2 * r_out + 2 * o["c_out"]
        return {"r_j": d_in / 2, "t": (d_out - d_in) / 2, "D": d_out, "d": d_in}
    return {"r_j": r_in, "t": r_out - r_in, "D": 2 * r_out, "d": 2 * r_in}


def check(M, g, d, n, o):
    """n штифтов Ø d -> (напряжения, нарушения)."""
    F = M * 1e3 / g["r_j"]
    e, h, t = o["edge_k"] * d, o["pin_depth_k"] * d, g["t"]
    s = {"F": F, "tau": F / (n * math.pi * d * d / 4), "sig_wall": F / (n * d * t),
         "sig_hub": F / (n * d * h), "tau_edge": F / (n * 2 * max(e - d / 2, 1e-6) * t),
         "L": 2 * e, "pitch": 2 * math.pi * g["r_j"] / n}
    bad = [k for k, lim in (("tau", o["tau_pin"]), ("sig_wall", o["sig_wall"]),
                            ("sig_hub", o["sig_hub"]), ("tau_edge", 0.6 * o["sig_wall"]))
           if s[k] > lim + 1e-9]
    if s["pitch"] < d + o["pin_web"] - 1e-9:
        bad.append("pitch")
    return s, bad


def pins(M, g, o, n_win=None):
    """Наименьший Ø, затем наименьшее n; при n_win — n | n_win (деление окон) -> dict | None."""
    for d in sorted(o["pin_d"]):
        ok = [n for n in sorted(o["pin_n"]) if not check(M, g, d, n, o)[1]]
        if n_win:
            ok = [n for n in ok if int(n_win) % n == 0] or ok
        if ok:
            s, _ = check(M, g, d, ok[0], o)
            return {"d": d, "n": ok[0], **{k: round(v, 1) for k, v in s.items()}}
    return None


def _area(t):
    return t["D"] ** 2 - (t["D"] - 2 * t["s"]) ** 2


def choose(M, r_in, r_out, stock, mats=None, opt=None, n_win=None):
    """Схема по доступности заготовок -> {pick | None, variants, tried, lim}."""
    o = {**JOIN, **(opt or {})}
    order = [o["join"]] if o["join"] in SCHEMES else [s for s in o["join_order"] if s in SCHEMES]
    by = MAT.stock_by_material(stock) if stock else {}
    tried = [str(m) for m in mats] if mats else [m for m in by if m is not None]
    tried = [None] if None in by else [m for m in tried if m in by]
    ta = float((stock or {}).get("tube_allow", 0.5))
    var = []
    for s in order:
        g = geometry(s, r_in, r_out, o)
        need = [round(g["D"] + 2 * ta, 2), round(g["d"] - 2 * ta, 2)]
        fit = {}
        for m in tried:
            ts = [t for t in (by.get(m) or {}).get("tubes", []) if tube_ok(t, *need, stock)]
            if ts:
                fit[m] = min(ts, key=_area)
        var.append({"scheme": s, "geom": {k: round(v, 2) for k, v in g.items()},
                    "pins": pins(M, g, o, n_win), "need": need, "fit": fit})
    pick = next(({"scheme": v["scheme"], "material": m, "tube": v["fit"][m], "pins": v["pins"],
                  "geom": v["geom"]} for m in tried for v in var if v["pins"] and m in v["fit"]),
                None)
    return {"pick": pick, "variants": var, "tried": tried,
            "lim": {"sig_wall": o["sig_wall"], "tau_pin": o["tau_pin"]}}


def why(jn):
    """Причины отказа по схемам."""
    out = []
    for v in jn["variants"]:
        p = "" if v["pins"] else "штифты не проходят"
        t = "" if v["fit"] else (f"нет трубы Ø ≥ {v['need'][0]:g} с отв. ≤ {v['need'][1]:g}"
                                 + (f" из {', '.join(map(str, jn['tried']))}"
                                    if any(jn["tried"]) else ""))
        out.append(f"{v['scheme']}: " + ("; ".join(x for x in (p, t) if x) or "нет марки"))
    return " | ".join(out) + " (Д-72)"


def short(jn):
    """Текст для SPEC-11."""
    p = jn["pick"]
    if p is None:
        return "соединение .02–.12: нет (Д-72)"
    t, q = p["tube"], p["pins"]
    m = f"{p['material']} " if p["material"] else ""
    return (f"соединение {p['scheme']}: {m}труба {t['D']:g}×{t['s']:g}, {q['n']}×Ø{q['d']:g}, "
            f"σсм {q['sig_wall']:g}/{jn['lim']['sig_wall']:g} МПа, пояс {q['L']:g} мм")


def self_test():
    """PTK-050 (r 33.06…33.94, M 100): collar — 73×7, 6×Ø3; insert — 73×5, 8×Ø3; выбор по наличию."""
    st = {"tube_allow": 0.5, "sheet_allow": 0.3, "tube_tol_D": 0.008, "tube_tol_s": 0.15,
          "materials": {"40Х": {"tubes": [{"D": 73.0, "s": 5.0}, {"D": 73.0, "s": 7.0}]}}}
    r_in, r_out = 33.06, 33.94
    assert tube_ok({"D": 73.0, "s": 5.0}, 68.88, 65.12, st)
    assert not tube_ok({"D": 73.0, "s": 5.0}, 70.88, 63.12, st)
    assert tube_ok({"D": 73.0, "s": 5.0}, 70.88, 63.12)
    p = choose(100.0, r_in, r_out, st, ["40Х"])["pick"]
    assert (p["scheme"], p["tube"]["s"], p["pins"]["d"], p["pins"]["n"]) == ("collar", 7.0, 3.0, 6), p
    j2 = choose(100.0, r_in, r_out, st, ["40Х"], {"join": "insert"})
    p2 = j2["pick"]
    assert (p2["scheme"], p2["tube"]["s"], p2["pins"]["n"]) == ("insert", 5.0, 8), p2
    assert "8×Ø3" in short(j2), short(j2)
    st1 = {**st, "materials": {"40Х": {"tubes": [{"D": 73.0, "s": 5.0}]}}}
    assert choose(100.0, r_in, r_out, st1, ["40Х"])["pick"]["scheme"] == "insert"
    j3 = choose(100.0, r_in, r_out, st1, ["40ХН2МА"])
    assert j3["pick"] is None and "нет трубы" in why(j3), why(j3)
    assert pins(100.0, geometry("insert", r_in, r_out, JOIN), JOIN, 50)["n"] == 10
    return True
