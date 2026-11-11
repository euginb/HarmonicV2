"""Конструктивы ПТК, шаг 2 (Д-55, CP-42): опоры .09/.10, кольца .11, крышки .07, заготовка .02.

Конструктив — набор деталей из products.yaml → PTK.layouts. Реализована схема
fixed = ring, output = cage: выход — сепаратор (стакан .02 в L1, обечайка .02 + ступица .12 в L2).
Ступица выхода полая: снаружи .09, внутри .10 (опора входного вала); кручение
τ = 16·M/(π·d³·(1 − β⁴)), β = D.10/d.09. Нагрузки опор по C0 не проверяются (OQ-17).
"""
import math
import re

from egm import materials as MAT
from egm import ptk_join

SUP = {"tau_allow": 25.0, "hub_wall": 2.0, "seat_wall": 2.0, "ring_w": 2.0,
       "lip": 1.0, "cup_t": 2.0, "ax_gap": 0.5, "nut_h": 4.0, "out_ext": 2.0, "pin_wall": 1.0,
       "hub_web": 2.0, "snap_h": 1.5,   # CP-90, Д-102: перемычка за гнездом .10; стопорное кольцо ГОСТ 13942
       "snap_web": 1.0, "fl_mu": 0.12, "fl_safety": 1.5, "fl_web": 1.0, "fl_tau_pin": 80.0}  # Д-104: фланец

_VP = None


def _vp():
    """vendor_prices.yaml (screws, rings_*, pins) — лениво; нет — {} (CP-90 этап 2b-2)."""
    global _VP
    if _VP is None:
        try:
            from egm import config
            _VP = config.load(config.cfg_file(config.load_app(), "configs.vendor_prices")) or {}
        except Exception:
            _VP = {}
    return _VP


def _lip_b(D09, o):
    """Буртик .07B под канавку кольца ГОСТ 13943 у .09: max(lip, m + snap_web) (Д-104)."""
    r = (_vp().get("rings_int") or {}).get(f"{D09:g}")
    return max(o["lip"], r["m"] + o["snap_web"]) if r else o["lip"]


def out_flange(M, oo, bears, b10, o, D_max):
    """CP-90 этап 2b-2, Д-104: момент — фланцем на торце ступицы (винты трением, иначе штифты срезом);
    ступица вровень: hub_l = ax_gap + B.09 + lip_B. .09 по возрастанию D: d ≥ D.10 + 2·hub_wall,
    D ≤ D_max, τ ступицы; первый .09 с проходящим фланцем. d_o без паза (паз — в гайке-опции)."""
    vp, T, sf = _vp(), M * 1e3, o["fl_safety"]
    scr, pins = vp.get("screws") or {}, vp.get("pins") or {}
    if not scr:
        return None, "нет таблицы screws в vendor_prices.yaml (Д-104)"
    D10 = (b10 or {}).get("D", 0.0)
    for _, d9, k9 in _brgs(bears):
        b = bears[k9]
        if b["D"] > D_max + 1e-9 or d9 < D10 + 2 * o["hub_wall"] - 1e-9:
            continue
        tau = 16 * T / (math.pi * d9 ** 3 * (1 - (D10 / d9) ** 4))
        if tau > o["tau_allow"] + 1e-9:
            continue
        lb = _lip_b(b["D"], o)
        hl = o["ax_gap"] + b["B"] + lb
        for ks, s in sorted(scr.items(), key=lambda x: x[1]["d"]):
            dep = round(1.5 * s["d"] + 1.0, 1)
            r_lo = D10 / 2 + s["d"] / 2 + o["hub_wall"]
            r_hi = d9 / 2 - s["d"] / 2 - o["hub_wall"]
            if dep > hl + 1e-9 or r_lo > r_hi + 1e-9:
                continue
            r = round((r_lo + r_hi) / 2, 1)
            pd = max((p["d"] for p in pins.values() if p["d"] <= s["d"]), default=0.0)
            for n in range(3, 13):
                if 2 * math.pi * r / n < s["d"] + o["fl_web"]:
                    break
                Tf = n * s["F_M"] * o["fl_mu"] * r            # кН·мм = Н·м
                n_p = 0
                if Tf / sf < M:
                    if not pd or math.pi * r / n < (s["d"] + pd) / 2 + o["fl_web"]:
                        continue
                    n_p = math.ceil(sf * T / (r * math.pi * pd ** 2 / 4 * o["fl_tau_pin"]))
                    if n_p > n or n % n_p:
                        continue
                fl = {"screw": ks, "n": n, "r": r, "d_tap": s["d_tap"], "depth": dep, "T_fric": round(Tf, 1),
                      "n_p": n_p, "pin_d": pd if n_p else 0.0, "pin_depth": round(min(2 * pd, hl), 1)}
                txt = f"{n}×{ks} r {r:g}" + (f" + {n_p}×Ø{pd:g} шт." if n_p else "") + f", трение {Tf:.0f} Н·м"
                ext = {**(vp.get("rings_ext") or {}).get(f"{d9:g}"), "std": "ГОСТ 13942-86"}       # 2b-3: наружные
                int_ = {**(vp.get("rings_int") or {}).get(f"{b['D']:g}"), "std": "ГОСТ 13943-86"}  # внутренние
                return {"link": "flange", "d": float(oo.get("d") or 0.0), "key": None, "l_key": 0.0,
                        "tau": round(tau, 1), "tau_allow": o["tau_allow"], "sigma_allow": 0.0,
                        "c09": [({"id": k9, **b}, tau)], "hub_l": round(hl, 2), "hub_by": "фланец/корпус",
                        "flush": True, "lip_B": round(lb, 2), "flange": fl, "fl_txt": txt,
                        "grooves": {"ext": ext, "int": int_}}, ""
    return None, (f"нет .09 с фланцем на торце ступицы под M {M:g} Н·м (винты screws, штифты pins, "
                  f"D ≤ {D_max:.1f}) — Д-104")
HEAD = ("| Проработка | Конструктив | Детали | .09 d×D×B | τ ступицы / [τ], МПа | .10 d×D×B | "
        ".11 n × h, мм | Крышки tA / tB, мм | Дно .02 z / t, мм; ступица | Длина, мм | Заготовка .02: марка, формы |")
RULE = "|---" * 11 + "|"
TOOL_HEAD = "| Проработка | Оснастка (Д-81) | Деталь | Размер | Маршрут |"
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


def hub_brgs(bears, M, D10, o, D_max):
    """Все .09 на полой ступице по возрастанию D: d ≥ D.10 + 2·hub_wall, D ≤ D_max, τ ≤ [τ]
    -> [(подшипник, τ)]; выбор среди них — по креплению дна-листа .13 (CP-83, _one)."""
    out = []
    for _, d, k in _brgs(bears):
        if d < D10 + 2 * o["hub_wall"] - 1e-9 or bears[k]["D"] > D_max + 1e-9:
            continue
        tau = 16 * M * 1e3 / (math.pi * d ** 3 * (1 - (D10 / d) ** 4))
        if tau <= o["tau_allow"] + 1e-9:
            out.append(({"id": k, **bears[k]}, tau))
    return out


def hub_brg(bears, M, D10, o, D_max):
    """.09 на полой ступице: наименьший из hub_brgs -> (подшипник, τ) | (None, None)."""
    c = hub_brgs(bears, M, D10, o, D_max)
    return c[0] if c else (None, None)


