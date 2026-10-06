"""Калькулятор волнового редуктора ПТК, уровень 1 (кинематика + реализуемость).

Схема (Д-11): генератор волн — вход, жёсткое колесо (внешний венец) с z
впадинами неподвижно, сепаратор с n = z - 1 телами — выход; u = z.
4 ряда с фазировкой 0/90/180/270° (Д-08). Венец несёт крепёжные отверстия,
они же технологические базы при изготовлении (Д-16). Отверстия пакета сквозные,
фазировка рядов переносится на сдвиг сверловки каждого венца (Д-19).

Рабочие параметры — specs/ptk_input.json (instructions/INS-10_PTK_CALC.md).
Значения по умолчанию в dataclass используются только в self_test() (Д-18).
"""
import math
import hashlib
import json
from dataclasses import dataclass, asdict, field, fields
from fractions import Fraction

from egm import ptk_profile


@dataclass
class PtkLimits:
    d_out_max: float = 110.0      # макс. наружный Ø редуктора, мм (Д-08)
    u_min: int = 10               # диапазон одноступенчатого u (Д-08, Д-11)
    u_max: int = 100
    wall_min: float = 4.0         # мин. стенка венца, мм
    gap_k_min: float = 1.0        # диапазон подбора gap_k = шаг тел / Ø тела (Д-34)
    gap_k_max: float = 3.0
    gamma_min: float = 25.0       # мин. наибольший угол профиля γ max, град (Д-34)
    mu_ring: float = 0.08         # трение тело/венец (заклинивание при γ ≤ arctg mu_ring)
    mu_slot: float = 0.1          # трение тело/паз сепаратора
    d_bc_step: float = 0.1        # округление вверх Ø окр. отв., мм (Д-35)
    d_out_step: float = 1.0       # округление вверх Øнар, мм (Д-35)
    ecc_k: float = 0.25           # эксцентриситет / Ø тела
    gen_bore_min: float = 18.0    # мин. Ø под генератор (подшипник + вал), мм
    row_gap: float = 1.0          # осевой зазор (шайба) между рядами, мм
    rows: int = 4
    row_phases: tuple = (0, 90, 180, 270)   # фазы эксцентриков рядов, град (Д-19)
    u_list: tuple = (10, 16, 20, 25, 32, 40, 50, 63, 80, 100)
    e_margin: float = 0.8         # e = min(ecc_k·Ø тела, e_margin·e max) (Д-31)


@dataclass
class RingHoles:
    bolt: str = "M4"              # ключ таблицы fasteners
    n: int = 8                    # число крепёжных отверстий венца (любое, Д-19)
    pins: int = 2                 # штифтовые отверстия H7 в промежутках между болтами
    pin_d: float = 4.0            # Ø штифта, мм
    head_margin: float = 0.5      # зазор головки болта до кромки/впадин, мм
    web_min: float = 1.0          # мин. перемычка между головками/штифтами, мм
    mu: float = 0.12              # коэффициент трения в стыке венец/корпус
    safety: float = 1.5           # запас удержания момента крепежом


@dataclass
class PtkResult:
    u: int
    body: str
    d_body: float
    id: str = ""
    n_bodies: int = 0
    z_ring: int = 0
    ecc: float = 0.0
    e_max: float = 0.0
    gap_k: float = 0.0
    gamma_max: float = 0.0
    eta: float = 0.0
    fr_ft: float = None
    d_pitch: float = 0.0
    d_root: float = 0.0
    d_tip: float = 0.0
    holes: str = ""
    mount: str = ""
    d_bc: float = 0.0
    d_out: float = 0.0
    width: float = 0.0
    d_body_max: float = 0.0
    t_hold: float = 0.0
    ring_variants: int = 0
    phasing: list = field(default_factory=list)
    parts: list = field(default_factory=list)
    geom: dict = field(default_factory=dict)
    ok: bool = False
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def _load(cls, d):
    names = {f.name for f in fields(cls)}
    data = {k: v for k, v in d.items() if not k.startswith("_")}
    unknown = sorted(set(data) - names)
    if unknown:
        raise ValueError(f"{cls.__name__}: неизвестные параметры {unknown}")
    return cls(**{k: tuple(v) if isinstance(v, list) else v for k, v in data.items()})


