"""Точный профиль венца ПТК и передача усилия (CP-08, Д-31, Д-34).

Тело в радиальном пазу сепаратора прижато к эксцентрику; центр тела в системе
венца: r(t) = e·cos(zt) + √(R0² − e²·sin²(zt)), R0 = Ø дел./2 (радиус эксцентрика
+ радиус тела). t = 0 — впадина 0 (наибольший радиус). Профиль венца — эквидистанта
траектории наружу на ρ = Ø тела/2. Подреза нет, пока на участках, выпуклых внутрь,
радиус кривизны траектории ≥ ρ — отсюда e max. Угол профиля γ (касательная к
траектории — окружность), tg γ = |r′|/r, определяет передачу усилия (Д-34).
"""
import math
from functools import lru_cache


def radius(t, e, R0, z):
    s = e * math.sin(z * t)
    return e * math.cos(z * t) + math.sqrt(R0 * R0 - s * s)


def dradius(t, e, R0, z):
    """dr/dt траектории центра тела."""
    w = z * t
    S = math.sqrt(R0 * R0 - (e * math.sin(w)) ** 2)
    return -e * z * math.sin(w) * (1 + e * math.cos(w) / S)


def curv_radius_min(e, R0, z, k=200):
    """Наименьший радиус кривизны там, где центр кривизны снаружи; inf — нигде."""
    h, best = 1e-4 / z, math.inf
    for i in range(k + 1):
        t = math.pi / z * i / k                       # полшага: профиль симметричен
        r0, rp, rm = (radius(x, e, R0, z) for x in (t, t + h, t - h))
        d1, d2 = (rp - rm) / (2 * h), (rp - 2 * r0 + rm) / (h * h)
        num = r0 * r0 + 2 * d1 * d1 - r0 * d2         # знак кривизны в полярных коорд.
        if num < 0:
            best = min(best, (r0 * r0 + d1 * d1) ** 1.5 / -num)
    return best


@lru_cache(maxsize=None)
def e_max(R0, rho, z):
    """Наибольший e без подреза эквидистанты (бисекция, проверка по всему шагу)."""
    lo, hi = 0.0, 0.5 * R0
    if curv_radius_min(hi, R0, z) >= rho:
        return hi
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if curv_radius_min(mid, R0, z) >= rho else (lo, mid)
    return lo


@lru_cache(maxsize=None)
def e_max_tip(R0, rho, z):
    """e max по вершине t = π/z: r = R0 − e, r′ = 0, r″ = e·z²(1 − e/R0),
    ρк = r²/(r″ − r) ≥ ρ. Быстрый вариант e_max для подбора gap_k (Д-34)."""
    f = lambda e: e * z * z * (1 - e / R0) - (R0 - e) * (1 + (R0 - e) / rho)
    lo, hi = 0.0, 0.5 * R0
    if f(hi) <= 0:
        return hi
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) <= 0 else (lo, mid)
    return lo


def gamma_deg(t, e, R0, z):
    """Угол профиля γ в точке t, град: tg γ = |r′|/r."""
    return math.degrees(math.atan2(abs(dradius(t, e, R0, z)), radius(t, e, R0, z)))


def gamma_max(e, R0, z, k=120):
    """Наибольший угол профиля на полушаге, град."""
    return max(gamma_deg(math.pi / z * i / k, e, R0, z) for i in range(k + 1))


def flank_share(e, R0, z, gamma_lim, k=120):
    """Доля положений тела на полушаге, где γ ≥ gamma_lim."""
    return sum(gamma_deg(math.pi / z * (i + 0.5) / k, e, R0, z) >= gamma_lim
               for i in range(k)) / k


def efficiency(gamma, mu_ring, mu_slot):
    """КПД тела при угле профиля γ, град (квазистатика, Д-34):
    η = tg(γ − φ) / (tg γ·(1 + mu_slot·tg(γ − φ))), φ = arctg mu_ring; 0 — заклинивание."""
    phi = math.degrees(math.atan(mu_ring))
    if gamma <= phi:
        return 0.0
    g, gp = math.radians(gamma), math.radians(gamma - phi)
    return math.tan(gp) / (math.tan(g) * (1 + mu_slot * math.tan(gp)))


