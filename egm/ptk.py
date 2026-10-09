"""Калькулятор волнового редуктора ПТК: кинематика, профиль венца, реализуемость.

Схема (Д-11, Д-31): генератор волн — вход, венец с z впадинами неподвижен, сепаратор
с n телами — выход; u = n = z − 1, для заданного u — z = u + 1 (egm/calc_vptc.py:
zg = i + 1, zsh = i). 4 ряда 0/90/180/270° (Д-08). Отверстия венца — крепёж и
технологические базы (Д-16), пакет сквозной, фаза ряда — поворот сверловки (Д-19).

Порядок расчёта (Д-38): u, D_ш, a_ω → R_Σ — наименьший без подреза вершины зуба, с
перемычкой сепаратора и D_г ≥ Dgen_min → профиль по (6) Янгулова → D_В, α max →
отверстия, D. Обозначения — Д-37. Параметры — specs/ptk_input.json (INS-10);
значения по умолчанию в dataclass — только для self_test() (Д-18).
"""
import hashlib
import json
import math
from dataclasses import asdict, dataclass, field, fields
from fractions import Fraction

from egm import ptk_force, ptk_parts, ptk_profile

SEP_K = 1.1    # полутолщина кольца сепаратора / a_ω (egm/calc_vptc.py: hc = 2.2·e)
GEN_TYPES = ("bearing", "eccentric")   # Д-42: тела на наружном кольце подшипника | на эксцентрике