def out_shaft(M, oo, keys, bears, b10, o, D_max):
    """CP-90, Д-102: выходной вал в ступице -> (dict | None, причина).
    d_o: 16M/(π(d − t1)³) ≤ [τ] (шпонка из keys, spline — без паза); l_key ≥ 2M/(d(h − t1)[σсм]) + b;
    .09 по возрастанию D: (d.09 − d_o)/2 − t2 ≥ hub_wall, d.09 ≥ D.10 + 2·hub_wall, D ≤ D_max, τ полой ступицы;
    hub_l = max(ax_gap + B.09 + snap_h + out_ext, B.10 + hub_web + l_key + ax_gap)."""
    link = oo.get("link", "key")
    if link not in ("key", "spline"):
        return None, f"output.link {link}: не реализован (flange — после 3D, Д-102)"
    ta, sa, T = float(oo.get("tau_allow", 25.0)), float(oo.get("sigma_crush", 100.0)), M * 1e3
    ks = sorted(keys, key=lambda k: k["d_max"])
    d0 = float(oo.get("d") or 0.0)
    dd = kk = None
    for x in ([d0] if d0 > 0 else [float(v) for v in range(6, 101)]):
        k = next((q for q in ks if x <= q["d_max"] + 1e-9), None) if link == "key" else None
        if link == "key" and k is None:
            continue
        if 16 * T / (math.pi * (x - (k["t1"] if k else 0.0)) ** 3) <= ta + 1e-9:
            dd, kk = x, k
            break
    if dd is None:
        return None, (f"вал Ø{d0:g}: τ > [τ] {ta:g} МПа" if d0 > 0 else
                      f"нет Ø вала ≤ 100 мм с τ ≤ {ta:g} МПа и шпонкой из keys")
    t1, t2 = (kk["t1"], kk["t2"]) if kk else (0.0, 0.0)
    l_key = float(math.ceil(2 * T / (dd * (kk["h"] - t1) * sa) + kk["b"])) if kk else 0.0
    D10, B10 = (b10 or {}).get("D", 0.0), (b10 or {}).get("B", 0.0)
    c09 = []
    for _, d9, k9 in _brgs(bears):
        b = bears[k9]
        if (b["D"] > D_max + 1e-9 or (d9 - dd) / 2 - t2 < o["hub_wall"] - 1e-9
                or d9 < D10 + 2 * o["hub_wall"] - 1e-9):
            continue
        tau = 16 * T / (math.pi * d9 ** 3 * (1 - (dd / d9) ** 4))
        if tau <= o["tau_allow"] + 1e-9:
            c09.append(({"id": k9, **b}, tau))
    if not c09:
        return None, (f"нет .09 со стенкой ступицы (d − {dd:g})/2 − t2 {t2:g} ≥ {o['hub_wall']:g}, "
                      f"D ≤ {D_max:.1f} мм в vendor_prices.yaml → bearings")
    B09 = c09[0][0]["B"]
    hl = max(o["ax_gap"] + B09 + o["snap_h"] + o["out_ext"], B10 + o["hub_web"] + l_key + o["ax_gap"])
    return {"link": link, "d": dd, "key": kk, "l_key": l_key,
            "tau": round(16 * T / (math.pi * (dd - t1) ** 3), 1), "tau_allow": ta, "sigma_allow": sa,
            "c09": c09, "hub_l": round(hl, 2),
            "hub_by": "шпонка" if hl > o["ax_gap"] + B09 + o["snap_h"] + o["out_ext"] + 1e-9 else ".09"}, ""


def _fit(forms, Dn, Dv, need, st=None):
    """Формы одной марки -> (труба | None, лист | None, пруток | None)."""
    tubes = sorted((t for t in forms.get("tubes", [])
                    if ptk_join.tube_ok(t, Dn, Dv, st)),
                   key=lambda t: (t["D"], t["s"]))
    sheets = sorted(s for s in forms.get("sheets", []) if s >= need - 1e-9)
    bars = sorted(b for b in forms.get("bars", []) if b >= Dn - 1e-9)
    return tubes[0] if tubes else None, sheets[0] if sheets else None, bars[0] if bars else None


# Формы заготовки .02 по исполнению (Д-68, Д-73, TECH-01): стакан монолитом (cup, .02A, L1) — пруток;
# обечайка с буртом (collar, .02B, L2) — толстостенная труба; обечайка без бурта (plain, .02C, L3) —
# труба или лист (маршрут weld).
FORMS_BY_02 = {"cup": ("bars",), "collar": ("tubes",), "plain": ("tubes", "sheets")}
# Буквы исполнений по ключу варианта (Д-73) — если в products.yaml → parts.<NN>.variants нет таблицы.
V_DEF = {"02": {"cup": "A", "collar": "B", "plain": "C"}, "12": {"flange": "A", "spigot": "A", "insert": "B"}}


def variant_letter(prods, nn, key):
    """Буква исполнения детали nn по ключу варианта конструктива: products.yaml → PTK.parts.<nn>.variants
    ({A: {key: cup, …}}), иначе V_DEF; нет — ""."""
    vs = (((prods or {}).get("PTK", {}).get("parts", {}).get(nn) or {}).get("variants") or {})
    for k, v in vs.items():
        if isinstance(v, dict) and v.get("key") == key:
            return str(k)
    return V_DEF.get(nn, {}).get(key, "")


def blanks(r_in, r_out, stock, mats=None, forms=MAT.FORMS):
    """Заготовка .02 из stock.yaml (Д-56, Д-67, Д-68): марки — по порядку mats (products.yaml →
    PTK.parts."02".material); берётся первая марка, у которой есть подходящая форма из forms
    (FORMS_BY_02 по конструктиву); прочие подходящие — alt/alt_fit (альтернативы с формами),
    марки без подходящей формы — missing. Без mats — все марки stock.yaml; старый формат без
    марок — марка None."""
    if not stock:
        return None
    ta, sa = float(stock.get("tube_allow", 0.5)), float(stock.get("sheet_allow", 0.3))
    Dn, Dv, need = 2 * r_out + 2 * ta, 2 * r_in - 2 * ta, r_out - r_in + 2 * sa
    by = MAT.stock_by_material(stock)
    tried = [str(m) for m in mats] if mats else [m for m in by if m is not None]
    order = [None] if None in by else [m for m in tried if m in by]
    fits = {}
    for m in order:
        f = _fit({k: v for k, v in by[m].items() if k in forms}, Dn, Dv, need, stock)
        if any(x is not None for x in f):
            fits[m] = f
    pick = next(iter(fits), None)
    tube, sheet, bar = fits.get(pick, (None, None, None))
    return {"material": pick, "alt": [m for m in fits if m != pick], "tried": tried,
            "alt_fit": {m: list(fits[m]) for m in fits if m != pick},
            "missing": [m for m in tried if m not in fits], "forms": list(forms),
            "tube": tube, "tube_need": [round(Dn, 2), round(Dv, 2)],
            "sheet": sheet, "sheet_need": round(need, 2),
            "sheet_len": round(math.pi * (r_in + r_out), 1), "bar": bar}


