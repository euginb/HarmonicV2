"""Силовой расчёт ПТК (CP-30, Д-40, Д-41): нагрузка тел ряда, контакт Герца,
статическая проверка подшипника генератора, допускаемый выходной момент.

Схема (OQ-07): эксцентрик → подшипник .08 (внутреннее кольцо на эксцентрике) →
наружное кольцо, D_г = D подшипника → тела качения → венец; тела ведут сепаратор (выход).
Реакции — (8), (9) Янгулова без трения; трение (11), износ, ресурс подшипника — OQ-08.
"""
import math
from types import SimpleNamespace

from egm import ptk_profile

K_PHASE = 8        # положений генератора внутри шага тел; берётся худшее


def e_star(E, nu):
    """Приведённый модуль двух тел из одного материала: 1/E* = 2(1 − ν²)/E, МПа."""
    return E / (2 * (1 - nu * nu))


def _k(*r):
    """Сумма кривизн 1/r, 1/мм; inf — плоскость, r < 0 — вогнутая поверхность."""
    return sum(0.0 if math.isinf(x) else 1.0 / x for x in r)


def f_line(sigma, l, r1, r2, Es):
    """Линейный контакт (ролик): σ_H = √(F·E*·k/(π·l)), k = 1/r1 + 1/r2 -> F при σ_H = sigma, Н."""
    return sigma ** 2 * math.pi * l / (Es * _k(r1, r2))


def sigma_line(F, l, r1, r2, Es):
    return math.sqrt(F * Es * _k(r1, r2) / (math.pi * l))


def f_point(sigma, kx, ky, Es):
    """Точечный контакт (шарик), круговое приближение R_e² = 1/(kx·ky):
    σ_H = (6F·E*²/(π³·R_e²))^(1/3) -> F при σ_H = sigma, Н."""
    return sigma ** 3 * math.pi ** 3 / (6 * Es ** 2 * kx * ky)


def sigma_point(F, kx, ky, Es):
    return (6 * F * Es ** 2 * kx * ky / math.pi ** 3) ** (1 / 3)


def pair_limits(D, l, kind, Dg, B, lim, groove=False):
    """Допускаемые силы на теле, Н: (F_г — тело/наружное кольцо подшипника, F_в — тело/венец).
    Венец — плоскость (запас: во впадине профиль вогнутый); ролик на кольце — длина min(l, B).
    groove — шарик в жёлобе эксцентрика r = groove_f·D (Д-45, Т2)."""
    Es = e_star(lim.E_mod, lim.nu)
    if kind == "ball":
        s = lim.sigma_H_point
        ky = _k(D / 2, -lim.groove_f * D) if groove else _k(D / 2)
        return (f_point(s, _k(D / 2, Dg / 2), ky, Es),
                f_point(s, _k(D / 2), _k(D / 2), Es))
    s = lim.sigma_H_line
    return (f_line(s, min(l, B), D / 2, Dg / 2, Es), f_line(s, l, D / 2, math.inf, Es))