def load_config(cfg):
    """specs/ptk_input.json -> (PtkLimits, {ключ: RingHoles}, fasteners, mount_mode) (Д-33)."""
    fast = {k: v for k, v in cfg["fasteners"].items() if not k.startswith("_")}
    raw = cfg.get("ring_mounts") or {"default": cfg["ring_holes"]}
    mounts = {k: _load(RingHoles, v) for k, v in raw.items() if not k.startswith("_")}
    return _load(PtkLimits, cfg["limits"]), mounts, fast, cfg.get("mount_mode", "first_ok")


def _band(holes, fast, lim):
    """Радиальный размер от профиля впадин до оси отверстия (и от оси до Øнар)."""
    f = fast.get(holes.bolt)
    if f is None:
        return lim.wall_min
    return max(lim.wall_min + f["d_clear"] / 2, f["dk"] / 2 + holes.head_margin)


def _ceil(x, step):
    """Округление вверх до шага (Д-35)."""
    return round(math.ceil(x / step - 1e-9) * step, 6) if step else x


def _deg(x):
    return round(float(x), 4)


def pin_gaps(holes):
    """Промежутки между болтами под штифты: j = round(i·n/pins); промежуток j —
    между болтами j и j+1 (болт j на угле j·360/n)."""
    if holes.pins <= 0 or holes.n < 1:
        return []
    return sorted({round(i * holes.n / holes.pins) % holes.n for i in range(holes.pins)})


def pattern_order(holes):
    """Порядок N поворотной симметрии сверловки (болты + штифты), шаг σ = 360/N."""
    n = holes.n
    if n < 1:
        return 1
    gaps = set(pin_gaps(holes))
    for m in sorted((m for m in range(1, n + 1) if n % m == 0), reverse=True):
        step = n // m
        if {(g + step) % n for g in gaps} == gaps:
            return m
    return 1