def wave(gk, n, z, d, ecc_k, e_margin):
    """Волна при шаге gap_k: (R0, e max, e, γ max)."""
    R0 = n * gk * d / (2 * math.pi)
    em = e_max_tip(round(R0, 6), d / 2, z)
    e = min(ecc_k * d, e_margin * em)
    return R0, em, e, gamma_max(e, R0, z)


def select_gap_k(n, z, d, gk_min, gk_max, ecc_k, e_margin, gamma_min, step=0.05):
    """Д-34: наименьший gap_k ∈ [gk_min, gk_max] с γ max ≥ gamma_min -> (gap_k, wave, найден).
    γ растёт с gap_k, пока e ограничен подрезом, и падает, когда e упирается в
    ecc_k·Ø тела. Нет решения — gap_k с наибольшим γ и найден = False."""
    w = lambda gk: wave(gk, n, z, d, ecc_k, e_margin)
    best, prev, gk = None, None, gk_min
    while True:
        cur = w(gk)
        if best is None or cur[3] > best[1][3]:
            best = (gk, cur)
        if cur[3] >= gamma_min:
            if prev is None:
                return gk, cur, True
            lo, hi = prev, gk
            for _ in range(20):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if w(mid)[3] < gamma_min else (lo, mid)
            g3 = math.ceil(hi * 1000 - 1e-9) / 1000
            c3 = w(g3)
            return (g3, c3, True) if c3[3] >= gamma_min else (hi, w(hi), True)
        if gk >= gk_max:
            return best[0], best[1], False
        prev, gk = gk, min(gk + step, gk_max)


def profile_points(e, R0, rho, z, k=24):
    """Контур впадин: z·k точек против часовой стрелки, замкнутый."""
    N, h, pts = z * k, 1e-6, []
    pol = lambda t: (radius(t, e, R0, z) * math.cos(t), radius(t, e, R0, z) * math.sin(t))
    for i in range(N):
        t = 2 * math.pi * i / N
        (x, y), (x1, y1), (x0, y0) = pol(t), pol(t + h), pol(t - h)
        tx, ty = x1 - x0, y1 - y0
        L = math.hypot(tx, ty)
        pts.append((x + rho * ty / L, y - rho * tx / L))   # наружная нормаль
    return pts