def axial(width, row_gap, b09, b10, r_out, cfg, o, covers, belt=0.0):
    """Осевая компоновка (Д-81); z = 0 — торец пакета со стороны входа, W — длина пакета.

    .07A [−tA, 0]: гнездо .10, tA = B.10 + lip. Гайка пакета эксцентриков — за последним рядом,
    поэтому дно стакана изнутри на z_b = max(W, W − row_gap + nut_h) + ax_gap. .07B [W, W + tB]:
    карман под дно Ø 2(r_out + ax_gap) глубиной z_b + cup_t + ax_gap − W, за ним гнездо .09
    и буртик: tB = карман + B.09 + lip. Ступица d.09, длина ax_gap + B.09 + lip + out_ext;
    отверстие ступицы D.10 сквозь дно — второй .10 на конце входного вала.
    belt — осевая длина соединения .02–.12 (CP-63, Д-76): пояс L (collar) | L + бурт cup_t (insert);
    дно — max(cup_t, belt): карман .07B, tB и длина изделия — с поясом."""
    warn = []
    B09, B10 = (b09 or {}).get("B", 0.0), (b10 or {}).get("B", 0.0)
    D10 = (b10 or {}).get("D", 0.0)
    bot = max(o["cup_t"], belt)
    z_b = max(width, width - row_gap + o["nut_h"]) + o["ax_gap"]
    pocket = z_b + bot + o["ax_gap"] - width
    hub_l = max(o["ax_gap"] + B09 + o["lip"] + o["out_ext"], o.get("hub_l_out") or 0.0)   # CP-90
    fl = bool(o.get("flush"))                                     # Д-103: ступица вровень с .07B
    lipB = o.get("lip_B", o["lip"]) if fl else o["lip"]
    if fl:
        hub_l = o["ax_gap"] + B09 + lipB
    if B10 > bot + hub_l + 1e-9:
        warn.append(f".10 в ступице: B = {B10:g} > длины отверстия {bot + hub_l:g} мм")
    cov = None
    if covers:
        r_pk = r_out + o["ax_gap"]
        r_lim = float(cfg["d_bc"]) / 2 - bolt_clear(cfg["id"]) / 2 - o["seat_wall"]
        if r_pk > r_lim + 1e-9:
            warn.append(f".07B: карман под дно .02 r {r_pk:.2f} > {r_lim:.2f} мм — "
                        f"стенка до отверстий крепежа < seat_wall")
        cov = {"tA": round(B10 + o["lip"], 2), "tB": round(pocket + B09 + lipB, 2),
               "D": cfg["d_out"], "seat_A": D10, "seat_B": (b09 or {}).get("D"),
               "pocket": [round(2 * r_pk, 2), round(pocket, 2)]}
    cup = {"z_in": round(z_b, 2), "t": round(bot, 2), "hub_d": (b09 or {}).get("d"),
           "hub_bore": D10, "hub_l": round(hub_l, 2)}
    length = ((cov["tA"] + cov["tB"] if cov else 0.0) + width + o["out_ext"]
              + hub_l - (o["ax_gap"] + B09 + o["lip"] + o["out_ext"]))       # CP-90: ступица длиннее крышки
    if fl:                                                                   # Д-103: вровень — tA + tB + W
        length = (cov["tA"] + cov["tB"] if cov else 0.0) + width
    return {"covers": cov, "cup": cup, "length": round(length, 2)}, warn


def tooling(rec, cfg, r_in, r_out):
    """Оснастка (Д-81) -> [{fx, part, size, route}]: требования калькулятора, не конструкция FX."""
    out = [{"fx": "разжимная оправка", "part": ".02",
            "size": f"Ø{2 * r_in:.2f} по dc, длина ≥ {float(cfg['width']):g}",
            "route": "точение Dc, окна, контроль — все маршруты тонкой стенки"}]
    if rec["parts"].get("02") == "plain":            # weld — только обечайка без бурта .02C (L3, Д-73)
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
                          f"профиль ЭЭС пакетами по вариантам ({len(var)}); 1 вариант — Д-81")})
    return out


def md_tool(name, r):
    """Строки таблицы «Оснастка» SPEC-11."""
    return [f"| {name} | {t['fx']} | {t['part']} | {t['size']} | {t['route']} |"
            for t in r.get("tooling", [])]


def join_cad(cfg, rec):
    """Геометрия соединения .02–.12 для egm.cad (CP-63, Д-76) -> dict | None (нет соединения):
    схема, z стыка = cup.z_in, пояс L, бурт .12B f, штифты на z стыка + L/2 по осям окон
    последнего ряда (cage + j·360/n), гнездо hole12, ступица; weld — лист и угол шва."""
    p = (rec.get("join") or {}).get("pick")
    if not p:
        return None
    q, g, c = p["pins"], p["geom"], rec["cup"]
    sep, a = cfg.get("sep") or {}, float(cfg.get("a_w", 0.0))
    r_in = float(sep.get("r_in", cfg.get("R_sum", 0.0) - 1.1 * a))
    r_out = float(sep.get("r_out", cfg.get("R_sum", 0.0) + 1.1 * a))
    win = sep.get("rows") or [{"cage": 0.0, "z0": 0.0}]
    last = max(win, key=lambda w: w["z0"])
    ins = p["scheme"] == "insert"
    n = int(sep.get("n") or cfg.get("n") or 0)
    weld = ins and p.get("tube") is None and p.get("sheet")
    res = {"scheme": p["scheme"], "z": c["z_in"], "L": q["L"],
            "f": round(c["t"] - q["L"], 2) if ins else 0.0,
            "r_in": r_in, "r_out": r_out, "r_j": g["r_j"], "D": g["D"], "d": g["d"],
            "pin_d": q["d"], "pin_n": q["n"], "pin_l": q.get("l"), "hole12": q["hole12"],
            "pin_z": round(c["z_in"] + q["L"] / 2, 3),
            "pin_a": [round((last["cage"] + j * 360.0 / q["n"]) % 360, 4) for j in range(q["n"])],
            "hub_d": c["hub_d"], "hub_bore": c["hub_bore"], "hub_l": c["hub_l"],
            "weld": {"sheet": p["sheet"],
                     "seam": round((win[0]["cage"] + 180.0 / n) % 360, 4) if n else None}
            if weld else None}
    if q.get("seat"):                        # CP-90 2b-3 ч. 2, Д-102 п. 2: L2/L4 — опорный обод .12A
        r0 = p["ring"]["r0"] if p["scheme"] == "ring" else g["r0"]        # в отверстии бурта/кольца; радиальные
        res.update(seat=True, axial=False, r_seat=r0, ring=p.get("ring"),  # штифты по окнам (pin_a, pin_z выше);
                   fit=q.get("fit"), **({"dir": p["dir"]} if p.get("dir") else {}))   # .13 нет
        return res
    if p.get("dir"):                         # CP-79, Д-93: collar — бурт h_b + дно-лист t_s, осевые сквозные
        res.update(dir=p["dir"], axial=True, h_b=q["h_b"], t_s=q["t_s"],
                   crit=q["crit"], t_s_min=q["t_s_min"], hub=q.get("hub"),   # CP-80: ступица–лист
                   pin_a=[round(j * 360.0 / q["n"], 4) for j in range(q["n"])])
    if p["scheme"] == "ring":                # CP-81, Д-96: pin_* — радиальные обечайка–кольцо по окнам;
        a, rg, L_r = q["ax"], p["ring"], q["L_r"]      # ax — осевые лист–кольцо (для .12/.13 — cad_parts)
        res.update(L=L_r, pin_z=round(c["z_in"] + L_r / 2, 3), ring=rg, t_s=q["t_s"], crit=q["crit"],
                   t_s_min=q["t_s_min"], hub=q.get("hub"),
                   ax={"axial": True, "h_b": L_r, "r_j": a["r_j"], "pin_d": a["d"], "pin_n": a["n"],   # CP-84, Д-97:
                       "pin_l": a.get("l"), "D": round(2 * r_in, 3), "d": round(2 * rg["r0"], 3),   # лист Ø = расточка
                       "pin_a": [round((last["cage"] + (j + 0.5) * 360.0 / a["n"]) % 360, 4)
                                 for j in range(a["n"])]})
        res["ax"].update(t_s=q["t_s"], hub=q.get("hub"), scheme="ring",
                         fit=(q.get("leaf") or {}).get("fit"))   # CP-84, Д-97: посадка листа в обечайку
    return res