def torque(n, z, a, R, D, l, kind, brg, lim, rows):
    """Допускаемый момент пакета рядов, Н·м (Д-41): M_H — по Герцу, M_B — по C0 подшипника.

    Тело в фазе φ_i от направления эксцентрика нагружено при 0 < φ_i < π: R_i = R_max·sin φ_i.
    Выход: M_р = Σ R_i·(R_о/R)_i·Y_i; подшипник: R_max·|Σ sin φ_i·e_i| ≤ C0/s0_brg.
    Худшее из K_PHASE положений генератора внутри шага тел.
    brg = None — тела на эксцентрике (Д-42): пара тело/эксцентрик на всей длине l, M_B нет."""
    Fg, Fv = pair_limits(D, l, kind, 2 * R - D, brg["B"] if brg else l, lim,
                         kind == "ball" and brg is None)
    MG = MV = MB = math.inf        # CP-98: M_H = min(MG — тело/генератор, MV — тело/венец)
    k_sep = 0.0                    # CP-94: max сила тела на окно / M ряда, 1/мм
    for j in range(K_PHASE):
        s_max = srv = mom = bx = by = so = 0.0
        for i in range(n):
            p = (2 * math.pi * (i + j / K_PHASE) / n) % (2 * math.pi)
            if not 1e-9 < p < math.pi - 1e-9:
                continue
            s = math.sin(p)
            ro, rv = ptk_profile.contact_ratios(p, a, R, z)
            y = ptk_profile.Y(p, a, R)
            s_max, srv = max(s_max, s), max(srv, s * rv)
            so = max(so, s * ro)
            mom += s * ro * y
            bx += s * (y * math.cos(p) - a) / R
            by += s * y * math.sin(p) / R
        if mom <= 0:
            continue
        k_sep = max(k_sep, so / mom)
        MG = min(MG, Fg / s_max * mom / 1000)
        MV = min(MV, Fv / srv * mom / 1000)
        if brg:
            MB = min(MB, brg["C0"] * 1000 / (lim.s0_brg * math.hypot(bx, by)) * mom / 1000)
    MH = min(MG, MV)
    if math.isinf(MH):
        MH = MG = MV = MB = 0.0
    return {"M_H": round(rows * MH, 1), "M_B": round(rows * MB, 1) if brg else None,
            "M_g": round(rows * MG, 1), "M_v": round(rows * MV, 1),
            "F_g": round(Fg, 1), "F_v": round(Fv, 1), "k_sep": k_sep}


def _strip(sep):
    """CP-95b: ширина сплошной полосы стенки через окна всех рядов, мм. Окна ряда k — угловые
    интервалы [cage_k, cage_k + w/r_in] в шаге 360/n; полоса — наибольший непокрытый промежуток
    на r_in. 0 — окна рядов перекрывают шаг (K20), полосы нет."""
    P = 360.0 / sep["n"]
    w_win = sep.get("w") or 2 * sep["r_in"] * math.sin(math.pi / sep["n"]) - sep["web"]
    ww = math.degrees(w_win / sep["r_in"])
    st = sorted({round(w_["cage"] % P, 6) for w_ in sep.get("rows", [])})
    if ww >= P or not st:
        return 0.0
    gap = max((st[i + 1] if i + 1 < len(st) else st[0] + P) - a0 - ww for i, a0 in enumerate(st))
    return round(max(gap, 0.0) * math.pi / 180 * sep["r_in"], 3)