@dataclass
class PtkLimits:
    d_out_max: float = 110.0      # D max — наружный Ø редуктора, мм (Д-08); None — без предела (Д-43)
    u_min: int = 10               # диапазон одноступенчатого u (Д-08, Д-11)
    u_max: int = 100
    wall_min: float = 4.0         # стенка впадины–отверстие и отверстие–D, мм; у тела — своя
    a_k: float = 0.2              # a_ω = a_k·D_ш, если у тела нет a_w (calc_vptc.py: 0.2)
    r_tip_min: float = 0.05       # наименьший радиус вершины зуба венца, мм
    sep_web_min: float = 1.0      # наименьшая перемычка сепаратора между пазами, мм
    shaft_d_min: float = 6.0      # Ø входного вала в эксцентрике, мм (Д-40)
    ecc_wall_min: float = 1.0     # стенка эксцентрика: d подш. ≥ shaft_d_min + 2(a_ω + ecc_wall_min)
    d_bc_step: float = 0.1        # округление вверх D_отв, мм (Д-35)
    d_out_step: float = 1.0       # округление вверх D, мм (Д-35)
    row_gap: float = 1.0          # осевой зазор (шайба) между рядами, мм
    rows: int = 4
    row_phases: tuple = (0, 90, 180, 270)   # фазы эксцентриков рядов, град (Д-19)
    u_list: tuple = (10, 16, 20, 25, 32, 40, 50, 63, 80, 100)
    E_mod: float = 210000.0       # модуль упругости тел, венца, колец подшипника, МПа (Д-41)
    nu: float = 0.3               # коэффициент Пуассона
    sigma_H_line: float = 2500.0  # допускаемое σ_H, линейный контакт (ролик), МПа (OQ-08)
    sigma_H_point: float = 3000.0  # допускаемое σ_H, точечный контакт (шарик), МПа (OQ-08)
    s0_brg: float = 1.0           # запас статической грузоподъёмности подшипника, C0/P0
    M_min: float = 0.0            # требуемый выходной момент, Н·м; 0 — не проверяется (Д-41)
    gen_types: tuple = ("bearing", "eccentric")   # генераторы для расчёта (Д-42)
    dgen_step: float = 0.1        # округление вверх D_г эксцентрика без подшипника, мм (Д-42)
    groove_f: float = 0.52        # жёлоб под шарик на эксцентрике: r = groove_f·D_ш, > 0.5 (Д-45)
    sep_gap: float = 0.05         # зазор тела в окне сепаратора, мм (Д-46)
    rho: float = 7850.0           # плотность стали эксцентрика, тел, колец, кг/м³
    brg_mass_k: float = 0.35      # масса подшипника / сплошное кольцо D×d×B, если нет bearings.m
    shaft_key_b: float = 2.0      # шпонка вала: ширина паза b, мм (DIN 6885 A — сверить)
    shaft_key_t2: float = 1.0     # глубина паза в ступице t2, мм
    key_angle: float = 45.0       # паз ряда 1 от эксцентриситета, град; ряд k: key_angle − φk
    bal_wall: float = 1.0         # стенка у отверстий балансировки, мм
    bal_n_max: int = 3            # наибольшее число отверстий балансировки
    bal_d_min: float = 1.0        # Ø отверстий балансировки: от, мм
    bal_d_step: float = 0.1       # шаг Ø (сверло), мм


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
    roller: str                   # ключ vendor_prices.json → rollers
    Drol: float                   # D_ш
    id: str = ""
    n: int = 0                    # тел в ряду
    z: int = 0                    # впадин венца
    a_w: float = 0.0              # a_ω
    R_sum: float = 0.0            # R_Σ
    R_by: str = ""                # что задало R_Σ: подрез | сепаратор | генератор
    Dgen: float = 0.0             # D_г
    bearing: str = ""             # подшипник генератора, ключ vendor_prices.json → bearings (Д-40)
    gen: str = "bearing"          # тип генератора: bearing | eccentric (Д-42)
    d_root: float = 0.0           # D_В
    d_tip: float = 0.0            # D_верш
    alpha_max: float = 0.0        # α max, град
    r_tip: float = 0.0            # радиус вершины зуба венца, мм
    sep_web: float = 0.0          # перемычка сепаратора, мм
    holes: str = ""
    mount: str = ""
    d_bc: float = 0.0             # D_отв
    d_out: float = 0.0            # D
    width: float = 0.0            # B
    Drol_max: float = 0.0
    t_hold: float = 0.0
    M_H: float = 0.0              # допускаемый момент по Герцу, Н·м (Д-41)
    M_B: float = 0.0              # то же по C0 подшипника, Н·м
    M: float = 0.0                # допускаемый выходной момент, Н·м
    M_by: str = ""                # что ограничивает M: контакт | подшипник | крепление
    ring_variants: int = 0
    phasing: list = field(default_factory=list)
    parts: list = field(default_factory=list)
    geom: dict = field(default_factory=dict)
    ok: bool = False
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    tech: list = field(default_factory=list)      # коды TECH (Д-45)
    excluded: str = ""                            # код TECH, по которому исключено из SPEC-10
    sep: dict = field(default_factory=dict)       # сепаратор .02 (Д-46)
    ecc: dict = field(default_factory=dict)       # эксцентрик .03 (Д-46)


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
    lim = _load(PtkLimits, cfg["limits"])
    bad = [g for g in lim.gen_types if g not in GEN_TYPES]
    if bad or not lim.gen_types:
        raise ValueError(f"limits.gen_types: {list(lim.gen_types)} — допустимы {GEN_TYPES} (Д-42)")
    if lim.groove_f <= 0.5:
        raise ValueError(f"limits.groove_f = {lim.groove_f}: нужно > 0.5 — жёлоб шире шарика (Д-45)")
    return lim, mounts, fast, cfg.get("mount_mode", "first_ok")


def _band(holes, fast, wall):
    """b — от профиля впадин до оси отверстия; столько же от оси до D."""
    f = fast.get(holes.bolt)
    if f is None:
        return wall
    return max(wall + f["d_clear"] / 2, f["dk"] / 2 + holes.head_margin)


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