def cad_parts(cfg, name, rec):
    """Детали конструктива для egm.cad (CP-45, Д-73): .02A стакан | .02B обечайка с буртом |
    .02C обечайка без бурта, .07A/.07B, .11; ступица .12A/.12B; соединение — join (CP-63, Д-76).

    ID — <ID>.<NN><вар>-<проработка>, base — без суффикса (Д-48); покупные .09/.10 — в rec."""
    cid = cfg["id"]
    rows = [ph.get("row", k + 1) for k, ph in enumerate(cfg["phasing"])]
    sfx, out, v02 = (f"-{name}" if name else ""), [], rec["parts"].get("02")
    l02 = (rec.get("var") or {}).get("02") or V_DEF["02"].get(v02, "")
    jc = join_cad(cfg, rec)
    if l02:
        base = f"{cid}.02{l02}"
        out.append({"id": base + sfx, "base": base, "rows": rows,
                    **({"cup": rec["cup"]} if v02 == "cup" else {}),
                    **({"join": jc} if jc else {})})
    if rec.get("covers"):
        out += [{"id": f"{cid}.07{s}{sfx}", "base": f"{cid}.07{s}", "rows": rows, "side": s}
                for s in "AB"]
    if rec.get("r11"):
        out.append({"id": f"{cid}.11{sfx}", "base": f"{cid}.11", "rows": rows})
    l12 = (rec.get("var") or {}).get("12")
    jl = {**jc, **jc["ax"]} if jc and jc.get("ax") else jc         # CP-81: .12/.13 в L4 — осевые штифты кольца
    if jc and l12:                                                   # CP-63: ступица .12A | .12B
        base = f"{cid}.12{l12}"
        out.append({"id": base + sfx, "base": base, "rows": rows, "join": jl})
    if jc and jc.get("hub") and rec["parts"].get("13") and not jc.get("seat"):   # CP-80; Д-102 п. 2 — нет .13
        out.append({"id": f"{cid}.13{sfx}", "base": f"{cid}.13", "rows": rows, "join": jl})
    if jc and jc.get("ring") and rec["parts"].get("14"):             # CP-81, Д-96: кольцо-бурт .14
        out.append({"id": f"{cid}.14{sfx}", "base": f"{cid}.14", "rows": rows, "join": jc})
    return out


def layout(cfg, d, ecc, shaft_d, row_gap, prods=None, bears=None, stock=None, pins=None):
    """Конструктив проработки -> (запись | None, ошибки, предупреждения).
    d["layout"] — код или список кодов (Д-73): из списка берётся первый без ошибок (есть заготовка,
    проходят штифты); отклонённые — в предупреждении. pins — vendor_prices.yaml → pins (Д-74)."""
    codes = d.get("layout") or "L1"
    if pins:
        d = {**d, "join": {**(d.get("join") or {}), "pin_cat": ptk_join.pin_cat(pins)}}
    if isinstance(codes, str):
        r, e, w = _one(cfg, d, codes, ecc, shaft_d, row_gap, prods, bears, stock)
        if e and codes != "L3" and any(DEGEN in x for x in e):
            return _to_l3(cfg, d, ecc, shaft_d, row_gap, prods, bears, stock, [f"{codes} — " + "; ".join(e)],
                          (r, e, w))
        return r, e, w
    rej = []
    for code in codes:
        r, e, w = _one(cfg, d, str(code), ecc, shaft_d, row_gap, prods, bears, stock)
        if r is not None and not e:
            return r, e, w + [f"конструктив {code} выбран из {', '.join(map(str, codes))}"
                              + (": " + "; ".join(rej) if rej else "")]
        rej.append(f"{code} — " + "; ".join(e))
    if "L3" not in map(str, codes) and any(DEGEN in x for x in rej):
        return _to_l3(cfg, d, ecc, shaft_d, row_gap, prods, bears, stock, rej, (r, e, w))
    return r, e, w


DEGEN = "вырождаются в L3"   # маркер ошибки _one (Д-102 п. 4): L2/L4 бессмысленны -> L3


def _to_l3(cfg, d, ecc, shaft_d, row_gap, prods, bears, stock, rej, last):
    """Д-102 п. 4: L2/L4 вырождены, L3 в списке нет — калькулятор подставляет L3 сам."""
    r, e, w = _one(cfg, d, "L3", ecc, shaft_d, row_gap, prods, bears, stock)
    if r is not None and not e:
        return r, e, w + ["конструктив L3 подставлен (Д-102 п. 4): " + "; ".join(rej)]
    return last[0], last[1] + [f"L3 (подстановка) — " + "; ".join(e)], last[2]


