"""Виртуальный технологический процесс заготовки стакана-ступицы ПТК (CP-93, Д-114, TECH-03).

Модель слоя 2 SPEC-04: по патенту RU 2538792 C1 считает деление деформации по переходам и
между роликами, размеры профилей роликов и требования к оснастке; усилие — оценка по Зибелю.

Границы применимости: геометрия и соотношения — из пунктов формулы (п. 2–13) и проверяются
assert'ами; усилие и время — инженерная оценка, калибруется пробной раскаткой (OQ-37).
"""
import math

# SUP — технологические константы раскатки (границы из формулы RU 2538792 C1, пункты указаны)
SUP = {
    "n_roll": 3,            # роликов на переход (п. 1, 7, 8)
    "k_pass": (1.1, 1.5),   # рост степени деформации между переходами (п. 2)
    "k_roll": (1.2, 3.0),   # спад степени деформации между роликами перехода (п. 2)
    "cone_deg": (5.0, 15.0),  # угол наклона конических переходных участков (п. 3)
    "cyl_min": 1.0,         # длина цилиндрического участка ≥ 1.0·T0 (п. 3)
    "r1": (0.4, 1.0),       # радиус вершины первого ролика, доли T0 (п. 5)
    "b_lat": (0.3, 0.5),    # плоская вершина последующих, доли T0 (п. 5)
    "gamma": (1.0, 5.0),    # наклон плоской вершины, град (п. 5)
    "r23": (0.6, 0.8),      # радиусы перехода плоской вершины, доли T0 (п. 5)
    "lead1": (10.0, 20.0),  # передний угол первого ролика, град (п. 4)
    "trail1": (15.0, 25.0),  # задний угол первого ролика, град (п. 4)
    "leadn": (25.0, 35.0),  # передний угол последующих, град (п. 4)
    "trailn": (10.0, 15.0),  # задний угол последующих, град (п. 4)
    "str_b": (4.0, 6.0),    # плоская вершина при правке, доли T (п. 9)
    "str_r": (1.1, 1.5),    # радиусы при правке, доли T (п. 11)
    "str_lead": (25.0, 35.0),  # передний угол при правке, град (п. 10)
    "str_trail": (15.0, 25.0),  # задний угол при правке и обжиме, град (п. 10)
    "neck_b": (0.2, 0.6),   # плоская вершина при обжиме, доли T_обж (п. 9)
    "neck_r": (0.5, 1.0),   # радиусы при обжиме, доли T_обж (п. 11)
    "neck_lead": (12.0, 20.0),  # передний угол при обжиме, град (п. 10)
    "sigma_k": 1.15,        # σ_ср = k·σт (оценка по Зибелю; калибруется)
    "feed_k": 0.5,          # осевое смещение роликов ≤ подачи на оборот (п. 4): 0.5·T0, мм/об
}


def mid(rng):
    """Середина диапазона — рекомендуемое значение по умолчанию."""
    return 0.5 * (rng[0] + rng[1])


def passes(t0, t_end, n=2, sup=None):
    """Деление деформации по переходам (п. 2): рост степени в 1.1…1.5 раза за переход.

    Деформация взята логарифмической (e = ln(t_вх/t_вых)) — она складывается по переходам.
    Показатель роста m подбирается так, чтобы e_(i+1)/e_i = m лежал в k_pass.
    """
    s = sup or SUP
    if not (0 < t_end < t0):
        raise ValueError(f"толщина: t_end {t_end} должна быть меньше t0 {t0}")
    m = math.sqrt(s["k_pass"][0] * s["k_pass"][1])       # середина диапазона роста
    w = [m ** i for i in range(n)]
    e_tot = math.log(t0 / t_end)
    out, t_in = [], t0
    for i, wi in enumerate(w):
        e_i = e_tot * wi / sum(w)
        t_out = t_in / math.exp(e_i)
        out.append({"pass": i + 1, "t_in": round(t_in, 4), "t_out": round(t_out, 4),
                    "eps": round((t_in - t_out) / t_in, 4),
                    "e_log": round(e_i, 4),
                    "grow": round(e_i / (e_tot * w[i - 1] / sum(w)), 3) if i else None})
        t_in = t_out
    out[-1]["t_out"] = t_end
    return out


def rollers(t0, sup=None):
    """Профили роликов и углы в долях T0 (п. 4–8). Возвращает рекомендуемые значения."""
    s = sup or SUP
    return {
        "n": s["n_roll"],
        "r1_mm": round(mid(s["r1"]) * t0, 3),
        "b_lat_mm": round(mid(s["b_lat"]) * t0, 3),
        "gamma_deg": mid(s["gamma"]),
        "r23_mm": round(mid(s["r23"]) * t0, 3),
        "lead1_deg": mid(s["lead1"]), "trail1_deg": mid(s["trail1"]),
        "leadn_deg": mid(s["leadn"]), "trailn_deg": mid(s["trailn"]),
        "feed_per_rev": round(s["feed_k"] * t0, 3),
        "cyl_min_mm": round(s["cyl_min"] * t0, 3),
        "cone_deg": mid(s["cone_deg"]),
    }