def _sep(M, sep, k_sep, D, l, kind, rows, R, lim):
    """Сепаратор при моменте пакета M, Н·м (CP-94, CP-98; Д-116, Д-118) — без округления.

    Ряды j = 1…rows — от выходного торца. Рама Виренделя по окружности периодична: точки
    перегиба — в серединах перемычек и участков поясов. Перемычка ряда j несёт сдвиг
    V_j = q·(rows − j + ½), q = M_ряд/(n·R_Σ) — момент дальних рядов и половина своего,
    у торца перемычки V_j·L/2; свой ряд — тело давит на сторону окна силой F = k_sep·M_ряд,
    балка с заделкой F·L/12 — у того же торца. Перемычка: σ = (V_1·L/2 + F·L/12)/W, W = t·b²/6.
    Пояс между рядами j, j+1 (CP-98): узел уравновешивает две перемычки, на пояс
    M_п = (V_j + V_j+1)·L/4 + F·L/12, W_п = t_п·h_п²/6, срез τ = 3·M_п/(s·t_п·h_п), s = 2πR_Σ/n;
    пояс у выходного торца — M_т = (V_1·L/2 + F·L/12)/2, h_т. Нет sep["band"] — пояса не
    проверяются (как CP-94). Жёсткость поясов на σ перемычки не влияет (периодичность): усиление
    пояса поднимает M_sep, только если лимитирует пояс. Контакт — Герц тело/плоскость на
    min(l, L), × sep_k_edge. u_b, u_H — загрузка в долях момента: M_sep = M/max(u_b, u_H)."""
    n, L, b = sep["n"], sep["h"], sep["web"]
    W = (sep["r_out"] - sep["r_in"]) * b * b / 6
    Mr = M * 1000 / rows                                  # момент ряда, Н·мм
    q = Mr / (n * R)
    V = [q * (rows - j + 0.5) for j in range(1, rows + 1)]
    F = k_sep * Mr
    m_r = F * L / 12
    Es = e_star(lim.E_mod, lim.nu)
    if kind == "ball":                                    # шарик/плоскость: σ ∝ F^(1/3)
        sH, p = sigma_point(F, _k(D / 2), _k(D / 2), Es), 3
    else:                                                 # ролик/плоскость: σ ∝ F^(1/2)
        sH, p = sigma_line(F, min(l, L), D / 2, math.inf, Es), 2
    sH *= lim.sep_k_edge
    s_fr, s_row = V[0] * L / 2 / W, m_r / W
    allow = lim.sep_sigma_m1 / (lim.sep_K * lim.sep_S)
    el = [(s_fr + s_row, "перемычка", 1)]
    s_bd = s_end = tau = 0.0
    bd = sep.get("band")
    # CP-95b: узлы рамы — жёсткие зоны шириной перемычки; пояс гнётся на пролёте окна w из шага 2πR/n
    w_win = sep.get("w") or 2 * sep["r_in"] * math.sin(math.pi / n) - sep["web"]
    k_off = min(1.0, w_win * n / (2 * math.pi * R))
    if bd:                                                # CP-98: пояса
        tb = bd["t"]
        if rows > 1 and bd.get("h_mid"):
            mb = [(V[j] + V[j + 1]) * L / 4 + m_r for j in range(rows - 1)]
            j = max(range(rows - 1), key=mb.__getitem__)
            s_bd = 6 * k_off * mb[j] / (tb * bd["h_mid"] ** 2)
            tau = 3 * mb[j] / (2 * math.pi * R / n) / (tb * bd["h_mid"])
            el.append((s_bd, "пояс", j + 1))
        s_end = 6 * k_off * (V[0] * L / 2 + m_r) / 2 / (tb * bd["h_end"] ** 2)
        el.append((s_end, "торец", 0))
    s_max, elem, j_lim = max(el)
    u_fr = max(s_max / allow, tau / (0.58 * allow))
    # CP-95b: вторая схема — сплошная полоса b_c через окна всех рядов, консоль от выходного торца,
    # пояса не нагружены; рама и полоса — два статически допустимых поля, берётся меньшая загрузка
    b_c, s_st = _strip(sep), 0.0
    if b_c > 0:
        arm = [w_["z0"] + L / 2 - sep["rows"][0]["z0"] for w_ in sep["rows"]]
        m_st = q * sum(arm) + max(F - q, 0.0) * max(arm)
        s_st = 6 * m_st / ((sep["r_out"] - sep["r_in"]) * b_c ** 2)
    u_st = s_st / allow if b_c > 0 else math.inf
    if u_st < u_fr:
        elem, j_lim = "полоса", 0
    return {"V": V[0], "F": F, "sig_frame": s_fr, "sig_row": s_row, "sig_b": s_fr + s_row,
            "sig_band": s_bd, "sig_end": s_end, "tau_band": tau, "sig_strip": s_st, "b_strip": b_c,
            "sig_allow": allow, "sig_H": sH, "sigH_allow": lim.sep_sigma_H,
            "u_b": min(u_fr, u_st), "u_H": (sH / lim.sep_sigma_H) ** p,
            "lim_elem": elem, "n_row_lim": j_lim}


def sep_check(M, sep, k_sep, D, l, kind, rows, R, a, lim):
    """Проверка сепаратора при принятом M, Н·м -> ptk_configs.yaml → sep_chk (CP-94).
    edge — запас от линии контакта до кромки стенки при крайнем ходе тела (SEP_K − 1)·a_ω;
    b_H — полуширина площадки Герца ролика: при b_H ~ edge контакт кромочный (sep_k_edge)."""
    c = _sep(M, sep, k_sep, D, l, kind, rows, R, lim)
    c["by"] = "изгиб" if c["u_b"] >= c["u_H"] else "контакт"
    c["edge"] = (sep["r_out"] - sep["r_in"]) / 2 - a
    c["b_H"] = (math.sqrt(4 * c["F"] * D / 2 / (math.pi * min(l, sep["h"])
                                               * e_star(lim.E_mod, lim.nu)))
                if kind != "ball" else 0.0)
    return {k: round(v, 4) if isinstance(v, float) else v for k, v in c.items()}