def _one(cfg, d, code, ecc, shaft_d, row_gap, prods=None, bears=None, stock=None):
    """Один конструктив code -> (запись | None, ошибки, предупреждения)."""
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
    c09 = hub_brgs(bears, M, D10, o, D_max)      # CP-83: кандидаты .09 по D; выбор — ниже, по креплению .13
    b09, tau = c09[0] if c09 else (None, None)
    out = None
    if isinstance(d.get("output"), dict):                    # CP-90, Д-102: вал со шпонкой в ступице
        out, why = (out_flange(M, d["output"], bears, b10, o, D_max) if d["output"].get("link") == "flange"
                    else out_shaft(M, d["output"], d.get("_keys") or [], bears, b10, o, D_max))   # Д-104
        if out is not None:                                   # CP-90 2b-3: добавить grooves если нет
            vp = _vp()
            if "grooves" not in out and b09:
                d9 = b09.get("d", 0.0)
                D9 = b09.get("D", 0.0)
                out["grooves"] = {"ext": {**(vp.get("rings_ext") or {}).get(f"{d9:g}"),
                                            "std": "ГОСТ 13942-86"},
                                "int": {**(vp.get("rings_int") or {}).get(f"{D9:g}"),
                                        "std": "ГОСТ 13943-86"}}
        if out is None:
            err.append(f"выход: {why}")
        else:
            c09 = out["c09"]
            b09, tau = c09[0]
            o = {**o, "hub_l_out": out["hub_l"], "flush": bool(out.get("flush")),
                 "lip_B": out.get("lip_B", o["lip"])}                                 # Д-103, Д-104
            out = {k: v for k, v in out.items() if k != "c09"}
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
    sep = cfg.get("sep") or {}
    r_in = float(sep.get("r_in", cfg["R_sum"] - 1.1 * a))
    r_out = float(sep.get("r_out", cfg["R_sum"] + 1.1 * a))
    mats02, jn, r_pk, belt = MAT.part_materials(prods, "PTK", "02"), None, r_out, 0.0
    if "12" in pr:                                                             # Д-72, OQ-12
        jopt = {**(d.get("join") or {}),                    # схему задаёт конструктив (Д-73)
                **({"join": lay["join"]} if lay.get("join") in ptk_join.SCHEMES else {})}
        # CP-79, Д-93: ограничения корпуса для направления бурта collar — в результат (jn.lim)
        jopt.setdefault("r_lim", float(cfg["d_bc"]) / 2 - bolt_clear(cfg["id"]) / 2
                        - o["seat_wall"] - o["ax_gap"])
        jopt.setdefault("r_free", max(D10 / 2, (r11 or {}).get("d_out", 0.0) / 2) + o["seat_wall"])
        if "14" in pr:                                       # CP-81: марки кольца-бурта .14 (L4)
            jopt.setdefault("ring_mats", MAT.part_materials(prods, "PTK", "14"))
        # CP-83: .09 — первый по D, при котором дно-лист .13 крепится к ступице напрямую (обод под штифты);
        # нет такого — наименьший .09 и фланец (Д-94 → CP-80)
        b0 = b09
        for b, t in (c09 or [(b09, tau)]):
            o2 = dict(jopt)
            o2.setdefault("hub_d", (b or {}).get("d"))              # CP-80: штифты ступица–лист на r_h
            o2.setdefault("hub_bore", D10)
            o2.setdefault("hub_l", o.get("hub_l_out")
                          or o["ax_gap"] + (b or {}).get("B", 0.0) + o["lip"] + o["out_ext"])   # CP-90
            o2.setdefault("pin_wall", o["pin_wall"])
            o2["seat"] = out is not None                            # CP-90 2b-3 ч. 2, Д-102 п. 2: обод в отв. бурта/кольца
            j1 = ptk_join.choose(M, r_in, r_out, stock, mats02, o2, cfg.get("n"))
            if jn is None:
                jn = j1
            if out is not None:                                     # .09 выбран выходом (Д-104) — один проход
                break
            if ptk_join.mode(j1) == "direct":
                jn, b09, tau = j1, b, t
                if b0 is not None and b is not b0:
                    jn["pick"]["brg"] = (f".09 {b['id']} вместо {b0['id']} — обод ступицы под штифты "
                                         f"дна-листа .13 (CP-83)")
                break
        if jn["pick"] is None:
            (err if stock else warn).append(f"{code}: соединение .02–.12 — " + ptk_join.why(jn))
        else:
            p, q = jn["pick"], jn["pick"]["pins"]
            r_pk = max(r_out, p["geom"]["D"] / 2)
            belt = (q["L"] + (o["cup_t"] if p["scheme"] == "insert" else 0.0)    # CP-63, Д-76
                    + (0.0 if (q.get("hub") or {}).get("flush")                 # Д-94: фланец в бурте
                       else (q.get("hub") or {}).get("h_f", 0.0)))                # CP-80: + фланец .12
            rs = ((p["ring"]["r0"] if p["scheme"] == "ring" else p["geom"]["r0"])     # Д-102 п. 2: обод в отв.
                  if q.get("seat") else p["geom"]["r_j"] if p["scheme"] == "insert" else None)
            wall = (rs - q["hole12"] - (b10 or {}).get("D", 0.0) / 2 if rs is not None
                    else o["pin_wall"])   # CP-79: collar — осевые; CP-81: ring — w ≥ hole12 + pin_wall
            if wall < o["pin_wall"] - 1e-9:
                warn.append(f".12: стенка под гнездом штифта {wall:.2f} < pin_wall {o['pin_wall']:g} мм "
                            "(TECH-01, Д-76)")
            n_w = int(cfg.get("n") or 0)
            if (p["scheme"] in ("insert", "ring") or q.get("seat")) and n_w and n_w % q["n"]:
                warn.append(f".02C: штифтов {q['n']} не делитель числа окон {n_w} — отверстия "
                            "не по делению окон (Д-72)")
    # Вырождение L2/L4 → L3 (Д-102 п. 4, уточнение 2026-11-06): при малых диаметрах бурт .02B /
    # кольцо .14 подходит вплотную к ступице — радиальный штифт со стороны окон (крепление фланца
    # ступицы к бурту/кольцу) не помещается; детали неразделимы → единая деталь, т.е. схема L3.
    # cw = seat_wall — минимальная перемычка от r_h ступицы до отверстия штифта (≈ d_r/2 + pin_wall):
    # и для кольца (r0 кольца), и для бурта внутрь (r0 бурта). Штифт крепит опорный обод ступицы
    # (утолщение со стороны сепаратора, Д-102 п. 2) к бурту/кольцу; фланец у ступицы один — на
    # выходном торце (Д-104), к ободу отношения не имеет.
    if out and b09 and jn and jn.get("pick"):
        r_h = (b09.get("da") or (b09["d"] + 0.3 * (b09["D"] - b09["d"]))) / 2   # da нет в каталоге — оценка
        pk, q = jn["pick"], jn["pick"].get("pins") or {}
        out.update(r_h=round(r_h, 2), da_est=not b09.get("da"))
        # Д-102 п. 4 (2026-11-07, заказчик): L2/L4 имеют смысл, только если опорный обод .12A — отдельное
        # утолщение ступицы: s_об = r0 − r_h вмещает гнездо штифта hole12 и перемычку pin_wall до зоны
        # заплечика .09; ob_min — технологический минимум (supports). Иначе (тонкий обод или его нет,
        # r0 ≤ r_h) деление на детали бессмысленно -> ошибка с маркером «вырождаются в L3»; layout()
        # переходит к L3. Прежний критерий r0 ≥ r_h + seat_wall (обод к торцу) не применяется.
        if q.get("seat"):
            ring = pk["scheme"] == "ring"
            r0 = pk["ring"]["r0"] if ring else pk["geom"]["r0"]
            s_ob = r0 - r_h
            s_need = max(q["hole12"] + o["pin_wall"], float(o.get("ob_min") or 0.0))
            out.update(s_ob=round(s_ob, 2), s_ob_need=round(s_need, 2))
            where = f"отв. {'кольца .14' if ring else 'бурта .02B'} r0 {r0:g}, заплечик .09 r_h {r_h:.2f}"
            if s_ob < s_need - 1e-9:
                why = (f"толщина {s_ob:.2f} < {s_need:.2f} (гнездо {q['hole12']:g} + pin_wall {o['pin_wall']:g}"
                       + (f", ob_min {o['ob_min']:g}" if o.get("ob_min") else "") + ")"
                       if s_ob > 1e-9 else "отсутствует (r0 ≤ r_h)")
                err.append(f"{code}: L2/L4 вырождаются в L3 — опорный обод .12A {why}: {where}; "
                           "деление на детали не имеет смысла (Д-102 п. 4)")
            else:
                warn.append(f"{code}: опорный обод .12A s_об {s_ob:.2f} ≥ {s_need:.2f} ({where}; Д-102 п. 4)"
                            + (" — da .09 оценкой" if not b09.get("da") else ""))
    ax, aw = axial(width, row_gap, b09, b10, r_pk, cfg, o, "07" in pr, belt)
    if jn and jn.get("pick") and jn["pick"]["scheme"] == "ring":            # CP-84, Д-97: радиальные L4 вне окон
        qr = jn["pick"]["pins"]
        zw = max((w["z0"] for w in sep.get("rows") or []), default=0.0) + float(sep.get("h") or 0.0)
        z_lo = ax["cup"]["z_in"] + qr["L_r"] / 2 - qr["d"] / 2
        if z_lo < zw + o["pin_wall"] - 1e-9:
            warn.append(f".02C: радиальные штифты L4 от z {z_lo:.2f} заходят в зону окон (до {zw:.2f}) "
                        f"+ pin_wall {o['pin_wall']:g} мм (Д-96)")
    warn += aw
    bl = blanks(r_in, r_out, stock, mats02,
                FORMS_BY_02.get(pr.get("02"), MAT.FORMS))
    if bl is not None and jn and jn["pick"]:
        bl.update(material=jn["pick"]["material"], tube=jn["pick"]["tube"])
        if jn["pick"].get("sheet"):                                  # CP-63: .02C из листа (weld)
            bl["sheet"] = jn["pick"]["sheet"]
    if bl is not None and not (bl["tube"] or bl["sheet"] or bl["bar"]):
        warn.append(".02: нет заготовки" + (f" из {', '.join(bl['tried'])}" if bl["tried"] else "")
                    + f" в stock.yaml (труба Ø ≥ {bl['tube_need'][0]:g} с отв. ≤ "
                    f"{bl['tube_need'][1]:g}, лист ≥ {bl['sheet_need']:g}, пруток Ø ≥ {bl['tube_need'][0]:g})")
    rec = {"code": code, "name": lay.get("name", ""), "parts": pr, "b09": b09, "b10": b10,
           "tau_hub": round(tau, 1) if tau is not None else None, "tau_allow": o["tau_allow"],
           "r11": r11, "covers": ax["covers"], "cup": ax["cup"], "length": ax["length"],
           "blank": bl, "join": jn}
    rec["output"] = out                                          # CP-90, Д-102
    rec["var"] = {nn: variant_letter(prods, nn, pr[nn]) for nn in ("02", "12") if pr.get(nn)}
    rec["var_name"] = {nn: variant_name(prods, nn, pr[nn]) for nn in rec["var"]}
    rec["tooling"] = tooling(rec, cfg, r_in, r_out)
    rec.update(shaft_d=shaft_d, ax_gap=o["ax_gap"])
    rec["cad_parts"] = cad_parts(cfg, d.get("name", ""), rec)
    return rec, err, warn