def phasing(z, n_bodies, holes, lim):
    """Д-19: сдвиг сверловки венцов при сквозных отверстиях пакета.

    Ряд k — копия ряда 1, повёрнутая на φk (эксцентрик генератора). Отверстия
    в корпусе совпадают, поэтому в системе профиля венца (впадина 0 на 0°)
    сверловка ряда k повёрнута на s = (−φk) mod g, g = 360°/НОК(z, N): венец
    симметричен с шагом 360/z, сверловка — с шагом 360/N. Равные s — один
    вариант венца. Гнёзда сепаратора ряда k смещены на φk mod (360/n)."""
    order = pattern_order(holes)
    g = Fraction(360, z * order // math.gcd(z, order))
    p = Fraction(360, z)
    q = Fraction(360, max(n_bodies, 1))
    phases = [Fraction(str(x)) for x in lim.row_phases]
    base = phases[0] if phases else Fraction(0)
    rows, labels = [], {}
    for k, ph in enumerate(phases):
        phi = (ph - base) % 360
        s = (-phi) % g
        var = labels.setdefault(s, chr(ord("A") + len(labels)))
        rows.append({"row": k + 1, "phi": _deg(phi), "delta_p": _deg((phi % p) / p),
                     "s": _deg(s), "cage": _deg(phi % q), "variant": var})
    return {"z": z, "pitch": _deg(p), "order": order, "g": _deg(g),
            "variants": len(labels), "rows": rows}


def ring(d_root, holes, fast, lim):
    """Отверстия венца (Д-16): окружность центров, Øнар, момент удержания, ошибки."""
    err = []
    f = fast.get(holes.bolt)
    band = _band(holes, fast, lim)
    r_bc = _ceil(d_root + 2 * band, lim.d_bc_step) / 2
    pins = f"+{holes.pins}шт Ø{holes.pin_d:g}" if holes.pins else ""
    res = {"d_bc": round(2 * r_bc, 2), "d_out": _ceil(2 * (r_bc + band), lim.d_out_step),
           "t_hold": 0.0,
           "label": f"{holes.n}×{holes.bolt}{pins}"}
    if f is None:
        return res, [f"крепёж {holes.bolt} отсутствует в таблице fasteners"]
    if holes.n < 1:
        return res, [f"число отверстий венца {holes.n} < 1"]
    n = holes.n
    if n >= 2:
        chord = 2 * r_bc * math.sin(math.pi / n)
        need = max(f["dk"] + holes.web_min, f["d_clear"] + lim.wall_min)
        if chord < need:
            err.append(f"{holes.n}×{holes.bolt} не помещаются на Ø{2 * r_bc:.1f}: "
                       f"шаг {chord:.1f} < {need:.1f} мм")
    if holes.pins:
        half = 2 * r_bc * math.sin(math.pi / (2 * n))
        need_p = f["dk"] / 2 + holes.pin_d / 2 + holes.web_min
        if half < need_p:
            err.append(f"штифт Ø{holes.pin_d:g} между болтами не помещается: "
                       f"{half:.1f} < {need_p:.1f} мм")
        if holes.pins > holes.n:
            err.append(f"штифтов {holes.pins} больше, чем промежутков между болтами {holes.n}")
    res["t_hold"] = round(holes.n * f["F_M"] * holes.mu * r_bc, 1)  # кН·мм = Н·м
    return res, err


# Д-22: маркировка конфигураций. GEOM_REV повышается при смене формул геометрии
# (CP-08 и далее) — тогда меняются все ID, старые чертежи остаются при старых ID.
GEOM_REV = 3                       # Д-34: gap_k подбирается по γ; Д-35: округление
GEOM_LIMITS = ("gap_k_min", "gap_k_max", "gamma_min", "ecc_k", "e_margin", "wall_min",
               "row_gap", "rows", "row_phases", "d_bc_step", "d_out_step")
GEOM_HOLES = ("bolt", "n", "pins", "pin_d", "head_margin")
BODY_TYPES = {"roller": "R", "ball": "B"}


def _n(v):
    """Нормализация для хэша: 4 и 4.0 — одно значение."""
    if isinstance(v, bool) or v is None or isinstance(v, str):
        return v
    if isinstance(v, (int, float)):
        return round(float(v), 6)
    if isinstance(v, (list, tuple)):
        return [_n(x) for x in v]
    if isinstance(v, dict):
        return {k: _n(x) for k, x in v.items()}
    return v


def _num(x):
    return f"{float(x):g}".replace(".", "_")   # точка занята разделителем детали


def body_code(body):
    t = BODY_TYPES.get(body.get("type"), "X")
    if t == "B":
        return f"B{_num(body['d'])}"
    return f"{t}{_num(body['d'])}X{_num(body.get('l', body['d']))}"


def holes_code(holes):
    return f"{holes.n}{holes.bolt}" + (f"P{holes.pins}" if holes.pins else "")


def geom_params(u, body, lim, holes, fast):
    """Все параметры, определяющие геометрию исполнения (вход хэша и CAD)."""
    f = fast.get(holes.bolt, {})
    return _n({"rev": GEOM_REV, "u": u,
               "body": {k: body.get(k) for k in ("type", "d", "l")},
               "limits": {k: getattr(lim, k) for k in GEOM_LIMITS},
               "ring_holes": {k: getattr(holes, k) for k in GEOM_HOLES},
               "fastener": {k: f.get(k) for k in ("d_clear", "dk")}})


def config_id(u, body, lim, holes, fast):
    """ID исполнения PTK-<u>-<тело>-<отверстия>-<хэш> (Д-22) и снимок геометрии."""
    g = geom_params(u, body, lim, holes, fast)
    raw = json.dumps(g, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    h = hashlib.sha1(raw.encode("ascii")).hexdigest()[:6].upper()
    return f"PTK-{u:03d}-{body_code(body)}-{holes_code(holes)}-{h}", g


def ring_parts(cid, ph):
    """Детали .01<вариант> — венцы (Д-19, Д-22). Остальные детали — OQ-04."""
    out = {}
    for row in ph["rows"]:
        v = row["variant"]
        p = out.setdefault(v, {"id": f"{cid}.01{v}", "name": "венец", "variant": v,
                               "s": row["s"], "s_arc_mm": row.get("s_arc_mm"), "rows": []})
        p["rows"].append(row["row"])
    return list(out.values())


def find(rows, cid):
    """Запись ptk_configs.json по ID исполнения или детали (вход CP-05)."""
    base = cid.split(".")[0]
    for r in rows:
        if r.get("id") == base:
            return r
    raise KeyError(f"конфигурация {base} не найдена в ptk_configs.json")


def calc(u, body_id, body, lim, holes, fast):
    """Расчёт одной конфигурации. body = {'type','d','l'}."""
    d = body["d"]
    r = PtkResult(u, body_id, d)
    r.id, r.geom = config_id(u, body, lim, holes, fast)
    if u > lim.u_max:
        s = two_stage(u, lim)
        r.errors.append(f"u={u} > {lim.u_max}: одноступенчатый ПТК не считается; рекомендуется "
                        f"двухступенчатая схема {s['u1']}×{s['u2']} = {s['u']} (Д-11)")
        return r
    if u < lim.u_min:
        r.errors.append(f"u={u} < {lim.u_min}: вне диапазона (Д-08)")
    if u < 2:
        return r
    z, n = u + 1, u                      # Д-31: венец неподвижен, выход — сепаратор
    gk, (R0, _, ecc, gmax), found = ptk_profile.select_gap_k(
        n, z, d, lim.gap_k_min, lim.gap_k_max, lim.ecc_k, lim.e_margin, lim.gamma_min)
    d_pitch = 2 * R0
    e_max = ptk_profile.e_max(round(R0, 6), d / 2, z)        # численно по всему шагу
    r.gap_k, r.e_max, r.gamma_max = round(gk, 3), round(e_max, 3), round(gmax, 1)
    r.eta = round(ptk_profile.efficiency(gmax, lim.mu_ring, lim.mu_slot), 3)
    r.fr_ft = round(1 / math.tan(math.radians(gmax)), 2) if gmax > 0 else None
    if ecc > e_max:
        r.errors.append(f"подрез профиля венца: e={ecc:.3f} > e max={e_max:.3f} мм (Д-31)")
    if not found:
        r.errors.append(f"угол профиля γ max {gmax:.1f}° < {lim.gamma_min:g}° при gap_k ≤ "
                        f"{lim.gap_k_max:g} (Д-34): больше ecc_k или меньше gamma_min")
    if r.eta == 0:
        r.errors.append(f"заклинивание: γ max {gmax:.1f}° ≤ arctg mu_ring (Д-34)")
    d_root = d_pitch + d + 2 * ecc
    rg, rerr = ring(d_root, holes, fast, lim)
    r.errors += rerr
    band = _band(holes, fast, lim)
    r.d_body_max = round((lim.d_out_max - 4 * band)
                         / (n * gk / math.pi + 1 + 2 * ecc / d), 2)
    if rg["d_out"] > lim.d_out_max:
        r.errors.append(f"Øнар {rg['d_out']:.1f} > {lim.d_out_max:g}: тела Ø{d:g} при n={n} "
                        f"с отверстиями {rg['label']} не вмещаются; макс. Ø тела "
                        f"{r.d_body_max:g} мм (OQ-05)")
    d_gen = d_pitch - d - 2 * ecc
    if d_gen < lim.gen_bore_min:
        r.errors.append(f"генератор Ø{d_gen:.1f} < {lim.gen_bore_min:g}: мал для подшипника/вала")
    if lim.rows != len(lim.row_phases):
        r.errors.append("число рядов не совпадает с фазировкой")
    ph = phasing(z, n, holes, lim)
    for row in ph["rows"]:
        row["s_arc_mm"] = round(row["s"] * math.pi * rg["d_bc"] / 360, 3)
    r.n_bodies, r.z_ring, r.ecc = n, z, round(ecc, 3)
    r.d_pitch, r.d_root = round(d_pitch, 2), round(d_root, 2)
    r.d_tip = round(d_pitch + d - 2 * ecc, 2)
    r.holes, r.d_bc, r.t_hold = rg["label"], rg["d_bc"], rg["t_hold"]
    r.ring_variants, r.phasing = ph["variants"], ph["rows"]
    r.parts = ring_parts(r.id, ph)
    r.d_out = round(rg["d_out"], 2)
    r.width = round(lim.rows * body["l"] + (lim.rows + 1) * lim.row_gap, 1)
    r.ok = not r.errors
    return r


def sweep(bodies, lim, mounts, fast, mode="first_ok"):
    """Д-33: для каждой пары (u, тело) — все крепления (all) или первое прошедшее (first_ok)."""
    out = []
    for u in lim.u_list:
        for bid, b in bodies.items():
            if bid.startswith("_"):
                continue
            rs = []
            for key, h in mounts.items():
                r = calc(u, bid, b, lim, h, fast)
                r.mount = key
                rs.append(r)
            out += rs if mode == "all" else [next((r for r in rs if r.ok), rs[0])]
    return out


def two_stage(u, lim):
    """Д-11: u = u1·u2, обе ступени в u_min..u_max, ступени по возможности равны."""
    best = None
    for u1 in range(lim.u_min, lim.u_max + 1):
        u2 = min(max(round(u / u1), lim.u_min), lim.u_max)
        key = (abs(u1 * u2 - u), abs(u1 - u2))
        if best is None or key < best[0]:
            best = (key, max(u1, u2), min(u1, u2))
    _, u1, u2 = best
    return {"u": u1 * u2, "u1": u1, "u2": u2, "exact": u1 * u2 == u,
            "ok": lim.u_min ** 2 <= u <= lim.u_max ** 2}


def two_stage_table(lim, u_list=(101, 120, 150, 200, 300, 500, 1000, 2500)):
    rows = ["| u | u1 | u2 | u1·u2 | Точно |", "|---|---|---|---|---|"]
    for u in u_list:
        s = two_stage(u, lim)
        exact = "да" if s["exact"] else "нет, ближайшее"
        rows.append(f"| {u} | {s['u1']} | {s['u2']} | {s['u']} | {exact} |")
    return (f"Одноступенчатый ПТК считается только для u ≤ {lim.u_max} (Д-11). Для больших u "
            "применяется двухступенчатая схема; каждая ступень рассчитывается этим же "
            "калькулятором как самостоятельный редуктор.\n\n" + "\n".join(rows))


def force_table(rows):
    """Д-34: передача усилия по исполнениям (раздел SPEC-10)."""
    t = ["### Передача усилия по исполнениям (Д-34)", "",
         "| ID | gap_k | e | γ max, ° | Fr/Ft | η | Статус |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["z_ring"]:
            t.append(f"| {r['id']} | {r['gap_k']} | {r['ecc']} | {r['gamma_max']} | "
                     f"{r['fr_ft'] or '—'} | {r['eta']} | {'OK' if r['ok'] else 'нет'} |")
    return "\n".join(t)


def phasing_table(lim, holes):
    """Таблица фазировки рядов и сдвигов сверловки для SPEC-10 (Д-19)."""
    order = pattern_order(holes)
    gaps = pin_gaps(holes)
    pins = (f", штифты Ø{holes.pin_d:g} в промежутках {gaps}" if gaps else ", без штифтов")
    head = (f"Сверловка венца: {holes.n}×{holes.bolt} через {360 / max(holes.n, 1):g}°{pins}; "
            f"порядок симметрии сверловки N = {order} (σ = {360 / order:g}°). "
            "Не зависит от тела качения, поэтому дана по u.")
    rows = ["| u (z = u + 1) | p, ° | g, ° | Венцов | Ряд | φ, ° | δ/p | s, ° | Сепаратор, ° | Вариант |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for u in lim.u_list:
        if not 2 <= u <= lim.u_max:
            continue
        ph = phasing(u + 1, u, holes, lim)
        for i, row in enumerate(ph["rows"]):
            lead = (f"| {u} | {ph['pitch']:g} | {ph['g']:g} | {ph['variants']} |"
                    if i == 0 else "| | | | |")
            rows.append(lead + f" {row['row']} | {row['phi']:g} | {row['delta_p']:g} | "
                        f"{row['s']:g} | {row['cage']:g} | {row['variant']} |")
    return head + "\n\n" + "\n".join(rows)


def params_md(lim, holes, fast):
    """Таблица входных параметров прогона для SPEC-10."""
    rows = ["| Параметр | Значение |", "|---|---|"]
    for obj, pre in ((lim, "limits"), (holes, "ring_holes")):
        for f in fields(obj):
            rows.append(f"| `{pre}.{f.name}` | {getattr(obj, f.name)} |")
    f = fast.get(holes.bolt, {})
    rows.append(f"| `fasteners.{holes.bolt}` | отверстие Ø{f.get('d_clear')}, головка "
                f"Ø{f.get('dk')}, затяжка {f.get('F_M')} кН |")
    return "\n".join(rows)


def torque_estimate(r: PtkResult, q_allow=None):
    """Грубая оценка момента: TODO(CP-08) — контакт Герца, доля нагруженных тел."""
    q = q_allow or 30.0 * r.d_body ** 2   # Н на тело, заглушка
    loaded = max(1, r.n_bodies // 3)
    return round(q * loaded * (r.d_pitch / 2000.0) * 4, 1)  # Н·м, 4 ряда


def to_rows(results, mounts):
    out = []
    for r in results:
        holes = mounts.get(r.mount) or next(iter(mounts.values()))
        row = asdict(r)
        m = torque_estimate(r) if r.ok else None
        row["torque_Nm_est"] = m
        if m is not None and r.t_hold < m * holes.safety:
            row["warnings"].append(
                f"момент удержания крепежа {r.t_hold:g} Н·м < {holes.safety:g}×M "
                f"({m * holes.safety:.0f} Н·м): больше/крупнее болтов или штифты под срез; "
                "M — заглушка до CP-08")
        out.append(row)
    return out


def self_test():
    """Проверки ПО на фиксированных параметрах (не зависят от ptk_input.json)."""
    lim, holes = PtkLimits(), RingHoles()
    fast = {"M4": {"d_clear": 4.5, "dk": 7.0, "F_M": 4.1}}
    b = {"type": "roller", "d": 5.0, "l": 8.0}

    def c(u, h=holes):
        return calc(u, "t", b, lim, h, fast)

    assert not c(100).ok
    r = c(19)                                             # z = 20 кратно 4
    assert r.ok, r.errors
    assert r.z_ring == 20 and r.n_bodies == 19            # Д-31: u = n = z − 1
    assert 0 < r.ecc <= r.e_max and abs(r.d_root - r.d_tip - 4 * r.ecc) < 0.02
    assert 75.0 < r.d_out < 100.0 and r.d_out == int(r.d_out), r.d_out   # Д-35
    assert r.gamma_max >= lim.gamma_min - 0.05 and r.eta > 0.6, (r.gamma_max, r.eta)
    assert r.ring_variants == 1, r.phasing
    assert not c(5).ok
    r = c(120)
    assert not r.ok and "двухступенчат" in r.errors[0]
    assert two_stage(200, lim)["u"] == 200 and two_stage(200, lim)["exact"]
    assert c(63).d_body_max < 5.0
    r = c(20, RingHoles(n=6))
    assert r.ok, r.errors                                 # кратность 4 не нужна (Д-19)
    assert not c(20, RingHoles(n=40)).ok                  # не помещаются по шагу
    assert not c(20, RingHoles(bolt="M99")).ok            # нет в таблице крепежа
    # Д-19: симметрия сверловки и сдвиги
    h8 = RingHoles(n=8, pins=0)
    assert pattern_order(h8) == 8 and pattern_order(holes) == 2
    assert pattern_order(RingHoles(n=8, pins=4)) == 4
    ph = phasing(63, 62, holes, lim)                      # N=2: g = 360/126
    assert ph["variants"] == 2 and abs(ph["rows"][1]["s"] - 180 / 126) < 1e-3, ph
    assert phasing(63, 62, h8, lim)["variants"] == 1      # N=8: 90° кратно 360/504
    ph = phasing(25, 24, RingHoles(n=5, pins=0), lim)     # НОК=25, g=14.4°
    assert ph["variants"] == 4 and abs(ph["rows"][1]["s"] - 10.8) < 1e-3, ph
    assert abs(phasing(20, 19, holes, lim)["rows"][1]["cage"] - 90 % (360 / 19)) < 1e-3
    # Д-22: маркировка
    r = c(20)
    assert r.id.startswith("PTK-020-R5X8-8M4P2-") and len(r.id.split("-")[-1]) == 6, r.id
    assert c(20).id == r.id                                       # детерминирован
    assert c(20, RingHoles(safety=3.0, mu=0.2)).id == r.id        # не геометрия
    assert c(20, RingHoles(pin_d=4)).id == r.id                   # 4 == 4.0
    assert c(20, RingHoles(pin_d=5.0)).id != r.id                 # геометрия
    assert calc(20, "t", b, PtkLimits(gamma_min=20.0), holes, fast).id != r.id
    assert body_code({"type": "ball", "d": 2.5}) == "B2_5"
    assert [p["id"] for p in c(62).parts] == [c(62).id + ".01A", c(62).id + ".01B"]  # z = 63
    rows = [asdict(c(20)), asdict(c(62))]
    assert find(rows, c(62).id + ".01B")["u"] == 62
    return True


if __name__ == "__main__":
    print(self_test())
