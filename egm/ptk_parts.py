"""Детали ПТК: .02 сепаратор, .03 эксцентрик — геометрия и балансировка (CP-35, Д-46).

Числа считаются здесь (слой расчёта, Д-39) и попадают в ptk_configs.json → sep, ecc;
egm/cad/ptk_sep.py и ptk_ecc.py только строят PartModel.

Сепаратор .02 — одна деталь на пакет: втулка R_Σ ± SEP_K·a_ω длиной B пакета с прямыми
радиальными окнами (тела движутся строго радиально); окна ряда k повёрнуты на
φk mod (360/n) — ptk.phasing → cage.
Эксцентрик .03 — диск толщиной t: наружный Ø D_э со смещением a_ω (посадка подшипника d
или поверхность качения D_г), отверстие под вал shaft_d_min с пазом шпонки; паз ряда k —
на угле key_angle − φk от эксцентриситета, отсюда варианты .03A… по рядам.
Балансировка ряда (Д-36): U = U_диска + m_подш·a_ω + (n/2)·m_тела·a_ω, г·мм; снимается
N сквозными отверстиями Ø d на радиусе r_h со стороны эксцентриситета:
U_отв = ρ·t·π·d²/4·r_h·Σcos β_j. Паз шпонки (~1 % U) не учитывается.
"""
import math

from egm.ptk_profile import Y


def separator(n, R, a, D, l, pitch, rows, lim, sep_k):
    """Сепаратор: радиусы, окна w × h, положение окон рядов по оси и углу."""
    r_in, r_out = R - sep_k * a, R + sep_k * a
    w, h = D + lim.sep_gap, l + lim.sep_gap
    win = [{"row": row["row"],
            "cage": round(((-row["s"] * (n + 1) - row["phi"]) / n) % (360 / n), 4),
            "z0": round(lim.row_gap + k * (pitch + lim.row_gap) + (pitch - h) / 2, 3)}
           for k, row in enumerate(rows)]
    return {"n": n, "r_in": round(r_in, 3), "r_out": round(r_out, 3), "w": round(w, 3),
            "h": round(h, 3), "length": round(len(rows) * pitch + (len(rows) + 1) * lim.row_gap, 3),
            "web": round(2 * r_in * math.sin(math.pi / n) - w, 3), "rows": win}


def _fit(N, d, a, Re, r_lo, w):
    """N отверстий Ø d у наружной кромки, перемычки w -> (r_h, [β, рад]) | None."""
    r = Re + a - w - d / 2
    for _ in range(500):
        r = math.floor(r * 100 + 1e-9) / 100
        if r - d / 2 < r_lo - 1e-9 or (N > 1 and d + w > 2 * r):
            return None
        db = 2 * math.asin((d + w) / (2 * r)) if N > 1 else 0.0
        bs = [(j - (N - 1) / 2) * db for j in range(N)]
        if abs(bs[0]) > math.pi / 2:
            return None
        r_max = min(Y(b, a, Re) for b in bs) - w - d / 2
        if r <= r_max + 1e-9:
            return r, bs
        r = min(r - 0.01, r_max)
    return None


def balance(U, a, Re, t, rho, r_lo, lim):
    """Подбор N × Ø d с наименьшим |U − U_отв|; N = 0 — без отверстий."""
    k = rho * t * math.pi / 4
    best = (abs(U), 0, 0.0, 0.0, [], 0.0)
    ds = getattr(lim, "bal_drills", None)       # Д-48: только свёрла из списка
    for N in range(1, int(lim.bal_n_max) + 1):
        i = 0
        while True:
            if ds is not None and i >= len(ds):
                break
            d = ds[i] if ds is not None else round(lim.bal_d_min + i * lim.bal_d_step, 4)
            g = _fit(N, d, a, Re, r_lo, lim.bal_wall)
            if g is None:
                break
            r, bs = g
            Ur = k * d * d * r * sum(math.cos(b) for b in bs)
            if abs(U - Ur) < best[0] - 1e-9:
                best = (abs(U - Ur), N, d, r, bs, Ur)
            if Ur >= U:
                break
            i += 1
    _, N, d, r, bs, Ur = best
    return {"n": N, "d": d, "r": r, "U_rem": round(Ur, 2), "res": round(U - Ur, 2),
            "holes": [(round(r * math.cos(b), 3), round(r * math.sin(b), 3)) for b in bs]}


