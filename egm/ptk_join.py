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
TODO(CP-79): collar по Д-92/Д-93 — бурт наружу/внутрь выбирается здесь (корпус, трубы, съём металла),
  осевые сквозные штифты через бурт и дно-лист, L = h_b + t_s; t_s — с определяющим критерием,
  t_s_min = max(k_fit·d, t_tech) — в JOIN; радиальная схема collar выше — устарела.
TODO(CP-80): дно-лист (.13) и ступица (.12) — отдельные детали, ступица к листу осевыми штифтами;
  t_s учитывает окружность штифтов ступицы r_h (смятие, срез диска M/(2π·r_h²·t)).
TODO(CP-81): L4 — обечайка без бурта + отдельное кольцо-бурт: радиальные штифты (окна) и осевые (дно-лист).
"""
import math

from egm import materials as MAT

JOIN = {"join": "auto", "join_order": ["collar", "insert"], "pin_d": [3.0, 4.0, 5.0],
        "pin_n": [4, 6, 8, 10, 12, 16], "edge_k": 1.5, "pin_depth_k": 1.5, "pin_web": 2.0,
        "tau_pin": 80.0, "sig_wall": 150.0, "sig_hub": 150.0, "c_in": 1.0, "c_out": 1.0,
        "pin_gap": 0.5, "weld": []}   # weld — марки, из листа которых допустима .02C (insert, Д-76)
# CP-79, Д-93: collar — t_s_min = max(k_fit·d, t_tech); [τ] диска на срез; корпус r_lim/r_free (из ptk_layout);
# значения k_fit, t_tech, tau_disk — предварительные, обосновать (OQ-27)
# hub_d — d.09 (ступица, CP-80): нет — штифты ступица–лист не считаются (как CP-79)
JOIN.update(k_fit=1.0, t_tech=2.0, tau_disk=80.0, r_lim=None, r_free=None, hub_d=None,
            fl_gap=0.5)   # OQ-28, Д-94: радиальный зазор утопленного фланца .12 в отверстии бурта
JOIN.update(hub_bore=None, hub_l=None, pin_wall=1.0)   # CP-83: обод ступицы D.10…d.09, длина, стенка за гнездом
JOIN.update(leaf_fit="H7/js6")   # CP-84, Д-97: посадка дна-листа .13 в расточку обечайки .02C (L4); предварительно
SCHEMES = ("collar", "insert", "ring")   # ring — L4: обечайка .02C + кольцо-бурт .14 (CP-81, Д-96); в join_order не входит
DIRS = ("out", "in")          # направление бурта collar: наружу | внутрь (Д-93)


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


def pin_cat(pins):
    """vendor_prices.yaml → pins -> {Ø: {key, l — стандартные длины, std}} (Д-74); не dict — пропуск."""
    out = {}
    for k, v in (pins or {}).items():
        if isinstance(v, dict) and v.get("d") and v.get("l"):
            out[float(v["d"])] = {"key": str(k), "l": sorted(float(x) for x in v["l"]),
                                  "std": str(v.get("std", ""))}
    return out


def pin_len(d, need, cat):
    """Наименьшая стандартная длина ≥ need из каталога -> (l | None, обозначение)."""
    c = (cat or {}).get(float(d))
    l = next((x for x in c["l"] if x >= need - 1e-9), None) if c else None
    if l is None:
        return None, ""
    return l, f"Штифт {d:g}×{l:g} {c['std']}".strip()


def pins(M, g, o, n_win=None, cat=None):
    """Наименьший Ø, затем наименьшее n; при n_win — n | n_win (деление окон) -> dict | None.
    cat — каталог (pin_cat): Ø только из каталога, длина l — наименьшая стандартная ≥ t + h
    (стенка .02 + глубина в .12); гнездо в .12 — l − t + pin_gap (Д-74)."""
    ds = sorted(o["pin_d"])
    if cat:
        ds = [d for d in ds if float(d) in cat]
    for d in ds:
        need = g["t"] + o["pin_depth_k"] * d
        l, des = pin_len(d, need, cat)
        if cat and l is None:
            continue
        ok = [n for n in sorted(o["pin_n"]) if not check(M, g, d, n, o)[1]]
        if n_win:
            ok = [n for n in ok if int(n_win) % n == 0] or ok
        if ok:
            s, _ = check(M, g, d, ok[0], o)
            q = {"d": d, "n": ok[0], **{k: round(v, 1) for k, v in s.items()}}
            q.update(t=round(g["t"], 2), need=round(need, 2), l=l, des=des,
                     key=f"{cat[float(d)]['key']}x{l:g}" if l else "",
                     hole12=round((l or need) - g["t"] + o["pin_gap"], 2))
            return q
    return None


def _area(t):
    return t["D"] ** 2 - (t["D"] - 2 * t["s"]) ** 2


def _blank(p):
    """Заготовка .02 выбранного соединения: «труба D×s» | «лист t (weld)» (rev 10.4, CP-63)."""
    t = p.get("tube")
    if t:
        return f"труба {t['D']:g}×{t['s']:g}"
    return f"лист {p['sheet']:g} (weld)" if p.get("sheet") else "нет"


def collar_geom(dr, r_in, r_out, d, o):
    """collar (Д-93): бурт наружу r_in…r_in+2e | внутрь r_in−2e…r_out, e = edge_k·d; штифты на r_j = r_in ± e.
    -> {r_j, t — ширина бурта, D, d — габарит кольца бурта с припусками c_in/c_out, r0, r1}."""
    e = o["edge_k"] * d
    if dr == "out":
        r0, r1, rj = r_in - o["c_in"], r_in + 2 * e + o["c_out"], r_in + e
    else:
        r0, r1, rj = r_in - 2 * e - o["c_in"], r_out + o["c_out"], r_in - e
    return {"r_j": rj, "t": r1 - r0, "D": 2 * r1, "d": 2 * r0, "r0": r0, "r1": r1}


def _up(x):
    return math.ceil(x * 10 - 1e-9) / 10


def _flush(v):
    """Вариант collar с фланцем .12, утопленным в отверстие бурта (OQ-28, Д-94)."""
    return bool(((v.get("pins") or {}).get("hub") or {}).get("flush"))


HUB_RANK = {"direct": 0, "flush": 1}       # CP-83: прямое → утопленный фланец (Д-94) → над листом (CP-80)


def _hub_rank(v):
    return HUB_RANK.get(((v.get("pins") or {}).get("hub") or {}).get("mode", ""), 2)


def mode(jn):
    """Крепление дна-листа .13 к ступице выбранного варианта: direct | flush | over | ''."""
    h = ((((jn or {}).get("pick") or {}).get("pins") or {}).get("hub")) or {}
    return h.get("mode", "")


def collar_check(M, g, d, n, o, ex=None, hb_min=0.0):
    """Осевые сквозные штифты через бурт h_b и дно-лист t_s -> (напряжения, нарушения).
    h_b = max(pin_depth_k·d, F/(n·d·[σсм])); t_s = max(смятие F/(n·d·[σсм]), срез диска
    M/(2π·r²·[τ]), k_fit·d, t_tech) — критерий выводится (Д-93); ex — критерии ступицы (CP-80):
    смятие по штифтам ступицы и срез диска на r_h (заменяет срез на r_j)."""
    F = M * 1e3 / g["r_j"]
    e = o["edge_k"] * d
    h_b = _up(max(o["pin_depth_k"] * d, F / (n * d * o["sig_wall"]), hb_min))   # hb_min — h_f утопл. фланца (Д-94)
    c = {"смятие": F / (n * d * o["sig_hub"]),
         "срез диска": M * 1e3 / (2 * math.pi * g["r_j"] ** 2 * o["tau_disk"]),
         "k_fit": o["k_fit"] * d, "t_tech": o["t_tech"]}
    c.update(ex or {})
    crit = max(c, key=c.get)
    t_s = _up(c[crit])
    s = {"F": F, "tau": F / (n * math.pi * d * d / 4), "sig_wall": F / (n * d * h_b),
         "sig_hub": F / (n * d * t_s), "tau_edge": F / (n * 2 * max(e - d / 2, 1e-6) * h_b),
         "h_b": h_b, "t_s": t_s, "L": h_b + t_s, "pitch": 2 * math.pi * g["r_j"] / n,
         "t_s_min": max(o["k_fit"] * d, o["t_tech"])}
    bad = [k for k, lim in (("tau", o["tau_pin"]), ("sig_wall", o["sig_wall"]),
                            ("sig_hub", o["sig_hub"]), ("tau_edge", 0.6 * o["sig_wall"]))
           if s[k] > lim + 1e-9]
    if s["pitch"] < d + o["pin_web"] - 1e-9:
        bad.append("pitch")
    return s, crit, bad


def _pin_ds(o, cat):
    ds = sorted(o["pin_d"])
    return [d for d in ds if float(d) in cat] if cat else ds


def _direct_pins(M, hub_d, g, d, dh, o):
    """CP-83: дно-лист .13 к ступице .12 напрямую, без фланца — штифты через лист в глухие гнёзда обода.
    Обод D.10/2…d.09/2, e = edge_k·d_h: r_h = d.09/2 − e, r_h − D.10/2 ≥ e; концы штифтов со стороны
    обечайки — в отверстии бурта (r_h + d_h/2 ≤ r0); ступица не закрывает штифты бурта
    (d.09/2 ≤ r_j − d/2 − c_out); гнездо h_p = max(pin_depth_k·d_h, смятие), h_p + pin_gap + pin_wall ≤ hub_l
    -> ((штифты, критерии t_s, ""), "") | (None, причина)."""
    e = o["edge_k"] * dh
    rb, ro = o["hub_bore"] / 2, hub_d / 2
    rh = ro - e
    if rh - rb < e - 1e-9:
        return None, f"обод ступицы {ro - rb:.2f} < 2·edge_k·d_h {2 * e:g} (d.09 {hub_d:g}, D.10 {2 * rb:g})"
    if rh + dh / 2 > g["r0"] + 1e-9:
        return None, f"штифты ступицы до r {rh + dh / 2:.2f} > отв. бурта {g['r0']:.2f}"
    lim = g["r_j"] - d / 2 - o["c_out"]
    if ro > lim + 1e-9:
        return None, f"ступица r {ro:.2f} закрывает штифты бурта (≤ {lim:.2f})"
    F, why = M * 1e3 / rh, ""
    for nh in sorted(o["pin_n"]):
        hp = _up(max(o["pin_depth_k"] * dh, F / (nh * dh * o["sig_hub"])))
        if o.get("hub_l") and hp + o["pin_gap"] + o.get("pin_wall", 1.0) > o["hub_l"] + 1e-9:
            why = f"гнездо {hp:g} + pin_gap + стенка > длины ступицы {o['hub_l']:g}"
            continue
        s = {"mode": "direct", "flush": False, "fl_why": "", "dir_why": "", "d": dh, "n": nh,
             "r_h": rh, "r_f": ro, "F": F, "h_f": 0.0, "depth": hp,
             "tau": F / (nh * math.pi * dh * dh / 4), "sig_fl": F / (nh * dh * hp),
             "tau_edge": F / (nh * 2 * max(e - dh / 2, 1e-6) * hp), "pitch": 2 * math.pi * rh / nh}
        if (s["tau"] > o["tau_pin"] + 1e-9 or s["tau_edge"] > 0.6 * o["sig_wall"] + 1e-9
                or s["pitch"] < dh + o["pin_web"] - 1e-9):
            continue
        ex = {"смятие ступицы": F / (nh * dh * o["sig_hub"]),
              "срез диска": M * 1e3 / (2 * math.pi * rh ** 2 * o["tau_disk"])}
        return (s, ex, ""), ""
    return None, why or "штифты в обод ступицы не проходят"


def _ang_gap(nr, na):
    """Наименьший угол, °, между радиальными (cage + i·360/nr) и осевыми (cage + (j + ½)·360/na) штифтами."""
    best = 360.0
    for i in range(nr):
        for j in range(na):
            x = ((j + 0.5) / na - i / nr) % 1.0
            best = min(best, 360.0 * min(x, 1.0 - x))
    return best


def _ring_blank(stock, by, mats, r0, r1, ta):
    """Заготовка кольца .14 (CP-81): труба (tube_ok с допусками ГОСТ), иначе пруток -> dict | None."""
    Dn, Dv = 2 * r1 + 2 * ta, 2 * r0 - 2 * ta
    for m in mats:
        f = by.get(m) or {}
        ts = [t for t in f.get("tubes", []) if tube_ok(t, Dn, Dv, stock)]
        if ts:
            return {"material": m, "tube": min(ts, key=_area), "need": [round(Dn, 2), round(Dv, 2)]}
        bs = sorted(b for b in f.get("bars", []) if b >= Dn - 1e-9)
        if bs:
            return {"material": m, "bar": bs[0], "need": [round(Dn, 2), round(Dv, 2)]}
    return None


def _ring(M, r_in, r_out, stock, by, tried, ta, o, cat, n_win):
    """L4 (CP-81, Д-93 п. 5, Д-96): обечайка .02C без бурта + кольцо-бурт .14 в её торце.
    Радиальные штифты обечайка → кольцо — как insert (по делению окон, ось C), гнездо hole12 в кольце;
    осевые лист .13 → кольцо на r_ja = r_in − e_a, углы между радиальными (cage + (j + ½)·360/n_a);
    кольцо r0…r_in: w = max(hole12 + pin_wall, 2·e_a), L_r = max(2·edge_k·d_r, h_b);
    ступица → лист — hub_pins (прямое → Д-94 → CP-80) -> [вариант]."""
    g = geometry("insert", r_in, r_out, o)
    need = [round(g["D"] + 2 * ta, 2), round(g["d"] - 2 * ta, 2)]
    fit = {}
    for m in tried:
        ts = [t for t in (by.get(m) or {}).get("tubes", []) if tube_ok(t, *need, stock)]
        if ts:
            fit[m] = min(ts, key=_area)
    v = {"scheme": "ring", "geom": {k: round(x, 2) for k, x in g.items()}, "pins": None, "need": need,
         "fit": fit, "house": "", "rej": "", "note": "", "margin": None}
    rad = pins(M, g, o, n_win, cat)
    if rad is None:
        v["note"] = "кольцо: радиальные штифты обечайка–кольцо не проходят"
        return [v]
    nr, dr, note = rad["n"], rad["d"], ""
    for d in _pin_ds(o, cat):
        e = o["edge_k"] * d
        w = max(rad["hole12"] + o["pin_wall"], 2 * e)
        r0, rj = r_in - w, r_in - e
        gr = {"r_j": rj, "r0": r0}
        h, ex = None, None
        if o.get("hub_d"):
            h, ex, hn = hub_pins(M, o["hub_d"], gr, d, o, cat)
            if h is None:
                note = hn
                continue
        for n in sorted(o["pin_n"]):
            s, crit, bad = collar_check(M, gr, d, n, o, ex, h["h_f"] if h and h.get("flush") else 0.0)
            if bad:
                continue
            gap = _ang_gap(nr, n)
            near = rj + d / 2 > r_in - rad["hole12"] - o["pin_wall"] - 1e-9   # в зоне радиальных гнёзд
            if near and math.radians(gap) * rj < (d + dr) / 2 + o["pin_web"] - 1e-9:
                note = f"кольцо: осевые {n}×Ø{d:g} и радиальные {nr}×Ø{dr:g} пересекаются ({gap:.1f}°)"
                continue
            l, des = pin_len(d, s["h_b"] + s["t_s"], cat)
            if cat and l is None:
                note = f"кольцо: нет стандартной длины осевого штифта Ø{d:g} ≥ {s['h_b'] + s['t_s']:g}"
                continue
            hub = hub_fin(h, s["t_s"], cat) if h else None
            if h and hub is None:
                note = f"ступица: нет стандартной длины штифта Ø{h['d']:g}"
                continue
            lr = {"2·e_r": 2 * o["edge_k"] * dr, "h_b осевых": s["h_b"],          # CP-84, Д-97: радиальные
                  "d_r + 2·pin_web": dr + 2 * o["pin_web"]}                          # вне зоны листа: z_r − d_r/2 ≥ t_s + pin_web
            L_r = _up(max(lr.values()))
            q = {**rad, "L_r": L_r, "h_b": s["h_b"], "t_s": s["t_s"], "crit": crit, "t_s_min": s["t_s_min"],
                 "L": round(L_r + s["t_s"], 2),
                 "z_r": round(s["t_s"] + L_r / 2, 2), "lr_why": max(lr, key=lr.get),   # z_r — от торца обечайки
                 "leaf": {"D": round(2 * r_in, 2), "fit": o.get("leaf_fit", "H7/js6")},  # лист в расточке обечайки
                 "ax": {"d": d, "n": n, "r_j": round(rj, 2), "l": l, "des": des,
                        "key": f"{cat[float(d)]['key']}x{l:g}" if l else "", "tau": round(s["tau"], 1),
                        "sig_ring": round(s["sig_wall"], 1), "sig_leaf": round(s["sig_hub"], 1),
                        "tau_edge": round(s["tau_edge"], 1), "gap": round(gap, 2)}}
            if hub:
                q["hub"] = hub
            rb = _ring_blank(stock, by, o.get("ring_mats") or tried, r0, r_in, ta)
            v.update(pins=q, ring={"r0": round(r0, 2), "r1": round(r_in, 2), "L": L_r, "w": round(w, 2)},
                     ring_blank=rb)
            if rb is None:
                v["rej"] = (f"кольцо .14: нет трубы/прутка Ø ≥ {2 * r_in + 2 * ta:.2f} с отв. ≤ "
                            f"{2 * r0 - 2 * ta:.2f} из {', '.join(map(str, o.get('ring_mats') or tried))}")
            if o.get("r_free") is not None:
                v["margin"] = round(r0 - o["r_free"], 2)
                if v["margin"] < -1e-9:
                    v["house"] = f"корпус: r отв. кольца {r0:.2f} < {o['r_free']:.2f} (.10/.11 + seat_wall)"
            return [v]
    v["note"] = note or "кольцо: осевые штифты лист–кольцо не проходят"
    return [v]


def hub_pins(M, hub_d, g, d, o, cat=None):
    """Штифты ступица–лист (CP-80, Д-93): r_h = d.09/2 + edge_k·d_h, фланец r_f = r_h + edge_k·d_h;
    отверстия ступицы — внутри отверстия бурта (r_h + d_h/2 ≤ r0), фланец не закрывает штифты бурта
    (r_f ≤ r_j − d/2 − c_out); h_f = max(pin_depth_k·d_h, смятие) -> (штифты | None, критерии t_s, причина)."""
    note = ""
    lim_f = g["r_j"] - d / 2 - o["c_out"]
    note_d = ""                                        # CP-83: сначала прямое крепление в обод ступицы
    if o.get("hub_bore"):
        for dh in _pin_ds(o, cat):
            r, why = _direct_pins(M, hub_d, g, d, dh, o)
            if r:
                return r
            note_d = note_d or f"прямое: {why}"
    for dh in _pin_ds(o, cat):
        e = o["edge_k"] * dh
        rh, rf = hub_d / 2 + e, hub_d / 2 + 2 * e
        if rh + dh / 2 > g["r0"] + 1e-9:
            note = f"ступица: штифты до r {rh + dh / 2:.2f} > отв. бурта {g['r0']:.2f}"
            continue
        if rf > lim_f + 1e-9:
            note = f"ступица: фланец r {rf:.2f} закрывает штифты бурта (≤ {lim_f:.2f})"
            continue
        lim_fl = g["r0"] - o.get("fl_gap", 0.5)       # OQ-28, Д-94: фланец в отверстии бурта, под листом
        flush = rf <= lim_fl + 1e-9                    # TODO(CP-82): сверка по 3D (Д-65)
        why_fl = "" if flush else f"фланец r {rf:.2f} > отв. бурта − fl_gap {lim_fl:.2f}"
        F = M * 1e3 / rh
        for nh in sorted(o["pin_n"]):
            h_f = _up(max(o["pin_depth_k"] * dh, F / (nh * dh * o["sig_wall"])))
            s = {"d": dh, "n": nh, "r_h": rh, "r_f": rf, "F": F, "h_f": h_f, "flush": flush, "fl_why": why_fl,
                 "mode": "flush" if flush else "over", "dir_why": note_d,          # CP-83
                 "tau": F / (nh * math.pi * dh * dh / 4), "sig_fl": F / (nh * dh * h_f),
                 "tau_edge": F / (nh * 2 * max(e - dh / 2, 1e-6) * h_f), "pitch": 2 * math.pi * rh / nh}
            if (s["tau"] > o["tau_pin"] + 1e-9 or s["sig_fl"] > o["sig_wall"] + 1e-9
                    or s["tau_edge"] > 0.6 * o["sig_wall"] + 1e-9 or s["pitch"] < dh + o["pin_web"] - 1e-9):
                continue
            ex = {"смятие ступицы": F / (nh * dh * o["sig_hub"]),
                  "срез диска": M * 1e3 / (2 * math.pi * rh ** 2 * o["tau_disk"])}
            if flush:                                  # Д-94: ступица сквозь лист — кромка у отв. d.09
                ex["кромка листа"] = F / (nh * 2 * max(e - dh / 2, 1e-6) * 0.6 * o["sig_wall"])
            return s, ex, ""
        note = note or "ступица: штифты не проходят"
    return None, None, note


def hub_fin(h, ts, cat=None):
    """Длина штифта ступицы ≥ h_f + t_s (сквозной), смятие в листе -> dict | None (нет длины)."""
    dr = h.get("mode") == "direct"                      # CP-83: лист + глухое гнездо обода h_p
    L = (h["depth"] if dr else h["h_f"]) + ts
    l, des = pin_len(h["d"], L, cat)
    if cat and l is None:
        return None
    out = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in h.items()}
    out.update(L=round(L, 2), sig_leaf=round(h["F"] / (h["n"] * h["d"] * ts), 1), l=l, des=des,
               key=f"{cat[float(h['d'])]['key']}x{l:g}" if l else "")
    if dr:                                              # гнездо по стандартной длине: l − t_s + pin_gap (Д-74)
        out["nest"] = round((l or L) - ts + JOIN["pin_gap"], 2)
    return out


def collar_pins(M, dr, r_in, r_out, o, cat=None):
    """Наименьший Ø, затем наименьшее n; длина штифта ≥ h_b + t_s (сквозной); при o["hub_d"] —
    штифты ступица–лист, t_s — max по обеим окружностям (CP-80) -> (dict | None, geom, причина)."""
    ds = _pin_ds(o, cat)
    g = collar_geom(dr, r_in, r_out, ds[0] if ds else 3.0, o)
    note = ""
    for d in ds:
        g = collar_geom(dr, r_in, r_out, d, o)
        for n in sorted(o["pin_n"]):
            s, crit, bad = collar_check(M, g, d, n, o)
            if bad:
                continue
            hub = None
            if o.get("hub_d"):
                h, ex, note = hub_pins(M, float(o["hub_d"]), g, d, o, cat)
                if h is None:
                    break                              # от n не зависит — следующий Ø бурта
                s, crit, bad = collar_check(M, g, d, n, o, ex)
                if h.get("flush") and h["h_f"] > s["h_b"] + 1e-9:   # Д-94: фланец в бурте — h_b ≥ h_f
                    s, crit, bad = collar_check(M, g, d, n, o, ex, h["h_f"])
                hub = hub_fin(h, s["t_s"], cat)
                if hub is None:
                    note = f"ступица: нет стандартной длины штифта Ø{h['d']:g} ≥ {(h.get('depth') or h['h_f']) + s['t_s']:g}"
                    continue
            l, des = pin_len(d, s["L"], cat)
            if cat and l is None:
                break
            q = {"d": d, "n": n, **{k: round(v, 1) for k, v in s.items()}}
            q.update(crit=crit, t=round(g["t"], 2), need=round(s["L"], 2), l=l, des=des,
                     key=f"{cat[float(d)]['key']}x{l:g}" if l else "", hole12=q["t_s"])
            if hub:
                q["hub"] = hub
            return q, g, ""
    return None, g, note


def _collar(M, r_in, r_out, stock, by, tried, ta, o, cat):
    """Варианты collar по направлениям бурта: штифты, труба по бурту, фильтр корпуса (Д-93)."""
    out = []
    for dr in DIRS:
        q, g, note = collar_pins(M, dr, r_in, r_out, o, cat)
        need = [round(g["D"] + 2 * ta, 2), round(g["d"] - 2 * ta, 2)]
        fit = {}
        for m in tried:
            ts = [t for t in (by.get(m) or {}).get("tubes", []) if tube_ok(t, *need, stock)]
            if ts:
                fit[m] = min(ts, key=_area)
        house, margin = "", None
        if dr == "out" and o.get("r_lim") is not None:
            margin = o["r_lim"] - g["r1"]
            if margin < -1e-9:
                house = f"корпус: r бурта {g['r1']:.2f} > {o['r_lim']:.2f} (карман .07B до болтов)"
        if dr == "in" and o.get("r_free") is not None:
            margin = g["r0"] - o["r_free"]
            if margin < -1e-9:
                house = f"корпус: r отв. бурта {g['r0']:.2f} < {o['r_free']:.2f} (.10/.11 + seat_wall)"
        out.append({"scheme": "collar", "dir": dr, "geom": {k: round(v, 2) for k, v in g.items()},
                    "pins": q, "need": need, "fit": fit, "house": house, "note": note,
                    "margin": round(margin, 2) if margin is not None else None})
    return out


def _vtext(v, jn):
    p = "" if v["pins"] else (v.get("note") or "штифты не проходят")
    t = "" if v["fit"] else (f"нет трубы Ø ≥ {v['need'][0]:g} с отв. ≤ {v['need'][1]:g}"
                             + (f" из {', '.join(map(str, jn['tried']))}" if any(jn["tried"]) else ""))
    r = "; ".join(x for x in (t, p, v.get("house", ""), v.get("rej", "")) if x) or "нет марки"
    return r + (f" [{'наружу' if v['dir'] == 'out' else 'внутрь'}]" if v.get("dir") else "")


def choose(M, r_in, r_out, stock, mats=None, opt=None, n_win=None, cat=None):
    """Схема по доступности заготовок -> {pick | None, variants, tried, lim}.
    cat — каталог штифтов (pin_cat); нет — из opt["pin_cat"] (Д-74)."""
    o = {**JOIN, **(opt or {})}
    cat = cat if cat is not None else o.get("pin_cat")
    order = [o["join"]] if o["join"] in SCHEMES else [s for s in o["join_order"] if s in SCHEMES]
    by = MAT.stock_by_material(stock) if stock else {}
    tried = [str(m) for m in mats] if mats else [m for m in by if m is not None]
    tried = [None] if None in by else [m for m in tried if m in by]
    ta = float((stock or {}).get("tube_allow", 0.5))
    var = []
    for s in order:
        if s == "ring":                                          # CP-81, Д-96: L4
            var += _ring(M, r_in, r_out, stock, by, tried, ta, o, cat, n_win)
            continue
        if s == "collar":                                        # CP-79, Д-93
            var += _collar(M, r_in, r_out, stock, by, tried, ta, o, cat)
            continue
        g = geometry(s, r_in, r_out, o)
        need = [round(g["D"] + 2 * ta, 2), round(g["d"] - 2 * ta, 2)]
        fit = {}
        for m in tried:
            ts = [t for t in (by.get(m) or {}).get("tubes", []) if tube_ok(t, *need, stock)]
            if ts:
                fit[m] = min(ts, key=_area)
        var.append({"scheme": s, "geom": {k: round(v, 2) for k, v in g.items()},
                    "pins": pins(M, g, o, n_win, cat), "need": need, "fit": fit})
    jn = {"variants": var, "tried": tried}
    pick = None
    for m in tried:
        for s in order:
            c = [v for v in var if v["scheme"] == s and v["pins"] and m in v["fit"] and not v.get("house")
                 and not v.get("rej")]                            # CP-81: нет заготовки кольца .14
            if not c:
                continue
            # Д-93: меньший съём — сечение трубы; при равенстве — наружу
            v = min(c, key=lambda v: (_area(v["fit"][m]), _hub_rank(v),           # CP-83: прямое → Д-94 → CP-80
                                      DIRS.index(v["dir"]) if v.get("dir") else 0))
            pick = {"scheme": v["scheme"], "material": m, "tube": v["fit"][m], "pins": v["pins"],
                    "geom": v["geom"]}
            if v.get("ring"):                                    # CP-81: кольцо-бурт .14 и его заготовка
                pick.update(ring=v["ring"], ring_blank=v.get("ring_blank"))
            if v.get("dir"):
                oth = [_vtext(x, jn) for x in var if x.get("dir") and x is not v]
                pick.update(dir=v["dir"], margin=v["margin"],
                            other="; ".join(oth) if oth else "")
            break
        if pick:
            break
    return {"pick": pick, "variants": var, "tried": tried,
            "lim": {"sig_wall": o["sig_wall"], "tau_pin": o["tau_pin"], "sig_hub": o["sig_hub"],
                    "r_lim": o.get("r_lim"), "r_free": o.get("r_free"), "k_fit": o["k_fit"],
                    "t_tech": o["t_tech"], "tau_disk": o["tau_disk"]}}


def why(jn):
    """Причины отказа по схемам."""
    out = []
    for v in jn["variants"]:
        out.append(f"{v['scheme']}: " + _vtext(v, jn))
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


JOIN_HEAD = ("| Проработка | Схема | Заготовка .02 | Штифты n × Ø × l | Обозначение | Гнездо в .12, мм | "
             "τ штифта / [τ], МПа | σсм стенки / [σ], МПа | σсм ступицы / [σ], МПа | "
             "Срез к торцу / [τ], МПа | Пояс L, мм |")
JOIN_RULE = "|---" * 11 + "|"


def _hub_txt(hb):
    """Ступица–лист в ячейке «Схема» (CP-80, Д-94, CP-83) — общая для collar и ring."""
    if not hb:
        return ""
    return (f"; ступица {hb['n']}×Ø{hb['d']:g}" + (f"×{hb['l']:g}" if hb.get("l") else "")
            + (f" на r_h {hb['r_h']:g}, прямо в обод ступицы без фланца, гнёзда {hb.get('nest') or hb['depth']:g} (CP-83)"
               if hb.get("mode") == "direct" else
               f" на r_h {hb['r_h']:g}, фланец Ø{2 * hb['r_f']:g}×{hb['h_f']:g}"
               + (" утоплен в бурт (Д-94)" if hb.get("flush")
                  else f" над листом, +h_f к длине ({hb.get('fl_why') or 'Д-94'})")
               + (f"; {hb['dir_why']}" if hb.get("dir_why") else "")))


def _sch_ring(p):
    """Ячейка «Схема» L4 (CP-81, Д-96): кольцо .14, радиальные и осевые штифты, t_s с критерием."""
    q, rg, b = p["pins"], p["ring"], p.get("ring_blank") or {}
    a = q["ax"]
    lf = q.get("leaf") or {}                                          # CP-84, Д-97: лист в расточке обечайки
    lt = (f"; дно-лист Ø{lf['D']:g} ({lf['fit']}) в расточке обечайки .02C на торце кольца, заподлицо с "
          f"торцом, обечайка +t_s; радиальные z_r {q['z_r']:g} от торца, L_r по {q['lr_why']}" if lf else "")
    bl = (f"труба {b['tube']['D']:g}×{b['tube']['s']:g}" if b.get("tube") else
          f"пруток Ø{b['bar']:g}" if b.get("bar") else "нет заготовки")
    mg = f"; запас корпуса {p['margin']:g} мм" if p.get("margin") is not None else ""
    return (f"ring (L4): кольцо .14 Ø{2 * rg['r1']:g}/Ø{2 * rg['r0']:g}×{rg['L']:g} "
            f"({(b.get('material') or '') + ' ' if b.get('material') else ''}{bl}); "
            f"радиальные обечайка–кольцо по делению окон, гнездо {q['hole12']:g} сквозь кольцо; "
            f"осевые лист–кольцо {a['n']}×Ø{a['d']:g}" + (f"×{a['l']:g}" if a.get("l") else "")
            + f" на r {a['r_j']:g} между радиальными ({a['gap']:g}°), τ {a['tau']:g}, σсм кольца "
            f"{a['sig_ring']:g}, листа {a['sig_leaf']:g}; дно-лист t_s {q['t_s']:g} ({q['crit']}; "
            f"t_s_min {q['t_s_min']:g}){_hub_txt(q.get('hub'))}{lt}{mg} (Д-96, Д-97)")


def _sch(p):
    """Ячейка «Схема» SPEC-11: collar — направление, h_b, t_s с критерием, запас корпуса, отказ другого."""
    if p["scheme"] == "ring":                                        # CP-81
        return _sch_ring(p)
    if not p.get("dir"):
        return p["scheme"]
    q = p["pins"]
    mg = f"; запас корпуса {p['margin']:g} мм" if p.get("margin") is not None else ""
    hs = _hub_txt(q.get("hub"))                                      # CP-80: ступица–лист
    hs += f"; {p['brg']}" if p.get("brg") else ""                   # CP-83: замена .09 ради прямого крепления
    return (f"collar {'наружу' if p['dir'] == 'out' else 'внутрь'}; бурт h_b {q['h_b']:g}, "
            f"дно-лист t_s {q['t_s']:g} ({q['crit']}; t_s_min {q['t_s_min']:g}){hs}{mg}"
            + (f"; отказ: {p['other']}" if p.get("other") else "") + " (Д-93)")


def join_row(name, jn):
    """Строка таблицы «Соединение .02–.12» SPEC-11 (Д-74); отказ — причины по схемам."""
    p = jn["pick"]
    if p is None:
        return f"| {name} | нет | {why(jn).replace(' | ', '; ')} |" + " — |" * 8
    t, q, lim = p["tube"], p["pins"], jn["lim"]
    m = f"{p['material']} " if p["material"] else ""
    nd = f"{q['n']} × Ø{q['d']:g}" + (f" × {q['l']:g}" if q.get("l") else "")
    des = f"{q['des']} ({q['key']})" if q.get("des") else "нет vendor_prices.yaml → pins"
    return (f"| {name} | {_sch(p)} | {m}труба {t['D']:g}×{t['s']:g} | {nd} | {des} | "
            f"{q.get('hole12', q['L']):g} | {q['tau']:g} / {lim['tau_pin']:g} | "
            f"{q['sig_wall']:g} / {lim['sig_wall']:g} | {q['sig_hub']:g} / {lim.get('sig_hub', 0):g} | "
            f"{q['tau_edge']:g} / {0.6 * lim['sig_wall']:g} | {q['L']:g} |")


def self_test():
    """PTK-050 (r 33.06…33.94, M 100): collar — 73×7, 6×Ø3; insert — 73×5, 8×Ø3; выбор по наличию."""
    st = {"tube_allow": 0.5, "sheet_allow": 0.3, "tube_tol_D": 0.008, "tube_tol_s": 0.15,
          "materials": {"40Х": {"tubes": [{"D": 73.0, "s": 5.0}, {"D": 73.0, "s": 7.0}]}}}
    r_in, r_out = 33.06, 33.94
    assert tube_ok({"D": 73.0, "s": 5.0}, 68.88, 65.12, st)
    assert not tube_ok({"D": 73.0, "s": 5.0}, 70.88, 63.12, st)
    assert tube_ok({"D": 73.0, "s": 5.0}, 70.88, 63.12)
    p = choose(100.0, r_in, r_out, st, ["40Х"])["pick"]
    assert p["scheme"] == "insert", p          # CP-79: под бурт Д-93 труб 73×5/7 мало
    j2 = choose(100.0, r_in, r_out, st, ["40Х"], {"join": "insert"})
    p2 = j2["pick"]
    assert (p2["scheme"], p2["tube"]["s"], p2["pins"]["n"]) == ("insert", 5.0, 8), p2
    assert "8×Ø3" in short(j2), short(j2)
    st1 = {**st, "materials": {"40Х": {"tubes": [{"D": 73.0, "s": 5.0}]}}}
    assert choose(100.0, r_in, r_out, st1, ["40Х"])["pick"]["scheme"] == "insert"
    j3 = choose(100.0, r_in, r_out, st1, ["40ХН2МА"])
    assert j3["pick"] is None and "нет трубы" in why(j3), why(j3)
    assert pins(100.0, geometry("insert", r_in, r_out, JOIN), JOIN, 50)["n"] == 10
    cat = pin_cat({"P3": {"d": 3.0, "l": [8, 10, 12], "std": "ГОСТ 24296-93"}, "_c": "x",
                   "P4": {"d": 4.0, "l": [10, 12]}})
    assert sorted(cat) == [3.0, 4.0] and pin_len(3.0, 5.38, cat) == (8.0, "Штифт 3×8 ГОСТ 24296-93")
    assert pin_len(3.0, 13.0, cat) == (None, "") and pin_len(5.0, 1.0, cat) == (None, "")
    jc = choose(100.0, r_in, r_out, st1, ["40Х"], cat=cat)
    q = jc["pick"]["pins"]
    assert (q["d"], q["l"], q["key"]) == (3.0, 8.0, "P3x8") and abs(q["hole12"] - 7.62) < 0.01, q
    assert choose(100.0, r_in, r_out, st1, ["40Х"], {"pin_cat": cat})["pick"]["pins"]["l"] == 8.0
    assert choose(100.0, r_in, r_out, st1, ["40Х"], {"pin_d": [5.0]}, cat=cat)["pick"] is None
    assert "Штифт 3×8" in join_row("K", jc) and join_row("K", jc).count("|") == 12, join_row("K", jc)
    assert join_row("K", j3).count("|") == 12, join_row("K", j3)
    # CP-79, Д-93: collar — направление бурта, осевые штифты, t_s с критерием, фильтр корпуса
    stc = {**st, "materials": {"40Х": {"tubes": [{"D": 73.0, "s": 18.0}, {"D": 89.0, "s": 16.0}]}}}
    jk = choose(100.0, r_in, r_out, stc, ["40Х"], {"join": "collar"})
    k = jk["pick"]
    assert (k["dir"], k["tube"]["D"], k["pins"]["d"], k["pins"]["n"]) == ("in", 73.0, 3.0, 8), k
    assert (k["pins"]["h_b"], k["pins"]["t_s"], k["pins"]["crit"], k["pins"]["L"]) == \
        (4.5, 3.0, "k_fit", 7.5), k["pins"]
    ko = choose(100.0, r_in, r_out, stc, ["40Х"], {"join": "collar", "r_free": 30.0})["pick"]
    assert ko["dir"] == "out" and ko["tube"]["D"] == 89.0 and "корпус" in ko["other"], ko
    kn = choose(100.0, r_in, r_out, stc, ["40Х"], {"join": "collar", "r_free": 30.0, "r_lim": 36.9})
    assert kn["pick"] is None and "корпус" in why(kn), why(kn)
    assert "внутрь" in join_row("K", jk) and join_row("K", jk).count("|") == 12, join_row("K", jk)
    # CP-80, Д-93: штифты ступица–лист на r_h, t_s — max по обеим окружностям
    kh = choose(100.0, r_in, r_out, stc, ["40Х"], {"join": "collar", "hub_d": 30.0})["pick"]
    h = kh["pins"]["hub"]
    assert (kh["dir"], kh["pins"]["n"], h["d"], h["n"], h["r_h"], h["r_f"], h["h_f"]) == \
        ("in", 8, 3.0, 10, 19.5, 24.0, 4.5), (kh["pins"], h)
    assert (kh["pins"]["t_s"], kh["pins"]["crit"], h["L"]) == (3.0, "k_fit", 7.5), kh["pins"]
    k40 = choose(100.0, r_in, r_out, stc, ["40Х"], {"join": "collar", "hub_d": 40.0})["pick"]
    assert k40["dir"] == "out" and k40["pins"]["hub"]["n"] == 8 and "ступица" in k40["other"], k40
    rk = join_row("K", {**jk, "pick": kh})
    assert "ступица 10×Ø3" in rk and rk.count("|") == 12, rk
    # OQ-28, Д-94: фланец в плоскости бурта при r_f ≤ r0 − fl_gap, иначе — над листом (+h_f к длине)
    assert not h["flush"] and "над листом" in rk, (h, rk)
    h40 = k40["pins"]["hub"]
    assert h40["flush"] and k40["pins"]["h_b"] >= h40["h_f"], k40["pins"]
    k26 = choose(100.0, r_in, r_out, stc, ["40Х"], {"join": "collar", "hub_d": 26.0})["pick"]
    h26 = k26["pins"]["hub"]
    assert (k26["dir"], h26["n"], h26["r_h"], h26["r_f"], h26["flush"]) == ("in", 12, 17.5, 22.0, True), h26
    assert k26["pins"]["t_s"] == 3.0 and "утоплен" in join_row("K", {**jk, "pick": k26}), k26["pins"]
    # CP-83: .13 к ступице напрямую — d.09 40, D.10 19, hub_l 10.5: обод 10.5 ≥ 9, r_h 15.5, 12×Ø3 (τ 76.1)
    jd = choose(100.0, r_in, r_out, stc, ["40Х"], {"join": "collar", "hub_d": 40.0, "hub_bore": 19.0,
                                                   "hub_l": 10.5})
    kd, hd = jd["pick"], jd["pick"]["pins"]["hub"]
    assert mode(jd) == "direct" and (kd["dir"], hd["n"], hd["r_h"], hd["h_f"], hd["depth"]) == \
        ("in", 12, 15.5, 0.0, 4.5), hd
    assert (kd["pins"]["t_s"], hd["L"], hd["nest"]) == (3.0, 7.5, 5.0), hd
    assert "прямо в обод" in join_row("K", jd) and join_row("K", jd).count("|") == 12, join_row("K", jd)
    jw = choose(100.0, r_in, r_out, stc, ["40Х"], {"join": "collar", "hub_d": 40.0, "hub_bore": 30.0,
                                                   "hub_l": 10.5})          # обод 5 < 9 — фланец (Д-94)
    hw = jw["pick"]["pins"]["hub"]
    assert mode(jw) == "flush" and "обод ступицы" in hw["dir_why"], hw
    # CP-81, Д-96: L4 ring — радиальные по окнам (n | 50), осевые между ними (8 — пересечение 4.5°, берётся 10)
    sr = {**st, "materials": {"40Х": {"tubes": [{"D": 73.0, "s": 5.0}, {"D": 73.0, "s": 18.0}]}}}
    jr = choose(100.0, r_in, r_out, sr, ["40Х"], {"join": "ring"}, 50)
    pr_, qa = jr["pick"], jr["pick"]["pins"]["ax"]
    assert (pr_["scheme"], pr_["tube"]["s"], pr_["pins"]["n"], pr_["pins"]["hole12"]) == ("ring", 5.0, 10, 5.0), pr_
    assert (qa["d"], qa["n"], qa["r_j"], qa["gap"]) == (3.0, 10, 28.56, 18.0), qa
    assert (pr_["ring"]["r0"], pr_["ring"]["L"], pr_["pins"]["L"], pr_["pins"]["t_s"]) == (24.06, 9.0, 12.0, 3.0), pr_
    assert pr_["ring_blank"]["tube"]["s"] == 18.0, pr_["ring_blank"]
    assert (pr_["pins"]["z_r"], pr_["pins"]["lr_why"], pr_["pins"]["leaf"]["D"]) == (7.5, "2·e_r", 66.12), pr_["pins"]
    assert "расточке обечайки" in join_row("K", jr), join_row("K", jr)   # CP-84, Д-97
    assert "ring (L4)" in join_row("K", jr) and join_row("K", jr).count("|") == 12, join_row("K", jr)
    jr0 = choose(100.0, r_in, r_out, st1, ["40Х"], {"join": "ring"}, 50)
    assert jr0["pick"] is None and "кольцо .14" in jr0["variants"][0]["rej"], jr0["variants"]
    return True