def sep_limit(sep, k_sep, D, l, kind, rows, R, a, lim):
    """M_sep, Н·м (вниз до 0.1), и причина: наименьший M, при котором σ перемычки = [σ]
    или k_edge·σ_H = [σ_H] (CP-94, Д-116). a — для единой сигнатуры с sep_check."""
    c = _sep(1.0, sep, k_sep, D, l, kind, rows, R, lim)
    u = max(c["u_b"], c["u_H"])
    if u <= 0:
        return 0.0, "сепаратор не нагружен (k_sep = 0) — проверка не выполнена"
    M = math.floor(10 / u) / 10
    s = _sep(M, sep, k_sep, D, l, kind, rows, R, lim)
    if c["u_b"] >= c["u_H"] and c["lim_elem"] == "полоса":       # CP-95b
        why = (f"изгиб сплошной полосы через окна всех рядов (консоль от выходного торца), "
               f"ширина {s['b_strip']:.1f} мм: σ {s['sig_strip']:.0f} МПа = [σ] "
               f"{s['sig_allow']:.1f} МПа; пояса не догружены (CP-95b)")
    elif c["u_b"] >= c["u_H"] and c["lim_elem"] == "перемычка":
        why = (f"изгиб перемычки ряда у выходного торца: σ рамы {s['sig_frame']:.0f} + σ ряда "
               f"{s['sig_row']:.0f} МПа = [σ] = σ₋₁/(K·S) = {lim.sep_sigma_m1:g}/"
               f"({lim.sep_K:g}·{lim.sep_S:g}) = {s['sig_allow']:.1f} МПа (CP-94)")
    elif c["u_b"] >= c["u_H"]:                            # CP-98: лимитирует пояс
        bd, mid = sep["band"], c["lim_elem"] == "пояс"
        where = (f"пояс между рядами {c['n_row_lim']}–{c['n_row_lim'] + 1} от выходного торца"
                 if mid else "пояс у выходного торца")
        why = (f"изгиб: {where}, {bd['h_mid'] if mid else bd['h_end']:g} × {bd['t']:g} мм: "
               f"σ {s['sig_band'] if mid else s['sig_end']:.0f} МПа = [σ] {s['sig_allow']:.1f} МПа; "
               f"усилить пояс (sep_band_t) или поднять row_gap (CP-98, OQ-46)")
    else:
        why = (f"контакт тело/окно: k_edge·σ_H = {s['sig_H']:.0f} МПа = [σ_H] "
               f"{lim.sep_sigma_H:g} МПа при F {s['F']:.0f} Н (CP-94)")
    return M, why


def sep_refs(sep, k_sep, D, l, kind, rows, R, a, lim):
    """Референсы сепаратора, Н·м (CP-98, Д-118), вниз до 0.1:
    M_row_b — один ряд, только изгиб перемычки своим рядом (без переноса через дальние ряды);
    M_row_H — один ряд по контакту тело/окно; M_row = min(M_row_b, M_row_H);
    M_win — пакет по контакту тело/окно (= rows·M_row_H) — предел тела в окне, M_body_win."""
    c = _sep(1.0, sep, k_sep, D, l, kind, rows, R, lim)
    Mb = c["sig_allow"] / (rows * c["sig_row"]) if c["sig_row"] > 0 else 0.0
    Mw = 1 / c["u_H"] if c["u_H"] > 0 else 0.0
    f = lambda x: math.floor(10 * x) / 10
    return {"M_row": f(min(Mb, Mw / rows)), "M_row_b": f(Mb), "M_row_H": f(Mw / rows),
            "M_win": f(Mw)}