def theory_md():
    return """## Профиль венца и кинематика (Д-31, CP-08)

Схема Д-11: венец неподвижен, вход — эксцентрик генератора, выход — сепаратор с
радиальными пазами; тело в пазу движется строго по радиусу и прижато к эксцентрику.

| Обозначение | Смысл |
|---|---|
| R0 | Ø дел./2 = радиус наружного кольца эксцентрика + ρ |
| ρ | Ø тела/2 |
| e | эксцентриситет генератора |
| φ, ψ | углы поворота эксцентрика (вход) и сепаратора (выход) |
| t | угол в системе венца от впадины 0 |
| γ | угол профиля: между касательной к траектории и окружностью |

Расстояние центра тела от оси: ρc = e·cos(α − φ) + √(R0² − e²·sin²(α − φ)),
α — угол тела. Профиль венца с z впадинами r(α) = F(z·α) держит контакт со всеми
телами при любом φ, если z·α ≡ α − φ для каждого тела, отсюда:

- n = z − 1, ψ = −φ/n, **u = n = z − 1** (вращение обратное); для заданного u
  калькулятор берёт z = u + 1 (u = z — схема с неподвижным сепаратором и выходом
  на венец, X-06);
- траектория центра тела в системе венца: **r(t) = e·cos(z·t) + √(R0² − e²·sin²(z·t))**;
- профиль венца — эквидистанта траектории наружу на ρ;
  Ø впадин = 2(R0 + e + ρ), Ø вершин = 2(R0 − e + ρ), глубина волны 2e;
- ход тела в пазу сепаратора 2e, длина паза ≥ Ø тела + 2e;
- подрез: на вершинах (выступах внутрь) радиус кривизны траектории
  ρк = (r² + r′²)^{3/2} / |r² + 2r′² − r·r″| должен быть ≥ ρ. На вершине
  r″ = e·z²(1 − e/R0), ρк = r²/(r″ − r), откуда **e max ≈ (R0 − e)(1 + (R0 − e)/ρ) / z²**;
  итоговая геометрия проверяется численно по всему шагу;
- принято **e = min(ecc_k·Ø тела, e_margin·e max)**; радиус вершины венца ρк − ρ,
  при e → e max он стремится к 0, поэтому e_margin < 1.

### Передача усилия и подбор gap_k (Д-34)

Эксцентрик толкает тело по радиусу, склон профиля отклоняет его, паз сепаратора
принимает касательную силу Ft. **tg γ = |r′(t)|/r(t)**; γ = 0 во впадине и на
вершине, наибольший на середине склона: **tg γ max ≈ e·z/R0**. На одно тело:

- Fr = Ft/tg γ — радиальная сила на эксцентрик и подшипник генератора;
- N = Ft/sin γ — нормальная сила в контакте с венцом (вход контакта Герца, CP-08);
- **η = tg(γ − φ) / (tg γ·(1 + mu_slot·tg(γ − φ)))**, φ = arctg mu_ring; γ ≤ φ — заклинивание.

При e по подрезу **tg γ max ≈ e_margin·gap_k/π**: угол задаёт шаг тел, а не u.
gap_k — результат: наименьший из [gap_k_min; gap_k_max] с γ max ≥ gamma_min,
оценка **gap_k ≈ π·tg(gamma_min)/e_margin**. Рост γ ограничен ecc_k: при
gap_k* ≈ π·√(2·ecc_k/e_margin) e упирается в ecc_k·Ø тела, дальше γ падает;
предел tg γ ≈ e_margin·gap_k*/π (≈ 32° при ecc_k = 0.25, e_margin = 0.8).
Цена угла — диаметр: Ø дел. = n·gap_k·Ø тела/π.

Контакт Герца и момент — CP-08, открыто."""


def self_test():
    em = e_max(18.3, 2.5, 21)
    assert 0.25 < em < 0.42, em                       # ≈ 0.335 по приближению
    assert curv_radius_min(0.9 * em, 18.3, 21) >= 2.5
    assert curv_radius_min(1.2 * em, 18.3, 21) < 2.5
    assert abs(e_max_tip(18.3, 2.5, 21) - em) < 0.05 * em   # вершина — худшая точка
    e = 0.8 * em
    pts = profile_points(e, 18.3, 2.5, 21)
    rs = [math.hypot(*p) for p in pts]
    assert len(pts) == 21 * 24
    assert abs(max(rs) - (18.3 + e + 2.5)) < 1e-6 and abs(min(rs) - (18.3 - e + 2.5)) < 1e-3
    # Д-34: угол профиля, КПД, подбор gap_k
    g = gamma_max(e, 18.3, 21)
    assert abs(math.tan(math.radians(g)) - e * 21 / 18.3) < 0.15 * e * 21 / 18.3, g
    assert efficiency(5.0, 0.1, 0.1) == 0.0 and 0.6 < efficiency(25.0, 0.08, 0.1) < 0.9
    gk, w, ok = select_gap_k(32, 33, 2.0, 1.0, 3.0, 0.25, 0.8, 25.0)
    assert ok and w[3] >= 25.0 and 1.5 < gk < 2.2, (gk, w)
    assert not select_gap_k(32, 33, 2.0, 1.0, 3.0, 0.25, 0.8, 45.0)[2]   # предел ecc_k
    return True