def _b(b):
    return f"{b['id']} {b['d']:g}×{b['D']:g}×{b['B']:g}" if b else "нет"


def _forms_txt(tube, sheet, bar, sheet_len):
    """Формы одной марки -> ["труба D×s", "лист t, L", "пруток ØD"]."""
    s = [f"труба {tube['D']:g}×{tube['s']:g}"] if tube else []
    s += [f"лист {sheet:g}, L {sheet_len:g}"] if sheet else []
    s += [f"пруток Ø{bar:g}"] if bar else []
    return s


def md_row(name, r):
    """Строка таблицы «Конструктив» SPEC-11."""
    bl, s = r["blank"], []
    if bl:
        s = _forms_txt(bl["tube"], bl["sheet"], bl["bar"], bl["sheet_len"])
        if bl.get("material") and s:
            s = [f"{bl['material']}: {', '.join(s)}"]
        for m, f in (bl.get("alt_fit") or {}).items():
            s.append(f"альтернатива {m}: {', '.join(_forms_txt(*f, bl['sheet_len']))}")
        if bl.get("missing"):
            s.append("нет подходящей заготовки: " + ", ".join(bl["missing"]))
    tau = f"{r['tau_hub']:g} / {r['tau_allow']:g}" if r["tau_hub"] is not None else "—"
    r11 = f"{r['r11']['n']} × {r['r11']['h']:g}" if r["r11"] else "—"
    cov = f"{r['covers']['tA']:g} / {r['covers']['tB']:g}" if r["covers"] else "—"
    c = r["cup"]
    cup = f"{c['z_in']:g} / {c['t']:g}" + (f"; Ø{c['hub_d']:g}×{c['hub_l']:g}" if c["hub_d"] else "")
    if r.get("join"):
        cup += "; " + ptk_join.short(r["join"])
    var = r.get("var") or {}
    return (f"| {name} | {r['code']} — {r['name']} | {', '.join('.' + k + var.get(k, '') for k in sorted(r['parts']))} | "
            f"{_b(r['b09'])} | {tau} | {_b(r['b10'])} | {r11} | {cov} | {cup} | {r['length']:g} | "
            f"{'; '.join(s) or ('нет stock.yaml' if bl is None else 'нет')} |")


def variant_name(prods, nn, key):
    """Краткое имя исполнения: products.yaml → PTK.parts.<nn>.variants.<буква>.name до «:» / «;»."""
    vs = (((prods or {}).get("PTK", {}).get("parts", {}).get(nn) or {}).get("variants") or {})
    for v in vs.values():
        if isinstance(v, dict) and v.get("key") == key:
            return re.split(r"[:;]", str(v.get("name", "")))[0].strip()
    return ""


def _vname(r, nn):
    """Ячейка исполнения «.02B — обечайка с буртом…»; детали нет — «нет»."""
    if nn not in r["parts"]:
        return "нет (ступица — часть .02)" if nn == "12" else "нет"
    v, n = (r.get("var") or {}).get(nn, ""), (r.get("var_name") or {}).get(nn, "")
    return f".{nn}{v}" + (f" — {n}" if n else "")


def _blank_rows(name, bl):
    """Строки таблицы «Заготовка .02»: выбранная марка, альтернативы, марки без заготовки."""
    if bl is None:
        return [f"| {name} | — | нет stock.yaml | — |"]
    out, s = [], _forms_txt(bl["tube"], bl["sheet"], bl["bar"], bl["sheet_len"])
    if s:
        out.append(f"| {name} | {bl.get('material') or '—'} | выбрана | {', '.join(s)} |")
    for m, f in (bl.get("alt_fit") or {}).items():
        out.append(f"| {name} | {m} | альтернатива | {', '.join(_forms_txt(*f, bl['sheet_len']))} |")
    if bl.get("missing"):
        out.append(f"| {name} | {', '.join(bl['missing'])} | нет подходящей заготовки | — |")
    return out or [f"| {name} | — | нет | — |"]


def md_nomenclature():
    """Блок номенклатуры позиций .01–.14 (ID → наименование)."""
    NOMEN = [
        ("01", "Венец (корпус)"),
        ("02", "Сепаратор"),
        ("02A", "Сепаратор L1: стакан монолитом"),
        ("02B", "Сепаратор L2: обечайка с буртом"),
        ("02C", "Сепаратор L3/L4: обечайка без бурта"),
        ("03", "Эксцентрик"),
        ("04", "Гильза"),
        ("05", "Межрядная шайба"),
        ("07A", "Крышка входа"),
        ("07B", "Крышка выхода"),
        ("08", "Тело качения"),
        ("09", "Подшипник выхода"),
        ("10", "Подшипник генератора (входное гнездо)"),
        ("11", "Дистанционное кольцо"),
        ("12", "Ступица выхода"),
        ("12A", "Ступица L2/L4: с опорным ободом"),
        ("12B", "Ступица L3: дно-вставка"),
        ("13", "Дно-лист (отменено, CANCELLED)"),
        ("14", "Кольцо-бурт L4"),
    ]
    lines = ["| ID | Наименование элемента |"]
    lines.append("|---|---|")
    for nid, nname in NOMEN:
        lines.append(f"| {nid} | {nname} |")
    return "\n".join(lines)


def get_nomenclature_desc(pos):
    """Возвращает наименование по позиции спецификации (.NN)."""
    NOMEN = {
        "01": "Венец (корпус)",
        "02": "Сепаратор",
        "02A": "Сепаратор L1: стакан монолитом",
        "02B": "Сепаратор L2: обечайка с буртом",
        "02C": "Сепаратор L3/L4: обечайка без бурта",
        "03": "Эксцентрик",
        "04": "Гильза",
        "05": "Межрядная шайба",
        "07A": "Крышка входа",
        "07B": "Крышка выхода",
        "08": "Тело качения",
        "09": "Подшипник выхода",
        "10": "Подшипник генератора (входное гнездо)",
        "11": "Дистанционное кольцо",
        "12": "Ступица выхода",
        "12A": "Ступица L2/L4: с опорным ободом",
        "12B": "Ступица L3: дно-вставка",
        "13": "Дно-лист (отменено, CANCELLED)",
        "14": "Кольцо-бурт L4",
    }
    # Определяем букву исполнения: 02A, 02B, 02C, 12A, 12B
    base = pos.rstrip("ABC")
    letter = pos[len(base):] if len(pos) > len(base) else ""
    key = base + letter if letter else base
    return NOMEN.get(key, NOMEN.get(base, "—"))