def eccentric(n, a, D, rol, brg, rows, lim, gen, R):
    """Эксцентрик ряда: размеры, дисбаланс, отверстия балансировки, пазы шпонки рядов."""
    rho = lim.rho * 1e-6                                  # г/мм³
    if gen == "bearing":
        De, t, est = brg["d"], brg["B"], not brg.get("m")
        m_b = (rho * lim.brg_mass_k * math.pi / 4 * (brg["D"] ** 2 - brg["d"] ** 2) * brg["B"]
               if est else brg["m"] * 1e3)
    else:
        De, t, m_b, est = 2 * R - D, rol["l"], 0.0, False
    ball = rol.get("type", "roller") == "ball"
    vol = math.pi * D ** 3 / 6 if ball else math.pi * D * D * rol["l"] / 4
    U = {"disk": rho * t * math.pi * De * De / 4 * a, "brg": m_b * a,
         "bodies": n / 2 * rho * vol * a}
    U["sum"] = sum(U.values())
    rs, t2 = lim.shaft_d_min / 2, lim.shaft_key_t2
    bal = balance(U["sum"], a, De / 2, t, rho, rs + t2 + lim.bal_wall, lim)
    warns = []
    if abs(bal["res"]) > 0.05 * U["sum"]:
        warns.append(f"эксцентрик: остаток дисбаланса {bal['res']:g} из {U['sum']:.1f} г·мм — "
                     f"отверстия балансировки не помещаются (Д-46)")
    out = []
    for row in rows:
        ka = round((lim.key_angle - row["phi"]) % 360, 3)
        wall = Y(math.radians(ka), a, De / 2) - rs - t2
        if wall < lim.ecc_wall_min - 1e-9:
            warns.append(f"ряд {row['row']}: стенка эксцентрика у паза шпонки {wall:.2f} < "
                         f"ecc_wall_min {lim.ecc_wall_min:g} мм — изменить key_angle (Д-46)")
        out.append({"row": row["row"], "phi": row["phi"], "key_angle": ka,
                    "key_wall": round(wall, 2)})
    return {"De": round(De, 3), "t": t, "a": a, "d_shaft": lim.shaft_d_min,
            "key_b": lim.shaft_key_b, "key_t2": t2, "m_brg_g": round(m_b, 1), "m_brg_est": est,
            "groove_r": round(lim.groove_f * D, 3) if ball and gen == "eccentric" else None,
            "U": {k: round(v, 2) for k, v in U.items()}, "bal": bal, "rows": out,
            "warnings": warns}


def parts(cid, ecc):
    """Детали .02 (одна на пакет) и .03<вариант> (по пазу шпонки ряда)."""
    out = [{"id": f"{cid}.02", "name": "сепаратор", "variant": "",
            "rows": [x["row"] for x in ecc["rows"]]}]
    var = {}
    for x in ecc["rows"]:
        v = var.setdefault(x["key_angle"], chr(ord("A") + len(var)))
        p = next((q for q in out if q["id"] == f"{cid}.03{v}"), None)
        if p is None:
            p = {"id": f"{cid}.03{v}", "name": "эксцентрик", "variant": v,
                 "key_angle": x["key_angle"], "rows": []}
            out.append(p)
        p["rows"].append(x["row"])
    return out


def table(rows):
    """SPEC-10: детали .02, .03 реализуемых исполнений."""
    L = ["| ID | Генератор | Dэ × t, мм | Пазы шпонки, ° | U, г·мм | Отв. балансировки | "
         "Остаток, г·мм | Сепаратор dс / Dс × B | Окна w × h | Перемычка |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        e, s = r.get("ecc"), r.get("sep")
        if not e or not s:
            continue
        b = e["bal"]
        holes = f"{b['n']}×Ø{b['d']:g}, r {b['r']:g}" if b["n"] else "нет"
        keys = ", ".join(f"{x['key_angle']:g}" for x in e["rows"])
        L.append(f"| {r['id']} | {r['bearing'] or 'эксцентрик'} | {e['De']:g} × {e['t']:g} | {keys} | "
                 f"{e['U']['sum']:g} | {holes} | {b['res']:g} | "
                 f"{2 * s['r_in']:g} / {2 * s['r_out']:g} × {s['length']:g} | "
                 f"{s['w']:g} × {s['h']:g} | {s['web']:g} |")
    return "\n".join(L) if len(L) > 2 else "нет реализуемых исполнений"


def self_test():
    from types import SimpleNamespace
    lim = SimpleNamespace(sep_gap=0.05, row_gap=1.0, rho=7850.0, brg_mass_k=0.35,
                          shaft_d_min=6.0, shaft_key_b=2.0, shaft_key_t2=1.0, bal_wall=1.0,
                          bal_n_max=3, bal_d_min=1.0, bal_d_step=0.1, ecc_wall_min=1.0,
                          key_angle=45.0, groove_f=0.52)
    rows = [{"row": k + 1, "phi": p, "s": -p} for k, p in enumerate((0, 90, 180, 270))]
    s = separator(50, 33.5, 0.4, 2.0, 4.2, 7.0, rows, lim, 1.1)
    assert s["web"] > 0 and len(s["rows"]) == 4, s
    c = s["rows"][1]["cage"]
    assert abs(c - 90 % 7.2) < 1e-6, ("s = −φ: cage = φ mod 360/n (Д-46)", c)
    s0 = separator(50, 33.5, 0.4, 2.0, 4.2, 7.0, [{**x, "s": 0.0} for x in rows], lim, 1.1)
    c0 = s0["rows"][1]["cage"]
    assert abs(c0 - (-90 / 50) % 7.2) < 1e-6, ("s = 0: cage = −φ/n mod 360/n (Д-46)", c0)
    e = eccentric(50, 0.4, 2.0, {"type": "roller", "d": 2.0, "l": 4.2},
                  {"d": 50.0, "D": 65.0, "B": 7.0}, rows, lim, "bearing", 33.5)
    assert e["bal"]["n"] >= 1 and abs(e["bal"]["res"]) <= 0.05 * e["U"]["sum"], e["bal"]
    assert not e["warnings"], e["warnings"]
    p = parts("PTK-T", e)
    assert [q["id"] for q in p] == ["PTK-T.02", "PTK-T.03A", "PTK-T.03B", "PTK-T.03C",
                                    "PTK-T.03D"], p
    return True