def straighten(t, sup=None):
    """Ролики правки (п. 9, 10, 11): плоская вершина 4…6·T, углы 25…35 / 15…25, радиусы 1.1…1.5·T."""
    s = sup or SUP
    return {"b_mm": round(mid(s["str_b"]) * t, 3), "lead_deg": mid(s["str_lead"]),
            "trail_deg": mid(s["str_trail"]), "r_mm": round(mid(s["str_r"]) * t, 3)}


def neck(t, sup=None):
    """Ролики обжима (п. 9, 10, 11): плоская вершина 0.2…0.6·T_обж, углы 12…20 / 15…25."""
    s = sup or SUP
    return {"b_mm": round(mid(s["neck_b"]) * t, 3), "lead_deg": mid(s["neck_lead"]),
            "trail_deg": mid(s["str_trail"]), "r_mm": round(mid(s["neck_r"]) * t, 3)}


def force(sigma_t, b_mm, r_mm, dh_mm, sup=None):
    """Оценка усилия ролика, Н: F = σ_ср·b·√(R·Δh) (Зибель). σ в МПа, размеры в мм → Н."""
    s = sup or SUP
    if min(b_mm, r_mm, dh_mm) <= 0:
        raise ValueError("force: b, R, Δh должны быть > 0")
    return round(s["sigma_k"] * sigma_t * b_mm * math.sqrt(r_mm * dh_mm), 0)


def plan(d0, t0, t_end, sigma_t, n=2, rpm=120, sup=None):
    """План раскатки: переходы, ролики, подача, оценка усилия и времени цикла."""
    s = sup or SUP
    ps = passes(t0, t_end, n, s)
    ro = rollers(t0, s)
    dh = (ps[0]["t_in"] - ps[0]["t_out"]) / s["n_roll"]    # съём на ролик на первом переходе
    f = force(sigma_t, mid(s["b_lat"]) * t0, mid(s["r1"]) * t0, dh, s)
    feed = ro["feed_per_rev"] * rpm                          # мм/мин: смещение ≤ подачи на оборот
    return {
        "d0": d0, "t0": t0, "t_end": t_end, "n_pass": n, "rpm": rpm,
        "passes": ps, "rollers": ro,
        "force_N": f, "force_kN": round(f / 1e3, 1),
        "feed_mm_min": round(feed, 1),
        "mandrel_od": round(d0 - 2 * t0, 2),            # оправка: Ø по внутреннему
        "mandrel_len_min": round(d0 * 0.5, 1),           # рабочая длина (оценка ≥ 0.5·D0)
        "time_min_per_100mm": round(1e5 / feed, 1) if feed else None,
    }


def self_test():
    # 1. деление деформации: рост в 1.1…1.5, толщина монотонно падает (п. 2)
    ps = passes(9.0, 1.2, 3)
    assert abs(ps[-1]["t_out"] - 1.2) < 1e-9, ps
    for a, b in zip(ps, ps[1:]):
        assert 1.1 - 1e-9 <= b["grow"] <= 1.5 + 1e-9, (a, b)
        assert b["t_in"] < a["t_in"], ps
    assert passes(4.0, 2.0, 1)[0]["eps"] == 0.5
    # 2. профили роликов внутри границ формулы (п. 4–8)
    t0, ro = 9.0, rollers(9.0)
    assert abs(ro["r1_mm"] - 0.7 * t0) < 1e-6 and abs(ro["b_lat_mm"] - 0.4 * t0) < 1e-6, ro
    assert ro["lead1_deg"] == 15.0 and ro["trail1_deg"] == 20.0 and ro["leadn_deg"] == 30.0, ro
    assert ro["feed_per_rev"] <= t0, ro        # п. 4: смещение ≤ подачи на оборот
    assert ro["cyl_min_mm"] >= 1.0 * t0 - 1e-9, ro
    assert 4.0 <= straighten(1.2)["b_mm"] / 1.2 <= 6.0
    assert 0.2 <= neck(2.0)["b_mm"] / 2.0 <= 0.6
    # 3. усилие растёт с обжатием, но не с толщиной напрямую
    assert force(930, 3.6, 6.0, 0.8) < force(930, 3.6, 6.0, 3.2)
    assert force(930, 3.6, 6.0, 0.8) > 0
    # 4. план для заготовки стакана: оправка внутри заготовки
    p = plan(d0=95.0, t0=9.0, t_end=1.2, sigma_t=930.0, n=3)
    assert 0 < p["mandrel_od"] < p["d0"], p
    assert p["force_kN"] > 0 and p["feed_mm_min"] > 0
    try:
        passes(1.0, 2.0)
        raise AssertionError("passes: обратный ход не пойман")
    except ValueError:
        pass
    return True


if __name__ == "__main__":
    import json
    print(json.dumps(plan(95.0, 9.0, 1.2, 930.0, 3), ensure_ascii=False, indent=1))
