"""Профиль венца ПТК и нагрузки в контактах (Д-37, Д-38).

Методика: Янгулов В.С., «Силовой расчёт ВППТК…» (docs/Силовой расчет ПТК), эталон
профиля — egm/calc_vptc.py. Обозначения: a_w = a_ω — эксцентриситет генератора;
R_sum = R_Σ = 0.5(D_г + D_ш); Drol = D_ш; z — впадин венца (z = u + 1, Д-31);
φ — угол эксцентрика относительно оси тела. Тело на угле t венца: φ = z·t.
Центр тела: Y = a_ω·cos φ + √(R_Σ² − a_ω²·sin²φ)  (6). Профиль — эквидистанта на
D_ш/2; нормаль отклонена от радиуса на α: tg α = z·a_ω·sin φ / √(R_Σ² − a_ω²·sin²φ)
(у Янгулова в числителе u — схема с вращающимся венцом, u = z).
"""
import math
from functools import lru_cache


def S(phi, a_w, R_sum):
    return math.sqrt(R_sum * R_sum - (a_w * math.sin(phi)) ** 2)


def Y(phi, a_w, R_sum):
    """(6): расстояние центра тела от центра венца."""
    return a_w * math.cos(phi) + S(phi, a_w, R_sum)


def alpha(phi, a_w, R_sum, z):
    """Угол передачи движения профилю, рад: tg α = V^R / V^τ."""
    return math.atan2(z * a_w * math.sin(phi), S(phi, a_w, R_sum))


def alpha_max(a_w, R_sum, z):
    """Наибольший α, град (φ = 90°): tg α max = z·a_ω / √(R_Σ² − a_ω²)."""
    return math.degrees(math.atan2(z * a_w, math.sqrt(R_sum ** 2 - a_w ** 2)))


def psi(phi, a_w, R_sum):
    """(4) при номинале: sin ψ = a_ω·sin φ / R_Σ."""
    return math.asin(a_w * math.sin(phi) / R_sum)


def contact_ratios(phi, a_w, R_sum, z):
    """(8), (9) без трения: (R_о/R, R_в/R) — сепаратор и венец на 1 Н реакции генератора."""
    al, ps = alpha(phi, a_w, R_sum, z), psi(phi, a_w, R_sum)
    return abs(math.sin(al - ps)) / math.cos(al), math.cos(ps) / math.cos(al)


def curv_radius_min(a_w, R_sum, z, k=200):
    """Наименьший радиус кривизны траектории центра тела на выступах венца; inf — нет."""
    h, best = 1e-4 / z, math.inf
    for i in range(k + 1):
        t = math.pi / z * i / k                       # полшага: профиль симметричен
        r0, rp, rm = (Y(z * x, a_w, R_sum) for x in (t, t + h, t - h))
        d1, d2 = (rp - rm) / (2 * h), (rp - 2 * r0 + rm) / (h * h)
        num = r0 * r0 + 2 * d1 * d1 - r0 * d2
        if num < 0:
            best = min(best, (r0 * r0 + d1 * d1) ** 1.5 / -num)
    return best


@lru_cache(maxsize=None)
def r_sum_undercut(a_w, rho_req, z):
    """Наименьший R_Σ без подреза: ρк min ≥ rho_req (= D_ш/2 + r_tip_min)."""
    ok = lambda R: curv_radius_min(a_w, R, z) >= rho_req
    lo = hi = 2 * a_w + rho_req
    while not ok(hi):
        lo, hi = hi, hi * 1.5
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if ok(mid) else (mid, hi)
    return hi


def profile_points(a_w, R_sum, Drol, z, k=24):
    """Контур венца: z·k точек против часовой стрелки (как egm/calc_vptc.py)."""
    N, r, pts = z * k, Drol / 2, []
    for i in range(N):
        t = 2 * math.pi * i / N
        phi = z * t
        y, al = Y(phi, a_w, R_sum), alpha(phi, a_w, R_sum, z)
        pts.append((y * math.cos(t) + r * math.cos(t + al),
                    y * math.sin(t) + r * math.sin(t + al)))
    return pts


