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


def pair_limits(D, l, kind, Dg, B, lim):
    """Допускаемые силы на теле, Н: (F_г — тело/наружное кольцо подшипника, F_в — тело/венец).
    Венец — плоскость (запас: во впадине профиль вогнутый); ролик на кольце — длина min(l, B)."""
    Es = e_star(lim.E_mod, lim.nu)
    if kind == "ball":
        s = lim.sigma_H_point
        return (f_point(s, _k(D / 2, Dg / 2), _k(D / 2), Es),
                f_point(s, _k(D / 2), _k(D / 2), Es))
    s = lim.sigma_H_line
    return (f_line(s, min(l, B), D / 2, Dg / 2, Es), f_line(s, l, D / 2, math.inf, Es))


def torque(n, z, a, R, D, l, kind, brg, lim, rows):
    """Допускаемый момент пакета рядов, Н·м (Д-41): M_H — по Герцу, M_B — по C0 подшипника.

    Тело в фазе φ_i от направления эксцентрика нагружено при 0 < φ_i < π: R_i = R_max·sin φ_i.
    Выход: M_р = Σ R_i·(R_о/R)_i·Y_i; подшипник: R_max·|Σ sin φ_i·e_i| ≤ C0/s0_brg.
    Худшее из K_PHASE положений генератора внутри шага тел.
    brg = None — тела на эксцентрике (Д-42): пара тело/эксцентрик на всей длине l, M_B нет."""
    Fg, Fv = pair_limits(D, l, kind, 2 * R - D, brg["B"] if brg else l, lim)
    MH = MB = math.inf
    for j in range(K_PHASE):
        s_max = srv = mom = bx = by = 0.0
        for i in range(n):
            p = (2 * math.pi * (i + j / K_PHASE) / n) % (2 * math.pi)
            if not 1e-9 < p < math.pi - 1e-9:
                continue
            s = math.sin(p)
            ro, rv = ptk_profile.contact_ratios(p, a, R, z)
            y = ptk_profile.Y(p, a, R)
            s_max, srv = max(s_max, s), max(srv, s * rv)
            mom += s * ro * y
            bx += s * (y * math.cos(p) - a) / R
            by += s * y * math.sin(p) / R
        if mom <= 0:
            continue
        MH = min(MH, min(Fg / s_max, Fv / srv) * mom / 1000)
        if brg:
            MB = min(MB, brg["C0"] * 1000 / (lim.s0_brg * math.hypot(bx, by)) * mom / 1000)
    if math.isinf(MH):
        MH = MB = 0.0
    return {"M_H": round(rows * MH, 1), "M_B": round(rows * MB, 1) if brg else None,
            "F_g": round(Fg, 1), "F_v": round(Fv, 1)}


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

$R_\text{max}$ = min($F_\text{г}$ / max sin φ, $F_\text{в}$ / max(sin φ · $R_\text{в}/R$)) → $M_H$;
подшипник $R_\text{max} \lvert \sum \sin\varphi_i \vec e_i \rvert \le C_0 / s_0$ → $M_B$.
M = min($M_H$, $M_B$, M крепл. / safety), в скобках — что ограничивает.
Генератор `eccentric` (Д-42): тела катятся прямо по эксцентрику, $D_\text{г}$ — его наружный
диаметр (вверх до `dgen_step`, не меньше `shaft_d_min` + 2($a_\omega$ + `ecc_wall_min`)); пара
тело/эксцентрик на всей длине тела, $M_B$ нет. В (12) $\omega_\text{к} = -\omega$ задана
кинематически (кольцо — сам эксцентрик), а не из равновесия кольца: скольжение в $K_\text{г}$
порядка $\omega D_\text{г}/2$, потери и износ выше, чем с подшипником (OQ-10).
Не учтены: трение (11), (12), ресурс подшипника, контакт тело/паз сепаратора (OQ-08, CP-32)."""


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
                          sigma_H_point=3000.0, s0_brg=1.0)
    brg = {"d": 45.0, "D": 58.0, "B": 7.0, "C": 6.63, "C0": 6.1}
    t1 = torque(19, z, a, R, D, 8.0, "roller", brg, lim, 4)
    assert t1["M_H"] > 0 and t1["M_B"] > 0, t1
    t2 = torque(19, z, a, R, D, 8.0, "roller", brg,
                SimpleNamespace(**{**vars(lim), "sigma_H_line": 5000.0}), 4)
    assert abs(t2["M_H"] - 4 * t1["M_H"]) < 0.01 * t2["M_H"] and t2["M_B"] == t1["M_B"]
    t4 = torque(19, z, a, R, D, 8.0, "roller", brg, lim, 1)
    assert abs(4 * t4["M_H"] - t1["M_H"]) < 0.5
    assert torque(19, z, a, R, D, 5.0, "ball", brg, lim, 4)["M_H"] < t1["M_H"]
    t5 = torque(19, z, a, R, D, 8.0, "roller", None, lim, 4)         # Д-42: эксцентрик
    assert t5["M_B"] is None and t5["M_H"] >= t1["M_H"], (t5, t1)
    return True