def md_layouts_info():
    """Блок справочной информации о конструктивах L1–L4.

    Заголовок "## Конструктивы L1–L4" НЕ включается — он есть в шаблоне.
    Возвращает только описание и таблицы по каждому L1–L4.
    """
    lines = [
        "Конструктив — выбор номенклатуры деталей и схемы соединения .02–.12 (Д-55, Д-73, Д-102).",
        "",
        "#### Расшифровка обозначений",
        "",
        "В разделе используются следующие обозначения напряжений и параметров:",
        "",
        "| Обозначение | Что это | Для чего используется |",
        "|---|---|---|",
        "| **τ ступицы** | Касательное напряжение кручения в ступице .12 | Проверка прочности ступицы при передаче выходного момента. [τ] — допускаемое значение (обычно 25 МПа для сталей 40Х/35ХМ). Если τ > [τ] — ступица не проходит по кручению, нужен больший Ø ступицы или более прочный материал.",
        "| **τ среза штифта** | Касательное напряжение среза в штифте соединения | Проверка штифта на срез силой, передаваемой от сепаратора к ступице. [τ] — допускаемое напряжение сдвига штифта (обычно 80 МПа). Если τ > [τ] — штифт не проходит, нужно увеличить Ø или число штифтов.",
        "| **σсм стенки** | Напряжение смятия стенки сепаратора .02 под штифтом | Проверка тонкостенной обечайки .02C на продавливание штифтом. [σсм] — допускаемое смятие (обычно 150 МПа). Если σсм > [σсм] — стенка не проходит, нужно увеличить толщину или Ø штифта.",
        "| **σсм ступицы** | Напряжение смятия ступицы .12 под штифтом | Проверка ступицы .12 на продавливание штифтом. [σсм] — допускаемое смятие (обычно 150 МПа). Если σсм > [σсм] — ступица не проходит, нужно увеличить толщину стенки или число штифтов.",
        "| **τ среза к торцу** | Касательное напряжение среза перемычки от штифта до торца детали | Проверка перемычки между отверстием штифта и внешним торцем (внутреннего кольца .09 или наружной поверхности). [τ] — допускаемое значение (обычно 90 МПа). Если τ > [τ] — перемычка не проходит, нужно увеличить Ø отверстия или сместить штифт.",
        "| **r_h .09** | Радиус заплечика подшипника .09 (da/2) | Внутренняя граница опорного обода .12A. Используется для проверки толщины обода: s_об = r0 − r_h, где r0 — отверстие бурта/кольца. Если s_об < требуется — конструктив вырождается (L2/L4 → L3).",
        "",
    ]

    layouts_info = [
        ("L1", "стакан монолитом",
         [(".02A", "стакан монолитом (обечайка с окнами, дно и ступица выхода — одна деталь)")],
         "Моноблок: .02 = cup, .12 = None (ступица — часть .02)."),
        ("L2", "обечайка с буртом",
         [(".02B", "обечайка с буртом на выходном торце (толстостенная труба)"),
          (".12A", "ступица с опорным ободом, входит в отверстие бурта .02B"),
          ("Схема collar", "бурт .02B, к его торцу дно-лист .13 осевыми штифтами, ступица .12A — к листу")],
         "Бурт .02B передаёт момент через осевые штифты .13; опорный обод .12A — в отверстии бурта."),
        ("L3", "обечайка без бурта",
         [(".02C", "обечайка без бурта (стенка как у окон по всей длине)"),
          (".12B", "дно-вставка внутри .02C"),
          ("Схема insert", "обечайка без бурта, дно-вставка .12B внутри, радиальные штифты через стенку по окнам")],
         "Радиальные штифты .02–.12 через стенки .02C; дно-вставка .12B внутри обечайки."),
        ("L4", "обечайка без бурта + кольцо-бурт",
         [(".02C", "обечайка без бурта"),
          (".14", "кольцо-бурт в выходном торце .02C"),
          (".13", "дно-лист к кольцу .14 осевыми штифтами"),
          (".12A", "ступица с опорным ободом, входит в отверстие кольца .14"),
          ("Схема ring", "кольцо-бурт .14 в торце .02C радиальными штифтами по окнам, лист .13 к кольцу осевыми")],
         "Кольцо-бурт .14 заменяет бурт .02B; опорный обод .12A — в отверстии кольца .14 (посадка H7/js6)."),
    ]

    for code, name, details, desc in layouts_info:
        lines.append(f"### {code} — {name}")
        lines.append("")
        lines.append(desc)
        lines.append("")
        if details:
            lines.append("| Характерная деталь | Описание |")
            lines.append("|---|---|")
            for det_name, det_desc in details:
                lines.append(f"| {det_name} | {det_desc} |")
            lines.append("")

    return "\n".join(lines)


def md_tables(items):
    """Раздел «Конструктив» SPEC-11 (Д-74): [(проработка, запись)] -> таблицы: состав;
    опоры, кольца, крышки, дно; соединение .02–.12 (если есть L2/L3); заготовка .02.

    Добавлено: таблица «Номенклатура» с позициями .01–.14 (ID → наименование).
    """
    # CP-84 (замечание заказчика): расшифровка кодов деталей — человеческими именами
    A = ["### Состав", "", "| ID | Наименование элемента |", "|---|---|"]
    B = ["### Опоры, кольца, крышки, дно "
         "(.09 — подшипник выхода, .10 — подшипник генератора, .11 — дистанционные кольца, "
         ".07A/B — крышки входа/выхода, .02 — дно, .12 — ступица)", "",
         "| Проработка | .09 d×D×B | τ ступицы / [τ], МПа | .10 d×D×B | .11 n × h, мм | "
         "Крышки .07A / .07B, мм | Дно .02 z / t, мм | Ступица Ø × L, мм |", "|---" * 8 + "|"]
    J = ["### Соединение .02 (сепаратор) – .12 (ступица выхода) (Д-72, Д-74)", "",
         ptk_join.JOIN_HEAD, ptk_join.JOIN_RULE]
    S = ["### Заготовка .02 (сепаратор) (Д-67, Д-68)", "", "| Проработка | Марка | Статус | Формы |",
         "|---" * 4 + "|"]
    O = ["### Выход: вал в ступице .12 / дне .02A (Д-102, CP-90)", "",
         "| Проработка | Вал d_o, мм | Шпонка b×h×l | τ вала / [τ], МПа | [σсм], МПа | .09 | "
         "Ступица L, мм (по) | r_h .09 |", "|---" * 8 + "|"]

    # Номенклатура — общая для всех проработок (одинаковый набор позиций)
    NOMEN = [
        ("01", "Венец (корпус)"),
        ("02", "Сепаратор"),
        ("02A", "Сепаратор L1: стакан монолитом"),
        ("02B", "Сепаратор L2: обечайка с буртом"),
        ("02C", "Сепаратор L3/L4: обечайка без бурта"),
        ("03", "Эксцентрик"),
        ("05", "Межрядная шайба"),
        ("07A", "Крышка входа"),
        ("07B", "Крышка выхода"),
        ("08", "Тело качения"),
        ("09", "Подшипник выхода"),
        ("10", "Подшипник генератора (входное гнездо)"),
        ("11", "Дистанционное кольцо"),
        ("12", "Ступица выхода"),
        ("12A", "Ступица L2/L4: с опорным ободом"),
        ("12B", "Ступица L3: дно-вставка"),
        ("13", "Дно-лист (отменено, CANCELLED)"),
        ("14", "Кольцо-бурт L4"),
    ]
    for nid, nname in NOMEN:
        A.append(f"| {nid} | {nname} |")

    # Пустая строка, затем шапка и строки проработок
    A.append("")
    A.append("| Проработка | Конструктив | Сепаратор .02 | Ступица .12 | Детали | Длина, мм |")
    A.append("|---|---|---|---|---|---|")

    for name, r in items:
        var, c = r.get("var") or {}, r["cup"]
        det = ", ".join("." + k + var.get(k, "") for k in sorted(r["parts"]))
        A.append(f"| {name} | {r['code']} — {r['name']} | {_vname(r, '02')} | {_vname(r, '12')} | "
                 f"{det} | {r['length']:g} |")
        tau = f"{r['tau_hub']:g} / {r['tau_allow']:g}" if r["tau_hub"] is not None else "—"
        r11 = f"{r['r11']['n']} × {r['r11']['h']:g}" if r["r11"] else "—"
        cov = f"{r['covers']['tA']:g} / {r['covers']['tB']:g}" if r["covers"] else "—"
        hub = f"Ø{c['hub_d']:g} × {c['hub_l']:g}" if c["hub_d"] else "—"
        B.append(f"| {name} | {_b(r['b09'])} | {tau} | {_b(r['b10'])} | {r11} | {cov} | "
                 f"{c['z_in']:g} / {c['t']:g} | {hub} |")
        if r.get("join"):
            J.append(ptk_join.join_row(name, r["join"]))
        S += _blank_rows(name, r["blank"])
        u = r.get("output")
        if u:
            k = u.get("key")
            kt = f"{k['b']:g}×{k['h']:g}×{u['l_key']:g}" if k else (u.get("fl_txt") or u["link"])   # Д-104
            rh = (f"{u['r_h']:g}" + (" (оценка da)" if u.get("da_est") else "")) if u.get("r_h") else "—"
            O.append(f"| {name} | {u['d']:g} | {kt} | {u['tau']:g} / {u['tau_allow']:g} | "
                     f"{u['sigma_allow']:g} | {_b(r['b09'])} | {u['hub_l']:g} ({u['hub_by']}) | {rh} |")
    out = (A + [""] + B + ([""] + J if len(J) > 4 else []) + ([""] + O if len(O) > 4 else [])
           + [""] + S)
    return "\n".join(out)