def theory_md():
    return r"""## Профиль венца и порядок расчёта (Д-38)

Источники: Янгулов В.С. «Силовой расчёт ВППТК» (`docs/Силовой расчет ПТК`), эталон
`egm/calc_vptc.py`. Обозначения — Д-37. Венец неподвижен, вход — генератор, выход —
сепаратор: $z = u + 1$, $n = u$.

| Обозначение | Код | Смысл |
|---|---|---|
| $D_\text{ш}$ | `Drol` | диаметр тела качения |
| $a_\omega$ | `a_w` | эксцентриситет генератора волн |
| $D_\text{г}$ | `Dgen` | диаметр генератора (поверхность качения тел) |
| $R_\Sigma = 0.5(D_\text{г} + D_\text{ш})$ | `R_sum` | радиус центров тел при $a_\omega = 0$ |
| $\varphi$ | — | угол эксцентрика от оси тела |
| $Y$ | — | расстояние центра тела от центра венца |
| $\alpha$ | `alpha_max` | угол передачи движения профилю |
| $\psi$ | — | угол между осью тела и линией центр тела — центр генератора |

1. $a_\omega = a_k D_\text{ш}$ (эталон: 0.2) или `a_w` тела.
2. $R_\Sigma$ — наименьший из трёх условий (поле `R_by`):
   подрез — радиус кривизны траектории на выступе $\rho_\text{к} \ge D_\text{ш}/2 + r_{tip,min}$
   (на вершине $\rho_\text{к} = Y^2/(Y'' - Y)$, $Y'' = a_\omega z^2 (1 - a_\omega/R_\Sigma)$, проверка численно по шагу);
   сепаратор — $2(R_\Sigma - 1.1a_\omega)\sin(\pi/n) - D_\text{ш} \ge$ `sep_web_min` (кольцо $2.2a_\omega$, эталон);
   генератор — $D_\text{г} = 2R_\Sigma - D_\text{ш} \ge$ `Dgen_min`.
3. Траектория центра тела, угол тела $t$, $\varphi = z t$:
   $Y = a_\omega\cos\varphi + \sqrt{R_\Sigma^2 - a_\omega^2\sin^2\varphi}$ (6).
4. Профиль — точка центра, сдвинутая на $D_\text{ш}/2$ по нормали под углом $\alpha$ к радиусу:
   $\operatorname{tg}\alpha = z a_\omega\sin\varphi / \sqrt{R_\Sigma^2 - a_\omega^2\sin^2\varphi}$
   (у Янгулова — $u$: там вращается венец и $u = z$).
5. $D_\text{В} = 2(R_\Sigma + a_\omega) + D_\text{ш}$, $D_\text{верш} = 2(R_\Sigma - a_\omega) + D_\text{ш}$, ход тела в пазу $2a_\omega$.
6. $\operatorname{tg}\alpha_{max} = z a_\omega / \sqrt{R_\Sigma^2 - a_\omega^2}$. Если $R_\Sigma$ задал подрез,
   $\operatorname{tg}\alpha_{max} \approx \sqrt{a_\omega/(D_\text{ш}/2 + r_{tip,min})} \approx \sqrt{2a_k}$ (≈ 32° при 0.2):
   угол — следствие $a_k$, не параметр. Размер: $D_\text{В} \approx z D_\text{ш}\sqrt{2a_k}$.
7. Нагрузки без трения (8), (9): $R_\text{о} = R\sin(\alpha - \psi)/\cos\alpha$, $R_\text{в} = R\cos\psi/\cos\alpha$,
   $\sin\psi = a_\omega\sin\varphi/R_\Sigma$. Равновесие генератора (5), (7), трение (11), скорости (12),
   момент и износ — CP-08."""


def self_test():
    a, D, z = 0.4, 2.0, 33
    R = r_sum_undercut(a, D / 2, z)
    assert 19.0 < R < 22.5, R                                   # ≈ 20.6 по вершине
    assert curv_radius_min(a, R * 1.001, z) >= D / 2
    assert curv_radius_min(a, R * 0.98, z) < D / 2
    tg = math.tan(math.radians(alpha_max(a, R, z)))
    assert abs(tg - math.tan(alpha(math.pi / 2, a, R, z))) < 1e-9
    assert abs(tg - math.sqrt(2 * a / D)) < 0.1 * tg, tg        # ≈ √(2·a_k)
    R2 = 1.1 * R
    pts = profile_points(a, R2, D, z)
    rs = [math.hypot(*p) for p in pts]
    assert len(pts) == z * 24
    assert abs(max(rs) - (R2 + a + D / 2)) < 1e-6
    assert abs(min(rs) - (R2 - a + D / 2)) < 1e-3
    ro, rv = contact_ratios(math.pi / 2, a, R, z)
    assert 1.0 < rv < 1.4 and 0.0 < ro < 1.0, (ro, rv)
    return True