def phasing(z, n_rol, holes, lim):
    """Д-19: сдвиг сверловки венцов при сквозных отверстиях пакета.

    Ряд k — копия ряда 1, повёрнутая на φk. В системе профиля венца сверловка ряда k
    повёрнута на s = (−φk) mod g, g = 360°/НОК(z, N). Равные s — один вариант венца.
    Гнёзда сепаратора ряда k смещены на φk mod (360/n)."""
    order = pattern_order(holes)
    g = Fraction(360, z * order // math.gcd(z, order))
    p = Fraction(360, z)
    q = Fraction(360, max(n_rol, 1))
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


def ring(d_root, holes, fast, lim, wall):
    """Отверстия венца (Д-16): D_отв, D, момент удержания, ошибки."""
    err = []
    f = fast.get(holes.bolt)
    band = _band(holes, fast, wall)
    r_bc = _ceil(d_root + 2 * band, lim.d_bc_step) / 2
    pins = f"+{holes.pins}шт Ø{holes.pin_d:g}" if holes.pins else ""
    res = {"d_bc": round(2 * r_bc, 2), "d_out": _ceil(2 * (r_bc + band), lim.d_out_step),
           "t_hold": 0.0, "label": f"{holes.n}×{holes.bolt}{pins}"}
    if f is None:
        return res, [f"крепёж {holes.bolt} отсутствует в таблице fasteners"]
    if holes.n < 1:
        return res, [f"число отверстий венца {holes.n} < 1"]
    n = holes.n
    if n >= 2:
        chord = 2 * r_bc * math.sin(math.pi / n)
        need = max(f["dk"] + holes.web_min, f["d_clear"] + wall)
        if chord < need:
            err.append(f"{holes.n}×{holes.bolt} не помещаются на D_отв {2 * r_bc:.1f}: "
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


# Д-22: маркировка. GEOM_REV повышается при смене формул геометрии — меняются все ID.
GEOM_REV = 6                       # Д-42: тип генератора bearing | eccentric в хэше
# Д-48: параметры эксцентрика (rho, brg_mass_k, shaft_key_*, key_angle, bal_*) — не в хэше;
# эксцентрик в SPEC-10 предварительный по limits, окончательный — шаг 2 (egm/ptk_design.py)
GEOM_LIMITS = ("a_k", "r_tip_min", "sep_web_min", "shaft_d_min", "ecc_wall_min", "wall_min",
               "row_gap", "rows", "row_phases", "d_bc_step", "d_out_step", "dgen_step",
               "sep_gap")
GEOM_HOLES = ("bolt", "n", "pins", "pin_d", "head_margin")
GEOM_ROLLER = ("type", "d", "l", "a_w", "wall_min")
GEOM_BEARING = ("d", "D", "B")     # Д-40
ROLLER_TYPES = {"roller": "R", "ball": "B"}

# Д-45: технологические ограничения пар тело/генератор/венец — код: (пара, следствие, обоснование)
TECH = {
    "Т1": ("шарик / наружное кольцо подшипника",
           "исключено из результатов SPEC-10",
           "без жёлоба контакт точечный: допускаемая сила на шарик — десятки Н (B_D3, u = 10: "
           "M ≈ 1 Н·м, CP-32); жёлоб на закалённой шлифованной дорожке покупного подшипника "
           "не изготовить"),
    "Т2": ("шарик / эксцентрик",
           "контакт с жёлобом r = groove_f·Dш: k_y = 2/Dш − 1/(groove_f·Dш); Герц в круговом "
           "приближении — оценка",
           "жёлоб точится и шлифуется на эксцентрике .03 (своё изготовление); на чертёж .03 — "
           "радиус и биение жёлоба (CP-28)"),
    "Т3": ("шарик / венец",
           "жёлоба в венце нет: шарик на профиле как на плоскости — обычно ограничивает M",
           "жёлоб по траектории (6) — сферической фрезой (SM-1, ось C) или профильным "
           "электродом ЭЭС; не заложен — OQ-11"),
    "Т4": ("тело / эксцентрик без подшипника",
           "M без проверки по скорости входа; η и износ не считаются",
           "скольжение ≈ ω·Dг/2: твёрдость эксцентрика не ниже тел, смазка; предел скорости — "
           "OQ-10 после калибровки OQ-08"),
}


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


def roller_code(rol):
    t = ROLLER_TYPES.get(rol.get("type"), "X")
    if t == "B":
        return f"B{_num(rol['d'])}"
    return f"{t}{_num(rol['d'])}X{_num(rol.get('l', rol['d']))}"


def holes_code(holes):
    return f"{holes.n}{holes.bolt}" + (f"P{holes.pins}" if holes.pins else "")


def geom_params(u, rol, lim, holes, fast, brg=None, gen="bearing"):
    """Все параметры, определяющие геометрию исполнения (вход хэша и CAD)."""
    f = fast.get(holes.bolt, {})
    return _n({"rev": GEOM_REV, "u": u, "gen": gen,
               "roller": {k: rol.get(k) for k in GEOM_ROLLER},
               "bearing": {k: brg.get(k) for k in GEOM_BEARING} if brg else None,
               "limits": {k: getattr(lim, k) for k in GEOM_LIMITS},
               "ring_holes": {k: getattr(holes, k) for k in GEOM_HOLES},
               "fastener": {k: f.get(k) for k in ("d_clear", "dk")}})


def config_id(u, rol, lim, holes, fast, brg=None, gen="bearing"):
    """ID исполнения PTK-<u>-<тело>-<отверстия>-<хэш> (Д-22) и снимок геометрии."""
    g = geom_params(u, rol, lim, holes, fast, brg, gen)
    raw = json.dumps(g, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    h = hashlib.sha1(raw.encode("ascii")).hexdigest()[:6].upper()
    return f"PTK-{u:03d}-{roller_code(rol)}-{holes_code(holes)}-{h}", g


def ring_parts(cid, ph):
    """Детали .01<вариант> — венцы (Д-19, Д-22)."""
    out = {}
    for row in ph["rows"]:
        v = row["variant"]
        p = out.setdefault(v, {"id": f"{cid}.01{v}", "name": "венец", "variant": v,
                               "s": row["s"], "s_arc_mm": row.get("s_arc_mm"), "rows": []})
        p["rows"].append(row["row"])
    return list(out.values())


def find(rows, cid):
    """Запись ptk_configs.json по ID исполнения или детали."""
    base = cid.split(".")[0]
    for r in rows:
        if r.get("id") == base:
            return r
    raise KeyError(f"конфигурация {base} не найдена в ptk_configs.json")


def r_sum(u, D, a, lim):
    """Д-38, Д-40: наименьший R_Σ по подрезу и сепаратору -> (R_Σ min, условие)."""
    z, n = u + 1, u
    return max((ptk_profile.r_sum_undercut(round(a, 6), round(D / 2 + lim.r_tip_min, 6), z),
                "подрез"),
               ((D + lim.sep_web_min) / (2 * math.sin(math.pi / n)) + SEP_K * a, "сепаратор"))


def bearing(D, R_min, a, bears, lim):
    """Д-40: подшипник генератора — наименьший D ≥ 2R_Σ min − D_ш с d ≥ shaft_d_min +
    2(a_ω + ecc_wall_min); при равных D — больший C0. -> (ключ | None, D треб., d треб.)."""
    need_D = 2 * R_min - D
    need_d = lim.shaft_d_min + 2 * (a + lim.ecc_wall_min)
    fit = sorted((b["D"], -b["C0"], k) for k, b in bears.items()
                 if not k.startswith("_") and b["D"] >= need_D - 1e-9 and b["d"] >= need_d - 1e-9)
    return (fit[0][2] if fit else None), need_D, need_d


def calc(u, rid, rol, lim, holes, fast, bears, gen="bearing"):
    """Расчёт одной конфигурации. rol = {'type','d','l'[, 'a_w', 'wall_min']};
    gen — bearing (тела на наружном кольце подшипника, Д-40) | eccentric (на эксцентрике, Д-42)."""
    D = rol["d"]
    wall = rol.get("wall_min", lim.wall_min)
    a = rol.get("a_w") or lim.a_k * D
    r = PtkResult(u, rid, D, gen=gen)
    r.id, r.geom = config_id(u, rol, lim, holes, fast, None, gen)
    if u > lim.u_max:
        s = two_stage(u, lim)
        r.errors.append(f"u={u} > {lim.u_max}: одноступенчатый ПТК не считается; рекомендуется "
                        f"двухступенчатая схема {s['u1']}×{s['u2']} = {s['u']} (Д-11)")
        return r
    if u < lim.u_min:
        r.errors.append(f"u={u} < {lim.u_min}: вне диапазона (Д-08)")
    if u < 2:
        return r
    z, n = u + 1, u                                     # Д-31
    if rol.get("type") == "ball" and gen == "bearing":   # Д-45: жёлоб на покупном кольце не сделать
        r.n, r.z, r.excluded, r.tech = n, z, "Т1", ["Т1"]
        return r
    R, by = r_sum(u, D, a, lim)
    brg = None
    if gen == "bearing":
        bk, need_D, need_d = bearing(D, R, a, bears, lim)
        brg = bears.get(bk) if bk else None
        if brg is None:
            r.errors.append(f"нет подшипника генератора с D ≥ {need_D:.1f} и d ≥ {need_d:.1f} мм "
                            f"в vendor_prices.json → bearings (Д-40)")
        else:
            R = (brg["D"] + D) / 2
            r.bearing = bk
            r.id, r.geom = config_id(u, rol, lim, holes, fast, brg, gen)
    else:                                               # Д-42: D_г — наружный Ø эксцентрика
        need_d = lim.shaft_d_min + 2 * (a + lim.ecc_wall_min)
        if need_d > 2 * R - D + 1e-9:
            by = "вал"
        R = (_ceil(max(2 * R - D, need_d), lim.dgen_step) + D) / 2
    rho_k = ptk_profile.curv_radius_min(a, R, z)
    d_root = 2 * (R + a) + D
    r.n, r.z, r.a_w, r.R_sum, r.R_by = n, z, round(a, 3), round(R, 3), by
    r.Dgen = round(2 * R - D, 2)
    r.d_root, r.d_tip = round(d_root, 2), round(2 * (R - a) + D, 2)
    r.alpha_max = round(ptk_profile.alpha_max(a, R, z), 1)
    r.r_tip = round(min(rho_k, 1e3) - D / 2, 3)
    r.sep_web = round(2 * (R - SEP_K * a) * math.sin(math.pi / n) - D, 2)
    rg, rerr = ring(d_root, holes, fast, lim, wall)
    r.errors += rerr
    band = _band(holes, fast, wall)
    if lim.d_out_max:                                   # None / 0 — без предела габарита (Д-43)
        r.Drol_max = math.floor((lim.d_out_max - 4 * band) / (d_root / D) * 100) / 100
        if rg["d_out"] > lim.d_out_max:
            r.errors.append(f"D {rg['d_out']:g} > {lim.d_out_max:g}: тела Dш {D:g} при n={n} "
                            f"с отверстиями {rg['label']} не вмещаются; Dш max ≈ "
                            f"{r.Drol_max:g} мм (OQ-05)")
    if lim.rows != len(lim.row_phases):
        r.errors.append("число рядов не совпадает с фазировкой")
    ph = phasing(z, n, holes, lim)
    for row in ph["rows"]:
        row["s_arc_mm"] = round(row["s"] * math.pi * rg["d_bc"] / 360, 3)
    r.holes, r.d_bc, r.t_hold = rg["label"], rg["d_bc"], rg["t_hold"]
    r.ring_variants, r.phasing = ph["variants"], ph["rows"]
    r.parts = ring_parts(r.id, ph)
    r.d_out = round(rg["d_out"], 2)
    pitch = max(rol["l"], brg["B"]) if brg else rol["l"]          # Д-40: шаг ряда
    r.width = round(lim.rows * pitch + (lim.rows + 1) * lim.row_gap, 1)
    if not r.errors and (brg is not None or gen == "eccentric"):    # Д-46: детали .02, .03
        r.sep = ptk_parts.separator(n, R, a, D, rol["l"], pitch, r.phasing, lim, SEP_K)
        r.ecc = ptk_parts.eccentric(n, a, D, rol, brg, r.phasing, lim, gen, R)
        r.warnings += r.ecc.pop("warnings")
        r.parts += ptk_parts.parts(r.id, r.ecc)
    if (brg is not None or gen == "eccentric") and not r.errors:
        t = ptk_force.torque(n, z, a, R, D, rol["l"], rol.get("type", "roller"), brg, lim,
                             lim.rows)
        r.M_H, r.M_B = t["M_H"], t["M_B"] or 0.0
        cand = [(r.M_H, "контакт"), (round(r.t_hold / holes.safety, 1), "крепление")]
        if brg is not None:
            cand.append((r.M_B, "подшипник"))
        r.M, r.M_by = min(cand)
        if r.M < lim.M_min:
            r.errors.append(f"M {r.M:g} < M_min {lim.M_min:g} Н·м, ограничивает: {r.M_by} (Д-41)")
    if gen == "eccentric":                               # Д-45
        r.tech += (["Т2", "Т3"] if rol.get("type") == "ball" else []) + ["Т4"]
    r.ok = not r.errors
    return r


def sweep(rollers, bears, lim, mounts, fast, mode="first_ok"):
    """Д-33, Д-42: для (u, тело, генератор) — все крепления (all) или первое прошедшее (first_ok)."""
    out = []
    for u in lim.u_list:
        for rid, rol in rollers.items():
            if rid.startswith("_"):
                continue
            for gen in lim.gen_types:
                rs = []
                for key, h in mounts.items():
                    r = calc(u, rid, rol, lim, h, fast, bears, gen)
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


def profile_table(rows):
    """Д-38: профиль и нагрузки по исполнениям (раздел SPEC-10)."""
    t = ["### Профиль и нагрузки по исполнениям (Д-38)", "",
         "R_о/R, R_в/R — (8), (9) при φ = 90° (α = α max), на 1 Н реакции генератора.", "",
         "| ID | $a_\\omega$ | $R_\\Sigma$ | $R_\\Sigma$ задан | $D_\\text{г}$ | α max, ° | "
         "$R_\\text{о}/R$ | $R_\\text{в}/R$ | r верш., мм | перемычка сеп., мм | Статус |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if not r["z"]:
            continue
        ro, rv = ptk_profile.contact_ratios(math.pi / 2, r["a_w"], r["R_sum"], r["z"])
        t.append(f"| {r['id']} | {r['a_w']} | {r['R_sum']} | {r['R_by']} | {r['Dgen']} | "
                 f"{r['alpha_max']} | {ro:.2f} | {rv:.2f} | {r['r_tip']} | {r['sep_web']} | "
                 f"{'OK' if r['ok'] else 'нет'} |")
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
    for obj, pre in ((lim, "limits"), (holes, "ring_mounts")):
        for f in fields(obj):
            rows.append(f"| `{pre}.{f.name}` | {getattr(obj, f.name)} |")
    f = fast.get(holes.bolt, {})
    rows.append(f"| `fasteners.{holes.bolt}` | отверстие Ø{f.get('d_clear')}, головка "
                f"Ø{f.get('dk')}, затяжка {f.get('F_M')} кН |")
    return "\n".join(rows)


def to_rows(results, mounts):
    """Строки ptk_configs.json; M, M_by считаются в calc (Д-41); mounts — для совместимости."""
    return [asdict(r) for r in results]


def tech_md():
    """Расшифровка технологических кодов (Д-45) для SPEC-10."""
    L = ["| Код | Пара | Следствие для расчёта | Обоснование |", "|---|---|---|---|"]
    L += [f"| {k} | {p} | {e} | {w} |" for k, (p, e, w) in TECH.items()]
    return "\n".join(L)


def self_test():
    """Проверки ПО на фиксированных параметрах (не зависят от ptk_input.json)."""
    lim, holes = PtkLimits(), RingHoles()
    fast = {"M4": {"d_clear": 4.5, "dk": 7.0, "F_M": 4.1}}
    bears = {f"T{d}": {"d": d - 12.0, "D": float(d), "B": 7.0, "C": 5.0, "C0": 5.0}
             for d in range(19, 121)}                      # шаг D 1 мм: R_Σ ≈ R_Σ min
    b = {"type": "roller", "d": 5.0, "l": 8.0}

    def c(u, h=holes, rol=b):
        return calc(u, "t", rol, lim, h, fast, bears)

    r = c(19)                                             # z = 20 кратно 4
    assert r.ok, r.errors
    assert r.z == 20 and r.n == 19 and r.a_w == 1.0       # Д-31, a_ω = 0.2·D_ш
    assert r.R_by == "подрез" and r.r_tip >= lim.r_tip_min - 1e-3, (r.R_by, r.r_tip)
    assert abs(r.d_root - r.d_tip - 4 * r.a_w) < 0.02
    assert 75.0 < r.d_out < 100.0 and r.d_out == int(r.d_out), r.d_out   # Д-35
    assert 25.0 < r.alpha_max < 40.0, r.alpha_max          # ≈ √(2·a_k)
    assert r.sep_web >= lim.sep_web_min - 1e-6
    assert r.bearing and r.Dgen == bears[r.bearing]["D"], (r.bearing, r.Dgen)   # Д-40
    assert abs(2 * r.R_sum - r.Dgen - r.Drol) < 1e-3
    assert r.width == 4 * 8.0 + 5 * lim.row_gap
    assert r.M > 0 and r.M_by in ("контакт", "подшипник", "крепление"), (r.M, r.M_by)
    assert r.M <= min(r.M_H, r.M_B, r.t_hold / holes.safety) + 0.1                # Д-41
    assert not calc(19, "t", b, PtkLimits(M_min=1e6), holes, fast, bears).ok
    assert not calc(19, "t", b, lim, holes, fast, {}).ok                         # нет подшипника
    assert c(19, rol={**b, "a_w": 0.5}).alpha_max < r.alpha_max   # меньше a_ω — меньше α
    assert c(19, rol={**b, "wall_min": 8.0}).d_out > r.d_out       # wall_min тела
    e = calc(19, "t", b, lim, holes, fast, {}, "eccentric")      # Д-42: каталог не нужен
    assert e.ok and not e.bearing and e.gen == "eccentric", e.errors
    assert e.Dgen >= lim.shaft_d_min + 2 * (e.a_w + lim.ecc_wall_min) - 1e-9
    assert abs(2 * e.R_sum - e.Dgen - e.Drol) < 1e-3 and e.M_B == 0.0
    assert e.M_by in ("контакт", "крепление") and e.id != r.id, (e.M_by, e.id)
    assert e.width == 4 * 8.0 + 5 * lim.row_gap
    assert "Т4" in e.tech and not r.tech, (e.tech, r.tech)
    bb = c(10, rol={"type": "ball", "d": 2.0, "l": 2.0})          # Д-45: шарик на подшипнике
    assert not bb.ok and bb.excluded == "Т1" and not bb.errors, bb
    be = calc(10, "t", {"type": "ball", "d": 2.0, "l": 2.0}, lim, holes, fast, {}, "eccentric")
    assert not be.excluded and be.tech == ["Т2", "Т3", "Т4"], be.tech
    assert tech_md().count("| Т") == len(TECH)
    big = calc(100, "t", b, PtkLimits(d_out_max=None), holes, fast, {}, "eccentric")
    assert big.ok and big.d_out > 110.0 and big.Drol_max == 0.0, big.errors   # Д-43
    try:
        load_config({"limits": {"gen_types": ["magnet"]}, "ring_mounts": {"x": {}}, "fasteners": {}})
        raise AssertionError("неизвестный gen_types принят")
    except ValueError:
        pass
    rb = c(10, rol={"type": "roller", "d": 2.0, "l": 2.0})
    assert bears[rb.bearing]["d"] >= lim.shaft_d_min + 2 * (rb.a_w + lim.ecc_wall_min) - 1e-9
    assert r.ring_variants == 1, r.phasing
    assert not c(5).ok and not c(100).ok
    r = c(120)
    assert not r.ok and "двухступенчат" in r.errors[0]
    assert two_stage(200, lim)["u"] == 200 and two_stage(200, lim)["exact"]
    assert c(63).Drol_max < 5.0
    assert c(20, RingHoles(n=6)).ok                       # кратность 4 не нужна (Д-19)
    assert not c(20, RingHoles(n=40)).ok
    assert not c(20, RingHoles(bolt="M99")).ok
    h8 = RingHoles(n=8, pins=0)
    assert pattern_order(h8) == 8 and pattern_order(holes) == 2
    assert pattern_order(RingHoles(n=8, pins=4)) == 4
    ph = phasing(63, 62, holes, lim)
    assert ph["variants"] == 2 and abs(ph["rows"][1]["s"] - 180 / 126) < 1e-3, ph
    assert phasing(63, 62, h8, lim)["variants"] == 1
    ph = phasing(25, 24, RingHoles(n=5, pins=0), lim)
    assert ph["variants"] == 4 and abs(ph["rows"][1]["s"] - 10.8) < 1e-3, ph
    r = c(20)
    assert r.id.startswith("PTK-020-R5X8-8M4P2-") and len(r.id.split("-")[-1]) == 6, r.id
    assert c(20).id == r.id
    assert c(20, RingHoles(safety=3.0, mu=0.2)).id == r.id
    assert c(20, RingHoles(pin_d=4)).id == r.id
    assert c(20, RingHoles(pin_d=5.0)).id != r.id
    assert calc(20, "t", b, PtkLimits(a_k=0.15), holes, fast, bears).id != r.id
    assert roller_code({"type": "ball", "d": 2.5}) == "B2_5"
    assert [p["id"] for p in c(62).parts if ".01" in p["id"]] == [c(62).id + ".01A", c(62).id + ".01B"]
    rows = [asdict(c(20)), asdict(c(62))]
    assert find(rows, c(62).id + ".01B")["u"] == 62
    return True


if __name__ == "__main__":
    print(self_test())