def self_test():
    """L1 для PTK-050/61810: .10 = 61800, .09 = 61806 (τ ступицы), .11 1×3 шт; заготовки; ошибки."""
    bears = {"_comment": "x", "61800": {"d": 10.0, "D": 19.0, "B": 5.0},
             "61804": {"d": 20.0, "D": 32.0, "B": 7.0}, "61805": {"d": 25.0, "D": 37.0, "B": 7.0},
             "61806": {"d": 30.0, "D": 42.0, "B": 7.0}, "61810": {"d": 50.0, "D": 65.0, "B": 7.0}}
    prods = {"PTK": {"layouts": {
        "L1": {"name": "стакан", "fixed": "ring", "output": "cage",
               "parts": {"02": "cup", "07": "side", "09": "out", "10": "in", "11": "ring", "12": None}},
        "L2": {"name": "обечайка с буртом", "fixed": "ring", "output": "cage", "join": "collar",
               "parts": {"02": "collar", "07": "side", "09": "out", "10": "in", "11": "ring", "12": "spigot"}},
        "L3": {"name": "обечайка без бурта", "fixed": "ring", "output": "cage", "join": "insert",
               "parts": {"02": "plain", "07": "side", "09": "out", "10": "in", "11": "ring", "12": "insert"}}}}}
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
    assert b["bar"] == 70.0 and (b["tube"] == {"D": 70.0, "s": 2.5}) == ("tubes" in b["forms"]) \
        and (b["sheet"] == 1.5) == ("sheets" in b["forms"]), b
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
    b5 = blanks(32.5, 34.0, st2, ["38Х2МЮА", "40ХН2МА", "40Х"], FORMS_BY_02["cup"])
    assert (b5["material"], b5["bar"], b5["tube"], b5["missing"]) == \
        ("40Х", 70.0, None, ["38Х2МЮА", "40ХН2МА"]), b5
    b6 = blanks(32.5, 34.0, st2, ["40Х", "40ХН2МА"])
    assert b6["alt_fit"] == {"40ХН2МА": [{"D": 73.0, "s": 14.0}, None, None]}, b6
    assert "61806" in md_row("K10", r)
    ids = [q["id"] for q in r["cad_parts"]]                                   # CP-45
    assert ids == ["PTK-T-8M4P2-AAAAAA.02A", "PTK-T-8M4P2-AAAAAA.07A", "PTK-T-8M4P2-AAAAAA.07B",
                   "PTK-T-8M4P2-AAAAAA.11"], ids
    assert r["cad_parts"][0]["rows"] == [1, 2, 3, 4] and r["cad_parts"][0]["cup"] == r["cup"]
    assert cad_parts({"id": "X", "phasing": [{}] * 2}, "K", r)[1]["id"] == "X.07A-K"
    assert r["var"] == {"02": "A"} and ".02A, " in md_row("K10", r), r["var"]       # Д-73
    assert variant_letter({"PTK": {"parts": {"12": {"variants": {"X": {"key": "insert"}}}}}},
                          "12", "insert") == "X" and variant_letter(None, "12", "spigot") == "A"
    r2, e2, _ = layout(cfg, {"layout": "L2"}, ecc, 10.0, 1.0, prods, bears, stock)
    assert any("collar: нет трубы" in x for x in e2) and r2["var"] == {"02": "B", "12": "A"}, \
        (e2, r2["var"])
    rc, ec, _ = layout(cfg, {"layout": "L3"}, ecc, 10.0, 1.0, prods, bears, stock)
    jc = rc["join"]["pick"]
    assert not ec and (jc["scheme"], jc["pins"]["n"]) == ("insert", 8) and \
        rc["blank"]["tube"] == {"D": 70.0, "s": 2.5}, (ec, rc["join"])
    assert rc["var"] == {"02": "C", "12": "B"} and ".02C, " in md_row("K", rc) and \
        ".12B" in md_row("K", rc) and "соединение insert" in md_row("K", rc)
    assert rc["cad_parts"][0]["id"] == "PTK-T-8M4P2-AAAAAA.02C", rc["cad_parts"]
    assert any("медной" in t["fx"] for t in rc["tooling"]), rc["tooling"]
    assert any(t["fx"] == "вальцовка" and "лист 1.5" in t["size"] for t in rc["tooling"])
    assert not any(t["fx"] == "вальцовка" for t in r2["tooling"])
    rl, el, wl = layout(cfg, {"layout": ["L2", "L3"]}, ecc, 10.0, 1.0, prods, bears, stock)
    assert not el and rl["code"] == "L3" and any("L2 —" in x for x in wl), wl
    _, e3, _ = layout({**cfg, "d_bc": 40.0}, {"layout": "L1"}, ecc, 10.0, 1.0, prods, bears, stock)
    assert any(".09" in x for x in e3), e3
    _, e4, _ = layout(cfg, {"layout": "L9"}, ecc, 10.0, 1.0, prods, bears, stock)
    assert e4 and "L9" in e4[0], e4
    assert layout(cfg, {}, ecc, 10.0, 1.0, prods, bears, None)[0]["blank"] is None
    t = md_tables([("K10", r), ("K", rc), ("K2", r2)])                           # Д-74
    assert "61806" in t and "| K10 | L1 — стакан |" in t and "нет (ступица — часть .02)" in t, t
    assert "### Соединение" in t and "| K | insert |" in t and ".02C, " in t, t
    assert "| K2 | нет |" in t and "collar: нет трубы" in t, t
    assert md_tables([("K10", r)]).count("### ") == 3
    rp, _, _ = layout(cfg, {"layout": "L3"}, ecc, 10.0, 1.0, prods, bears, stock,
                      {"P3": {"d": 3.0, "l": [8, 10], "std": "ГОСТ 24296-93"}})
    assert rp["join"]["pick"]["pins"]["des"] == "Штифт 3×8 ГОСТ 24296-93", rp["join"]
    assert rc["cup"]["t"] == 11.0 and rc["length"] == 64.0, (rc["cup"], rc["length"])  # CP-63
    assert [q["id"].split(".")[-1] for q in rc["cad_parts"]] == ["02C", "07A", "07B", "11", "12B"], \
        rc["cad_parts"]
    jc = rc["cad_parts"][-1]["join"]
    assert (jc["scheme"], jc["f"], jc["pin_z"], len(jc["pin_a"])) == ("insert", 2.0, 41.0, 8), jc
    assert rc["cad_parts"][0]["join"] == jc and r["cup"]["t"] == 2.0, rc["cad_parts"][0]
    ks = [{"d_max": 30, "b": 8, "h": 7, "t1": 4.0, "t2": 3.3},
          {"d_max": 38, "b": 10, "h": 8, "t1": 5.0, "t2": 3.3}]                   # CP-90, Д-102
    ro, eo, _ = layout(cfg, {"layout": "L1", "output": {"link": "key"}, "_keys": ks},
                       ecc, 10.0, 1.0, prods, bears, stock)
    assert not eo and ro["output"]["d"] >= 30 and ro["b09"]["id"] == "61810", (eo, ro["output"])
    assert ro["cup"]["hub_l"] == ro["output"]["hub_l"] and "### Выход" in md_tables([("K", ro)])
    return True
