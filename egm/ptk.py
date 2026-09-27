"""Калькулятор волнового редуктора ПТК, уровень 1 (кинематика + реализуемость).

Схема (OQ-02, предварительно): генератор волн — вход, жёсткое колесо с z_r
впадинами неподвижно, сепаратор с n = z_r - 1 телами — выход; u = z_r.
4 ряда с фазировкой 0/90/180/270° (Д-08).
"""
import math
from dataclasses import dataclass, asdict, field


@dataclass
class PtkLimits:
    d_out_max: float = 110.0   # Д-08
    u_min: int = 10
    u_max: int = 100
    wall_min: float = 4.0      # минимальная стенка корпуса/колеса, мм
    gap_k: float = 1.15        # шаг тел / диаметр тела (перемычка сепаратора)
    rows: int = 4
    row_phases: tuple = (0, 90, 180, 270)
    # TODO(CP-08): вынести в specs/ptk_limits.json


@dataclass
class PtkResult:
    u: int
    body: str
    d_body: float
    n_bodies: int
    z_ring: int
    ecc: float
    d_pitch: float
    d_out: float
    width: float
    ok: bool
    errors: list = field(default_factory=list)


def calc(u, body_id, body, lim=PtkLimits()):
    """Расчёт одной конфигурации. body = {'type','d','l'}."""
    err = []
    d = body["d"]
    z_r = u
    n = z_r - 1
    if not lim.u_min <= u <= lim.u_max:
        err.append(f"u={u} вне диапазона {lim.u_min}..{lim.u_max}")
    ecc = 0.5 * d * 0.5          # эксцентриситет ≈ четверть диаметра тела
    # TODO(CP-08): эксцентриситет из условия непрерывного зацепления
    step = lim.gap_k * d
    d_pitch = max(n * step / math.pi, 1e-9)
    d_out = d_pitch + d + 2 * ecc + 2 * lim.wall_min
    if d_out > lim.d_out_max:
        err.append(f"Øнар {d_out:.1f} > {lim.d_out_max}: тела Ø{d} не вмещаются при n={n}")
    d_gen = d_pitch - d - 2 * ecc
    if d_gen < 2 * lim.wall_min + 10:
        err.append(f"генератор Ø{d_gen:.1f} слишком мал для подшипника/вала")
    if lim.rows != len(lim.row_phases):
        err.append("число рядов не совпадает с фазировкой")
    width = lim.rows * body["l"] + (lim.rows + 1) * 1.0
    return PtkResult(u, body_id, d, n, z_r, round(ecc, 3), round(d_pitch, 2),
                     round(d_out, 2), round(width, 1), not err, err)


def sweep(bodies, u_list=(10, 16, 20, 25, 32, 40, 50, 63, 80, 100)):
    return [calc(u, bid, b) for u in u_list for bid, b in bodies.items()
            if not bid.startswith("_")]


def torque_estimate(r: PtkResult, q_allow=None):
    """Грубая оценка момента: TODO(CP-08) — контакт Герца, доля нагруженных тел."""
    q = q_allow or 30.0 * r.d_body ** 2   # Н на тело, заглушка
    loaded = max(1, r.n_bodies // 3)
    return round(q * loaded * (r.d_pitch / 2000.0) * 4, 1)  # Н·м, 4 ряда


def to_rows(results):
    out = []
    for r in results:
        row = asdict(r)
        row["torque_Nm_est"] = torque_estimate(r) if r.ok else None
        out.append(row)
    return out


def self_test():
    """Проверки ПО: u=100 роликом Ø5 в Ø110 нереализуемо; u=20 Ø5 реализуемо."""
    b = {"type": "roller", "d": 5.0, "l": 8.0}
    assert not calc(100, "t", b).ok
    assert calc(20, "t", b).ok
    assert not calc(5, "t", b).ok
    return True


if __name__ == "__main__":
    print(self_test())