def theory_md():
    return r"""### Силовой расчёт (Д-40, Д-41)

Схема: эксцентрик → подшипник генератора (внутреннее кольцо на эксцентрике) → наружное
кольцо, $D_\text{г}$ = D подшипника → тела → венец; тела ведут сепаратор (выход).

Тело ряда в фазе $\varphi_i$ от направления эксцентрика нагружено при $0 < \varphi_i < \pi$:
$R_i = R_\text{max} \sin\varphi_i$. Реакции по (8), (9) без трения:
$R_\text{о} / R = \sin(\alpha - \psi) / \cos\alpha = u\, a_\omega \sin\varphi / R_\Sigma$,
$R_\text{в} / R = \cos\psi / \cos\alpha$.
Момент ряда $M_\text{р} = R_\text{max} \sum \sin\varphi_i (R_\text{о}/R)_i Y_i$, пакета —
rows · $M_\text{р}$; берётся худшее из 8 положений генератора внутри шага тел.

Контакт Герца, $1/E^* = 2(1 - \nu^2)/E$:
ролик — $\sigma_H = \sqrt{F E^* k / (\pi l)}$; шарик — $\sigma_H = (6 F E^{*2} k_x k_y / \pi^3)^{1/3}$.
Кривизны: тело/наружное кольцо $k = 2/D_\text{ш} + 2/D_\text{г}$ (ролик — на длине
min(l, B подш.)), тело/венец $k = 2/D_\text{ш}$ (венец как плоскость — запас).
Шарик на эксцентрике (Д-45, Т2): жёлоб $r = f D_\text{ш}$, $f$ = `groove_f`,
$k_y = 2/D_\text{ш} - 1/(f D_\text{ш})$; шарик на подшипнике исключён (Т1), венец без жёлоба (Т3).

$R_\text{max}$ = min($F_\text{г}$ / max sin φ, $F_\text{в}$ / max(sin φ · $R_\text{в}/R$)) → $M_H$;
подшипник $R_\text{max} \lvert \sum \sin\varphi_i \vec e_i \rvert \le C_0 / s_0$ → $M_B$.
M = min($M_H$, $M_B$, M крепл. / safety, $M_\text{sep}$), в скобках — что ограничивает.
Генератор `eccentric` (Д-42): тела катятся прямо по эксцентрику, $D_\text{г}$ — его наружный
диаметр (вверх до `dgen_step`, не меньше `shaft_d_min` + 2($a_\omega$ + `ecc_wall_min`)); пара
тело/эксцентрик на всей длине тела, $M_B$ нет. В (12) $\omega_\text{к} = -\omega$ задана
кинематически (кольцо — сам эксцентрик), а не из равновесия кольца: скольжение в $K_\text{г}$
порядка $\omega D_\text{г}/2$, потери и износ выше, чем с подшипником (OQ-10).
Сепаратор (CP-94, Д-116): $M_\text{sep}$ — наименьший M, при котором перемычка ряда у выходного
торца достигает $[\sigma] = \sigma_{-1}/(K S)$ (`sep_sigma_m1`, `sep_K`, `sep_S`; многоцикловая
усталость — нагружение на каждый оборот входа) или контакт тело/сторона окна — `sep_sigma_H`.
Перемычка b × t ($t = 2.2 a_\omega$), высота окна L. Рама Виренделя:
$V = M (rows - 1/2)/(rows\, n R_\Sigma)$, $M_\text{изг} = V L/2$; свой ряд — $F = k_\text{sep} M/rows$,
$k_\text{sep}$ = max(sin φ · $R_\text{о}/R$) / Σ sin φ ($R_\text{о}/R$) Y, балка с заделкой $F L/12$;
$\sigma = (V L/2 + F L/12)/W$, $W = t b^2/6$. Контакт — Герц тело/плоскость на длине min(l, L),
× `sep_k_edge`: тело доходит до кромки стенки (запас $(1.1 - 1) a_\omega$). K, S, k_edge, [σ_H] — OQ-44.

Пояса сепаратора (CP-98, Д-118): кольца между окнами соседних рядов (высота $h_п$) и у торцов
($h_т$), радиальная толщина $t_п$ = `sep_band_t` (0 — стенка t; утолщение наружу в зоне шайб .05
до $d_\text{вн}/2$ − `sep_band_gap`). Рама периодична по окружности, перегибы в серединах
элементов: $M_п = (V_j + V_{j+1}) L/4 + F L/12$, $\sigma_п = 6 M_п/(t_п h_п^2)$,
$\tau_п = 3 M_п/(s\, t_п h_п)$, $s = 2\pi R_\Sigma/n$; у выходного торца $M_т = (V_1 L/2 + F L/12)/2$.
Жёсткость пояса на σ перемычки не влияет; потолок рамы $M \approx 2 n R_\Sigma W [\sigma]/L$ не
зависит от числа рядов. Референс $M_\text{row}$ — один ряд по изгибу своим рядом и контакту в окне;
$M_\text{pack}$ = $M_\text{sep}$; η = $M_\text{pack}/(rows\, M_\text{row})$ — доля, оставшаяся после переноса.
Пределы тела (CP-98): $M_\text{body,gen}$, $M_\text{body,ring}$ — по $F_\text{г}$, $F_\text{в}$
($M_H$ = min из них), $M_\text{body,win}$ — по контакту в окне; `M_by_body` — первый.
Не учтены: трение (11), (12), ресурс подшипника, сдвиг окон соседних рядов по углу (перемычки
рядов не соосны — пояс между ними работает и на сдвиг; OQ-08, OQ-44, OQ-46)."""


def self_test():
    Es = e_star(210000.0, 0.3)
    assert abs(Es - 115384.6) < 0.1, Es
    s = sigma_line(1000.0, 10.0, 5.0, math.inf, Es)           # ролик R5 × 10 мм на плоскости
    assert 850.0 < s < 865.0, s
    assert abs(f_line(s, 10.0, 5.0, math.inf, Es) - 1000.0) < 1e-6
    s = sigma_point(1000.0, 0.1, 0.1, Es)                     # шар R10 на плоскости
    assert 2900.0 < s < 3000.0, s
    assert abs(f_point(s, 0.1, 0.1, Es) - 1000.0) < 1e-6
    a, D, z = 1.0, 5.0, 20
    R = (58.0 + D) / 2
    for p in (0.3, 1.0, 2.0):                                 # без трения: M вых = u·M вх
        ro, _ = ptk_profile.contact_ratios(p, a, R, z)
        assert abs(ro - (z - 1) * a * math.sin(p) / R) < 1e-9, (p, ro)
    lim = SimpleNamespace(E_mod=210000.0, nu=0.3, sigma_H_line=2500.0,
                          sigma_H_point=3000.0, s0_brg=1.0, groove_f=0.52)
    g0 = pair_limits(2.0, 2.0, "ball", 60.0, 2.0, lim)                    # Д-45: жёлоб
    g1 = pair_limits(2.0, 2.0, "ball", 60.0, 2.0, lim, True)
    assert g1[0] > 10 * g0[0] and g1[1] == g0[1], (g0, g1)
    brg = {"d": 45.0, "D": 58.0, "B": 7.0, "C": 6.63, "C0": 6.1}
    t1 = torque(19, z, a, R, D, 8.0, "roller", brg, lim, 4)
    assert t1["M_H"] > 0 and t1["M_B"] > 0, t1
    assert t1["M_H"] == min(t1["M_g"], t1["M_v"]) and t1["M_g"] > 0 and t1["M_v"] > 0, t1  # CP-98
    t2 = torque(19, z, a, R, D, 8.0, "roller", brg,
                SimpleNamespace(**{**vars(lim), "sigma_H_line": 5000.0}), 4)
    assert abs(t2["M_H"] - 4 * t1["M_H"]) < 0.01 * t2["M_H"] and t2["M_B"] == t1["M_B"]
    t4 = torque(19, z, a, R, D, 8.0, "roller", brg, lim, 1)
    assert abs(4 * t4["M_H"] - t1["M_H"]) < 0.5
    assert torque(19, z, a, R, D, 5.0, "ball", brg, lim, 4)["M_H"] < t1["M_H"]
    t5 = torque(19, z, a, R, D, 8.0, "roller", None, lim, 4)         # Д-42: эксцентрик
    assert t5["M_B"] is None and t5["M_H"] >= t1["M_H"], (t5, t1)
    lim2 = SimpleNamespace(**vars(lim), sep_sigma_m1=509.0, sep_K=2.0, sep_S=2.5,  # CP-94
                           sep_sigma_H=880.0, sep_k_edge=1.2)
    sep = {"n": 19, "r_in": R - 1.1 * a, "r_out": R + 1.1 * a, "h": 8.05,
           "web": 2 * (R - 1.1 * a) * math.sin(math.pi / 19) - 5.05}
    k = t1["k_sep"]
    assert 0 < k < 5.5 / (19 * R), k                      # ≈ 4/(n·R_Σ): Σ sin²φ ≈ n/4
    Ms, why = sep_limit(sep, k, D, 8.0, "roller", 4, R, a, lim2)
    c1 = sep_check(Ms, sep, k, D, 8.0, "roller", 4, R, a, lim2)
    assert Ms > 0 and 0.98 < max(c1["u_b"], c1["u_H"]) <= 1.0 + 1e-3, (Ms, c1)
    c2 = sep_check(2 * Ms, sep, k, D, 8.0, "roller", 4, R, a, lim2)
    assert abs(c2["sig_b"] - 2 * c1["sig_b"]) < 0.01, (c1, c2)               # изгиб ∝ M
    assert abs(c2["sig_H"] - 2 ** 0.5 * c1["sig_H"]) < 0.1, (c1, c2)        # Герц ∝ √M
    assert sep_limit({**sep, "web": 1.5 * sep["web"]}, k, D, 8.0, "roller", 4, R, a, lim2)[0] > Ms
    assert sep_limit(sep, k, D, 8.0, "roller", 4, R, a,
                     SimpleNamespace(**{**vars(lim2), "sep_K": 4.0}))[0] < Ms
    # CP-98: пояс 0.95 мм (шаг ряда = l) лимитирует, усиление пояса поднимает M_sep;
    # широкий пояс не лимитирует — M_sep как в CP-94
    wide = {**sep, "band": {"t": 2.2 * a, "h_mid": 6.0, "h_end": 4.0}}
    assert abs(sep_limit(wide, k, D, 8.0, "roller", 4, R, a, lim2)[0] - Ms) < 0.05
    bn = {**sep, "band": {"t": 2.2 * a, "h_mid": 0.95, "h_end": 0.975}}
    Mn = sep_limit(bn, k, D, 8.0, "roller", 4, R, a, lim2)[0]
    Mt = sep_limit({**bn, "band": {**bn["band"], "t": 4.4 * a}}, k, D, 8.0, "roller", 4, R, a,
                   lim2)[0]
    assert 0 < Mn < Ms and 1.5 * Mn < Mt <= Ms + 0.1, (Mn, Mt, Ms)
    cn = sep_check(Mn, bn, k, D, 8.0, "roller", 4, R, a, lim2)
    assert cn["lim_elem"] == "пояс" and cn["n_row_lim"] == 1, cn
    rf = sep_refs(sep, k, D, 8.0, "roller", 4, R, a, lim2)
    assert rf["M_row"] == min(rf["M_row_b"], rf["M_row_H"]) > 0, rf
    assert abs(rf["M_win"] - 4 * rf["M_row_H"]) < 0.5 and rf["M_win"] >= Ms - 0.1, (rf, Ms)
    st = {"n": 10, "w": 8.05, "r_in": 64.09, "rows": [{"cage": c} for c in (0.0, 18.0, 18.0, 0.0)]}
    assert 11.9 < _strip(st) < 12.3, _strip(st)                  # CP-95b: u = 10, окна 0/18°
    assert _strip({"n": 63, "w": 3.05, "r_in": 60.84,
                   "rows": [{"cage": c} for c in (0.0, 4.2857, 2.8571, 1.4286)]}) == 0.0
    return True
