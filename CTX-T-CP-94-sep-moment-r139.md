# CTX-T — CP-94: предел по переносу момента через ряд окон (M_sep), rev13.9

База: `ee15b20ecfbc27d4930898534110852ba7cc2ab0` (ветка `rev13.9`; содержит rev13.7 с CP-93…CP-97 и rev13.8 с новыми телами качения).
Продукт `euginb/HarmonicV2`, ПТК. Язык ответа — русский, комментарии в коде — русский, с номерами Д-##/CP-##.

## Правила вывода (INS-91B §6)

1. Ответ — два блока: `p.diff` (unified diff от указанной базы) и `upd.md` (что сделано, что проверено, что осталось).
2. Маркеры `===== FILE: … =====` / `===== END FILE =====` — только в этом CTX, в ответе их быть не должно.
3. Правки — минимальные; стиль и структура кода — как в приложенных файлах.

## Задача

Добавить в шаг 1 проверку сепаратора и учесть её в моменте исполнения. Сейчас
`M = min(M_H, M_B, t_hold/safety)` (`egm/ptk.py`), сепаратор в минимум не входит, поэтому K20
(`PTK-063-R3X8-22M6P2-BDBB72`) проходит с «✓» при M 1160.5 Н·м, а ручная оценка модели даёт предел
сепаратора 250…500 Н·м. Требуется:

1. `M_sep` — предел по трём механизмам: перенос момента через ряд окон (рама Виренделя), изгиб
   перемычки нагрузкой своего ряда, контакт тела со стороной окна (Герц + кромочный контакт).
2. Допускаемое — многоцикловая усталость (нагружение на каждый оборот входа): `[σ] = σ₋₁/(K·S)`,
   `K ≈ 2` в углах окон.
3. `M_sep` входит в `min(...)`, `M_by` получает значение «сепаратор», причина — `sep_why`.
4. Коэффициенты (K_окн, S_sep, k_edge и т. п.) — в `specs/ptk_input.yaml` с комментарием-глоссарием
   в `egm/ptk_doc.py`; в коде — без магических чисел.
5. Пересчитать K10/K20: ожидается падение M до 250…500 Н·м и смена `M_by`.
6. `self_test` фиксирует K20: σ в перемычке ≤ [σ], M_sep < M_H.

Стенка `t = 2.2·a_ω` задана кинематикой (запас по `sep_web_min` 0.06 мм) — поднимать её нельзя.

## Новое в этой ветке (важно для задачи)

- `specs/vendor_prices.yaml` → `rollers`: пользователь добавил тела **D5×5, D5×8, D6×6, D7×20, D8×8, D8×16**
  (было только 2 и 3 мм). Каталог приложен целиком ниже.
- После пересчёта шага 1 с новым каталогом тела D5…D8 дают `M = 0.0` и габарит 198…364 мм — то есть
  для u 50/63 они не проходят по габариту; рабочее тело по-прежнему `R3X8`. Это ожидаемо (CP-95/CP-97),
  но при реализации `M_sep` перебор тел уже включает новые.
- Ветка `rev13.8` (влита в `rev13.9`) содержит пользовательские правки схем ПТК и новые ролики.


---

# Исходники

## Расчёт шага 1 и профиль

===== FILE: egm/ptk.py (строки 1–624) =====
"""Калькулятор волнового редуктора ПТК: кинематика, профиль венца, реализуемость.

Схема (Д-11, Д-31): генератор волн — вход, венец с z впадинами неподвижен, сепаратор
с n телами — выход; u = n = z − 1, для заданного u — z = u + 1 (egm/calc_vptc.py:
zg = i + 1, zsh = i). 4 ряда 0/90/180/270° (Д-08). Отверстия венца — крепёж и
технологические базы (Д-16), пакет сквозной, фаза ряда — поворот сверловки (Д-19).

Порядок расчёта (Д-38): u, D_ш, a_ω → R_Σ — наименьший без подреза вершины зуба, с
перемычкой сепаратора и D_г ≥ Dgen_min → профиль по (6) Янгулова → D_В, α max →
отверстия, D. Обозначения — Д-37. Параметры — specs/ptk_input.yaml (INS-10);
значения по умолчанию в dataclass — только для self_test() (Д-79).
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
    spacer_gap: float = 0.5       # зазор dвн шайбы .05 над DВ венца, мм; не в хэше ID (Д-53)


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
    roller: str                   # ключ vendor_prices.yaml → rollers
    Drol: float                   # D_ш
    id: str = ""
    n: int = 0                    # тел в ряду
    z: int = 0                    # впадин венца
    a_w: float = 0.0              # a_ω
    R_sum: float = 0.0            # R_Σ
    R_by: str = ""                # что задало R_Σ: подрез | сепаратор | генератор
    Dgen: float = 0.0             # D_г
    bearing: str = ""             # подшипник генератора, ключ vendor_prices.yaml → bearings (Д-40)
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
    spacer: dict = field(default_factory=dict)    # шайбы .05 (Д-53)


def _load(cls, d):
    names = {f.name for f in fields(cls)}
    data = {k: v for k, v in d.items() if not k.startswith("_")}
    unknown = sorted(set(data) - names)
    if unknown:
        raise ValueError(f"{cls.__name__}: неизвестные параметры {unknown}")
    return cls(**{k: tuple(v) if isinstance(v, list) else v for k, v in data.items()})


def load_config(cfg):
    """specs/ptk_input.yaml -> (PtkLimits, {ключ: RingHoles}, fasteners, mount_mode) (Д-33)."""
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
    Окна сепаратора ряда k повёрнуты на (−s·z − φk)/n mod (360/n) (Д-46, Д-53, OQ-13)."""
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
                     "s": _deg(s), "cage": _deg(((-s * z - phi) / max(n_rol, 1)) % q),
                     "variant": var})
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


# Д-80: маркировка. GEOM_REV повышается при смене формул геометрии — меняются все ID.
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
    """ID исполнения PTK-<u>-<тело>-<отверстия>-<хэш> (Д-80) и снимок геометрии."""
    g = geom_params(u, rol, lim, holes, fast, brg, gen)
    raw = json.dumps(g, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    h = hashlib.sha1(raw.encode("ascii")).hexdigest()[:6].upper()
    return f"PTK-{u:03d}-{roller_code(rol)}-{holes_code(holes)}-{h}", g


def ring_parts(cid, ph):
    """Детали .01<вариант> — венцы (Д-19, Д-80)."""
    out = {}
    for row in ph["rows"]:
        v = row["variant"]
        p = out.setdefault(v, {"id": f"{cid}.01{v}", "name": "венец", "variant": v,
                               "s": row["s"], "s_arc_mm": row.get("s_arc_mm"), "rows": []})
        p["rows"].append(row["row"])
    return list(out.values())


def find(rows, cid):
    """Запись ptk_configs.yaml по ID исполнения или детали."""
    base = cid.split(".")[0]
    for r in rows:
        if r.get("id") == base:
            return r
    raise KeyError(f"конфигурация {base} не найдена в ptk_configs.yaml")


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
                            f"в vendor_prices.yaml → bearings (Д-40)")
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
        r.spacer = ptk_parts.spacers(d_root, r.d_out, r.d_bc, r.geom["fastener"]["d_clear"],
                                     rol["l"], pitch, lim.rows, lim)
        r.warnings += r.spacer.pop("warnings")
        r.parts += ptk_parts.spacer_parts(r.id, r.spacer, lim.rows)
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


def to_rows(results, mounts):
    """Строки ptk_configs.yaml; M, M_by считаются в calc (Д-41); mounts — для совместимости."""
    return [asdict(r) for r in results]


def tech_md():
    """Расшифровка технологических кодов (Д-45) для SPEC-10."""
    L = ["| Код | Пара | Следствие для расчёта | Обоснование |", "|---|---|---|---|"]
    L += [f"| {k} | {p} | {e} | {w} |" for k, (p, e, w) in TECH.items()]
    return "\n".join(L)


def self_test():
    """Проверки ПО на фиксированных параметрах (не зависят от ptk_input.yaml)."""
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
    sp = [p for p in r.parts if ".05" in p["id"]]                 # Д-53: шаг = l — один вариант
    assert [p["id"][-4:] for p in sp] == [".05A"] and sp[0]["pos"] == [0, 1, 2, 3, 4], sp
    assert abs(sum(x["h"] for x in r.spacer["pos"]) + 4 * 8.0 - r.width) < 1e-6, r.spacer
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
===== END FILE =====
===== FILE: egm/ptk_force.py (строки 1–154) =====
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
Шарик на эксцентрике (Д-45, Т2): жёлоб $r = f D_\text{ш}$, $f$ = `groove_f`,
$k_y = 2/D_\text{ш} - 1/(f D_\text{ш})$; шарик на подшипнике исключён (Т1), венец без жёлоба (Т3).

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
                          sigma_H_point=3000.0, s0_brg=1.0, groove_f=0.52)
    g0 = pair_limits(2.0, 2.0, "ball", 60.0, 2.0, lim)                    # Д-45: жёлоб
    g1 = pair_limits(2.0, 2.0, "ball", 60.0, 2.0, lim, True)
    assert g1[0] > 10 * g0[0] and g1[1] == g0[1], (g0, g1)
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
===== END FILE =====
===== FILE: egm/ptk_profile.py (строки 1–158) =====
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


def bodies(a_w, R_sum, n, theta_e=0.0):
    """Центры n тел ряда при эксцентрике на угле theta_e, град (система профиля, Д-44).

    Тело k: t_k = (2πk − θe)/n, |центр| = Y(t_k − θe) — на окружности R_Σ генератора и,
    при z = n + 1, на траектории (6): z·t_k ≡ t_k − θe (mod 2π)."""
    te = math.radians(theta_e)
    out = []
    for k in range(n):
        t = (2 * math.pi * k - te) / n
        y = Y(t - te, a_w, R_sum)
        out.append((y * math.cos(t), y * math.sin(t)))
    return out


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
    te = 37.0
    ex, ey = a * math.cos(math.radians(te)), a * math.sin(math.radians(te))
    for x, y in bodies(a, R2, z - 1, te):
        t = math.atan2(y, x)
        assert abs(math.hypot(x, y) - Y(z * t, a, R2)) < 1e-9          # на траектории (6)
        assert abs(math.hypot(x - ex, y - ey) - R2) < 1e-9              # на генераторе R_Σ
    return True
===== END FILE =====
===== FILE: egm/ptk_doc.py (строки 3–10) =====
Пишет main.py run_calc: specs/ptk_configs.yaml. Прежний ptk_configs.json читался, но не
объяснял смысл ~130 сокращённых ключей (R_sum, Drol_max, t_hold, M_H, sep_web, a_w…).
Здесь над каждым ключом стоит комментарий, в шапке — глоссарий сокращений.

Эмиттер — общий, egm/doc_yaml.py (Д-106). Таблица комментариев этого документа ниже:
GLOSSARY — точные пути, PATTERNS — повторяющиеся узлы (ряды, детали, позиции шайб),
GENERIC — последний рубеж по имени листа.
"""
===== END FILE =====

===== FILE: egm/ptk_doc.py (строки 41–45) =====
#   d_out       наружный диаметр венца, мм.
#   M_H, M_B    моменты, выдерживаемые венцом (H — holder) и подшипником генератора (B), Н·мм.
#   t_hold      момент удержания венца крепежом и посадкой, Н·мм.
#   Drol_max    наибольший допустимый диаметр тела качения для этого исполнения, мм.
#   ecc         эксцентрик .03; De — наружный Ø, t — толщина, a — эксцентриситет.
===== END FILE =====

===== FILE: egm/ptk_doc.py (строки 50–53) =====

GLOSSARY = {
    # --- исполнение --------------------------------------------------------
    "u": "Число тел качения в одном ряду, шт (в исполнении — сумма по рядам).",
===== END FILE =====

===== FILE: egm/ptk_doc.py (строки 75–81) =====
    "Drol_max": "Наибольший допустимый Ø тела качения для исполнения, мм.",
    "t_hold": "Момент удержания венца крепежом и посадкой, Н·мм.",
    "M_H": "Момент, который выдерживает венец (крепёж и посадка), Н·мм.",
    "M_B": "Момент, который выдерживает подшипник генератора, Н·мм.",
    "M": "Принятый момент исполнения M = min(M_H, M_B), Н·мм.",
    "M_by": "Чем ограничен момент: «венец» | «подшипник».",
    "ring_variants": "Число вариантов исполнения венца (фаз), шт.",
===== END FILE =====

===== FILE: egm/ptk_doc.py (строки 232–235) =====
    HEADER = HEADER
    GLOSSARY = GLOSSARY
    PATTERNS = PATTERNS
    GENERIC = GENERIC
===== END FILE =====

## Вход и каталоги

===== FILE: specs/ptk_input.yaml (строки 1–156) =====
# Входные параметры калькулятора ПТК — шаг 1 «Расчёт» (Д-16, Д-79).
# Формат — YAML (Д-79): описание каждого параметра — в комментарии рядом с ним,
# логика и формулы — instructions/INS-10_PTK_CALC.md.
# Запуск: python main.py calc --publish (шаг 1 отдельно) или полный прогон python main.py.
# Результат — specs/ptk_configs.json и specs/SPEC-10_PTK_CALC.md: их пишет машина,
# руками не править (code-first).

limits:
  # Наибольший наружный диаметр венца D, мм: 110 — станки и оснастка EG-MACHINES (Д-08);
  # null — без предела (Д-43). D больше предела — ошибка; колонка «Dш max» считается
  # только при заданном пределе.
  d_out_max: 200.0

  # Диапазон одноступенчатого передаточного числа u (Д-08: 10…100).
  # u > u_max — две ступени (Д-11).
  u_min: 10
  u_max: 100

  # Какие u считать — только состав таблицы SPEC-10. Пример: [30, 40, 50, 60].
  u_list: [10, 16, 20, 25, 32, 40, 50, 63, 80, 100]

  # aω / Dш, если у тела не задан свой a_w (Д-38: 0.2). Больше — глубже волна (4aω)
  # и больше α max (≈ arctg √(2aω/Dш)), но RΣ по подрезу и D растут.
  a_k: 0.2

  # Наименьший радиус кривизны профиля на вершине волны, мм (подрез) —
  # задаёт RΣ min при больших u.
  r_tip_min: 0.05

  # Наименьшая перемычка сепаратора между гнёздами, мм — задаёт RΣ min при малых u.
  sep_web_min: 1.0

  # Стенка венца: впадины — отверстие — кромка, мм; у тела можно переопределить
  # (wall_min в rollers). Больше — больше D.
  wall_min: 4.0

  # Ø входного вала в эксцентрике, мм (Д-40): по нему подбирается подшипник генератора,
  # входит в ID; на шаге 2 вал может быть толще (designs[].shaft.d), если проходит
  # стенка эксцентрика (проверка там же).
  shaft_d_min: 6.0

  # Стенка эксцентрика, мм: d ≥ shaft_d_min + 2·(aω + ecc_wall_min).
  # Больше — крупнее генератор при малых u.
  ecc_wall_min: 1.0

  # Округление вверх Dотв и D, мм (Д-35); проверка d_out_max — после округления.
  d_bc_step: 0.1
  d_out_step: 1.0

  # Осевой зазор или шайба между рядами, мм — входит в ширину пакета B.
  row_gap: 1.0

  # Число рядов и фазы эксцентриков, град (Д-08: 4 ряда, 0/90/180/270);
  # длина row_phases = rows. Сдвиг сверловки венцов — Д-19.
  rows: 4
  row_phases: [0, 90, 180, 270]

  # Типы генератора (Д-42): bearing — тела на наружном кольце подшипника;
  # eccentric — тела прямо по эксцентрику (жёлоб groove_f). Каждая пара (u, тело)
  # считается для каждого типа; тип входит в хэш ID и в колонку «Генератор».
  gen_types: [bearing, eccentric]

  # Округление вверх Dг эксцентрика, мм — только eccentric.
  dgen_step: 0.1

  # Радиус жёлоба под шарик на эксцентрике / Dш, > 0.5 (Д-45, Т2); 0.52 — как у
  # шарикоподшипников. Меньше — выше допускаемая сила шарик/эксцентрик; в ID не входит.
  groove_f: 0.52

  # Зазор тела в окне сепаратора, мм (Д-46): окна (Dш + sep_gap) × (l + sep_gap);
  # входит в ID.
  sep_gap: 0.05

  # Модуль упругости, МПа, и коэффициент Пуассона — тела, венец, кольца
  # (сталь: 210000, 0.3). Герц (Д-41).
  E_mod: 210000.0
  nu: 0.3

  # Допускаемое контактное напряжение, МПа: ролик (линия) / шарик (точка).
  # Ниже — меньше M_H; калибровка — OQ-08.
  sigma_H_line: 2500.0
  sigma_H_point: 3000.0

  # Запас C0/P0 подшипника генератора. Больше — меньше M_B.
  s0_brg: 1.0

  # Требуемый допускаемый момент M, Н·м; 0 — не проверяется. M < M_min — ошибка.
  M_min: 0.0

  # ─── Предварительный эксцентрик и шайбы шага 1: не входят в ID (Д-48, Д-53) ───
  # На шаге 1 считаются только для оценки; окончательные вал, шпонка и балансировка —
  # шаг 2 (designs[] в ptk_design_input.yaml), там переопределяются.

  # Плотность стали эксцентрика, тел, колец, кг/м³ — массы и балансировка.
  rho: 7850.0

  # Масса подшипника, кг: сплошное кольцо D×d×B, если в bearings нет m.
  brg_mass_k: 0.35

  # Шпоночный паз: ширина b и глубина в ступице t2, мм — keys.table шага 2 по shaft.d.
  shaft_key_b: 2.0
  shaft_key_t2: 1.0

  # Паз ряда 1 от эксцентриситета, град; ряд k — key_angle − φk (шаг 2, key_angle).
  key_angle: 45.0

  # Отверстия балансировки шага 1: стенка у отверстий, мм; наибольшее число, шт;
  # Ø от и шаг, мм. На шаге 2 — balance.wall / balance.n_max / balance.drills.
  bal_wall: 1.0
  bal_n_max: 3
  bal_d_min: 1.0
  bal_d_step: 0.1

  # Зазор dвн шайбы .05 над DВ венца, мм: тела и сепаратор шайбу не касаются (Д-53).
  spacer_gap: 0.5

# Как попадать крепления в таблицу, когда их несколько:
#   first_ok (по умолчанию) — первое прошедшее все проверки; если ни одно —
#     первое по списку, с его ошибками;
#   all — все крепления, по строке на каждое.
# Порядок записей в ring_mounts — приоритет: первым основное (крупнее болт,
# больше M крепл.), за ним запасные для тесных случаев.
mount_mode: first_ok

# Крепления венца (Д-16, Д-33): ключ — только имя (в скобках в колонке «Отверстия»
# и в поле mount; в ID не входит, состав отверстий входит). Каждая тройка
# (u, тело, генератор) считается со всеми креплениями в порядке записи.
# Одни и те же отверстия крепят редуктор в машине и базируют венец на оснастке
# станков (ЭЭС, фрезерование); штифты H7 задают угловое положение.
# Без штифтов (pins: 0) угловую фазу ряда держать нечем — только для проверки.
ring_mounts:
  M6x24P2: {bolt: M6, n: 22, pins: 2, pin_d: 6.0, head_margin: 0.5, web_min: 1.0, mu: 0.12, safety: 1.5}
  M5x12P2: {bolt: M5, n: 10, pins: 2, pin_d: 5.0, head_margin: 0.5, web_min: 1.0, mu: 0.12, safety: 1.5}
  M4x12P2:
    bolt: M4          # резьба, ключ таблицы fasteners; нет в таблице — ошибка
    n: 10              # число болтов; болт j на угле j·360°/n
    pins: 2           # штифты посередине промежутков j = round(i·n/pins); 0 — без штифтов
    pin_d: 4.0        # Ø штифта, мм
    head_margin: 0.5  # зазор от головки до впадин и до кромки, мм — входит в c
    web_min: 1.0      # перемычка между головками или головкой и штифтом, мм — шаг отверстий
    mu: 0.12          # трение в стыке венец/корпус (сталь, сухо: 0.1…0.15) — M крепл.
    safety: 1.5       # запас: M ≤ M крепл./safety — ограничивает M (Д-41)
  M3x12P2: {bolt: M3, n: 10, pins: 2, pin_d: 3.0, head_margin: 0.5, web_min: 1.0, mu: 0.12, safety: 1.5}
  M3x8P2: {bolt: M3, n: 6, pins: 2, pin_d: 3.0, head_margin: 0.5, web_min: 1.0, mu: 0.12, safety: 1.5}

# Таблица крепежа: d_clear — Ø отверстия под болт (ISO 273, средний ряд), мм;
# dk — Ø головки винта с цилиндрической головкой (ISO 4762), мм; F_M — ориентировочная
# сила затяжки, кН (кл. 8.8, μ резьбы 0.12, VDI 2230).
# Значения сверить со справочником; новый размер добавляется строкой, например
# M10: {d_clear: 11.0, dk: 16.0, F_M: 27.0}.
fasteners:
  M3: {d_clear: 3.4, dk: 5.5, F_M: 2.2}
  M4: {d_clear: 4.5, dk: 7.0, F_M: 4.1}
  M5: {d_clear: 5.5, dk: 8.5, F_M: 6.6}
  M6: {d_clear: 6.6, dk: 10.0, F_M: 9.3}
  M8: {d_clear: 9.0, dk: 13.0, F_M: 17.2}
===== END FILE =====
### Каталог тел качения (файл, который просил добавить заказчик)

===== FILE: specs/vendor_prices.yaml (строки 1–130) =====
# Покупные позиции — заполняет заказчик. Цена в currency; unit: pcs | m.
# Формат — YAML (Д-79). Тела и подшипники — instructions/INS-10_PTK_CALC.md,
# направляющие и цены — instructions/INS-20_CATALOG.md.

currency: RUB

# Наличие, цена, сроки: ключ — обозначение позиции; null — не заполнено.
items:
  HGH15CA: {unit: pcs, price: null, available: null, lead_days: null, supplier: "", date: ""}
  HGR15R: {unit: m, price: null, available: null, lead_days: null, supplier: "", date: ""}
  HGH20CA: {unit: pcs, price: null, available: null, lead_days: null, supplier: "", date: ""}
  HGR20R: {unit: m, price: null, available: null, lead_days: null, supplier: "", date: ""}
  HGW20CC: {unit: pcs, price: null, available: null, lead_days: null, supplier: "", date: ""}
  HGH25CA: {unit: pcs, price: null, available: null, lead_days: null, supplier: "", date: ""}
  HGR25R: {unit: m, price: null, available: null, lead_days: null, supplier: "", date: ""}
  R_D2x4: {unit: pcs, price: null, available: null, lead_days: null, supplier: "", date: ""}
  R_D3x8: {unit: pcs, price: null, available: null, lead_days: null, supplier: "", date: ""}
  B_D3: {unit: pcs, price: null, available: null, lead_days: null, supplier: "", date: ""}
  P3x8: {unit: pcs, price: null, available: null, lead_days: null, supplier: "", date: ""}

# Подшипник генератора ПТК (Д-40): d, D, B — мм; C, C0 — кН. Тела катятся по наружному
# кольцу, внутреннее сидит на эксцентрике. Берётся наименьший D ≥ 2·RΣ min − Dш
# с d ≥ shaft_d_min + 2·(aω + ecc_wall_min); нет подходящего — ошибка
# «нет подшипника генератора». Серия 618 — ориентировочно по каталогу SKF,
# сверить с каталогом поставщика (OQ-09).
# da — Ø заплечика вала под внутреннее кольцо (SKF, abutment da min; CP-90, OQ-31): упор .09 на ступице
# и проверка вырождения L4/L2 (Д-102 п. 4); 61806/61809/61810 сверены по SKF, прочие — d + 2 (r 0.3),
# сверить; нет поля — оценка d + 0.3·(D − d) в ptk_layout.
bearings:
  "61800": {d: 10.0, D: 19.0, B: 5.0, C: 1.72, C0: 0.83, da: 12.0}
  "61801": {d: 12.0, D: 21.0, B: 5.0, C: 1.74, C0: 0.915, da: 14.0}
  "61802": {d: 15.0, D: 24.0, B: 5.0, C: 1.9, C0: 1.1, da: 17.0}
  "61803": {d: 17.0, D: 26.0, B: 5.0, C: 2.03, C0: 1.27, da: 19.0}
  "61804": {d: 20.0, D: 32.0, B: 7.0, C: 4.03, C0: 2.32, da: 22.0}
  "61805": {d: 25.0, D: 37.0, B: 7.0, C: 4.36, C0: 2.6, da: 27.0}
  "61806": {d: 30.0, D: 42.0, B: 7.0, C: 4.49, C0: 2.9, da: 32.0}
  "61807": {d: 35.0, D: 47.0, B: 7.0, C: 4.75, C0: 3.2, da: 37.0}
  "61808": {d: 40.0, D: 52.0, B: 7.0, C: 4.94, C0: 3.45, da: 42.0}
  "61809": {d: 45.0, D: 58.0, B: 7.0, C: 6.63, C0: 6.1, da: 47.0}
  "61810": {d: 50.0, D: 65.0, B: 7.0, C: 6.76, C0: 6.8, da: 52.0}
  "61811": {d: 55.0, D: 72.0, B: 9.0, C: 9.04, C0: 8.8, da: 57.0}
  "61812": {d: 60.0, D: 78.0, B: 10.0, C: 11.9, C0: 11.4, da: 62.0}
  "61813": {d: 65.0, D: 85.0, B: 10.0, C: 12.1, C0: 12.5}
  "61814": {d: 70.0, D: 90.0, B: 10.0, C: 12.4, C0: 13.2}
  "61815": {d: 75.0, D: 95.0, B: 10.0, C: 12.5, C0: 10.8}
  "61816": {d: 80.0, D: 100.0, B: 10.0, C: 12.7, C0: 11.2}
  "61817": {d: 85.0, D: 110.0, B: 13.0, C: 19.5, C0: 16.6}
  "61818": {d: 90.0, D: 115.0, B: 13.0, C: 19.5, C0: 17.0}
  "61819": {d: 95.0, D: 120.0, B: 13.0, C: 19.9, C0: 18.8}
  "61820": {d: 100.0, D: 125.0, B: 13.0, C: 20.8, C0: 19.6}
  "61821": {d: 105.0, D: 130.0, B: 13.0, C: 20.8, C0: 19.6}
  "61822": {d: 110.0, D: 140.0, B: 16.0, C: 28.1, C0: 26.5}

# Тела качения ПТК (Д-37): type roller | ball; d = Dш, l — длина ролика
# (у шарика = Ø), мм; необязательные a_w (мм), wall_min (мм) переопределяют limits
# для этого тела. Ключ — обозначение тела: оно же в ID исполнения и в цене в items.
rollers:
  R_D8x16: {type: roller, d: 8.0, l: 16.0}
  R_D8x8: {type: roller, d: 8.0, l: 8.0}
  R_D7x20: {type: roller, d: 7.0, l: 20.0}
  R_D6x6: {type: roller, d: 6.0, l: 6.0}
  R_D5x8: {type: roller, d: 5.0, l: 8.0}
  R_D5x5: {type: roller, d: 5.0, l: 5.0}
  R_D3x8: {type: roller, d: 3.0, l: 8.0}
  B_D3: {type: ball, d: 3.0, l: 3.0}

# Штифты цилиндрические закалённые (Д-74): соединение .02–.12 (L2, L3) и штифты венца
# (ptk_input.yaml → ring_mounts.pin_d). ГОСТ 24296-93 (= ISO 8734): исполнение A — закалённые
# (550–650 HV30), B — цементированные; поле допуска d — m6. Обозначение «Штифт 3×8 ГОСТ 24296-93».
# Ключ P<d>; l — стандартные длины, мм (по ISO 8734; короткие длины для малых Ø — доп. таблица
# ГОСТ 24296 прил. 1, сверить с поставщиком — OQ-26). Цена и наличие — в items по ключу P<d>x<l>.
# Калькулятор (egm/ptk_join.py) берёт Ø из JOIN.pin_d только из этого списка, длину — наименьшую
# ≥ стенка .02 + 1.5·d; гнездо в .12 = l − стенка + 0.5. Нет раздела — длина не подбирается.
pins:
  P3: {d: 3.0, l: [8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30], std: "ГОСТ 24296-93", tol: m6}
  P4: {d: 4.0, l: [10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 35, 40], std: "ГОСТ 24296-93", tol: m6}
  P5: {d: 5.0, l: [12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 35, 40, 45, 50], std: "ГОСТ 24296-93", tol: m6}
  P6: {d: 6.0, l: [14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 35, 40, 45, 50, 55, 60], std: "ГОСТ 24296-93", tol: m6}

# Винты фланца выхода (CP-90 этап 2b-2, Д-104): d — номинал, d_tap — Ø под резьбу, мм;
# F_M — усилие затяжки, кН (кл. 8.8, μ резьбы 0.12 — ориентировочно, сверить, OQ-33).
screws:
  M3: {d: 3.0, d_tap: 2.5, F_M: 2.2}
  M4: {d: 4.0, d_tap: 3.3, F_M: 3.9}
  M5: {d: 5.0, d_tap: 4.2, F_M: 6.4}
  M6: {d: 6.0, d_tap: 5.0, F_M: 9.0}
  M8: {d: 8.0, d_tap: 6.8, F_M: 16.5}
  M10: {d: 10.0, d_tap: 8.5, F_M: 26.2}
  M12: {d: 12.0, d_tap: 10.2, F_M: 38.3}
# Кольца стопорные: rings_ext — ГОСТ 13942-86 (вал = d .09), rings_int — ГОСТ 13943-86 (отверстие = D .09);
# s — толщина кольца, m — ширина канавки H13, d2 — Ø канавки (расточка в отверстии, НЕ Ø кольца свободного), мм;
# канавки и s — по тексту ГОСТ (opm.ru PDF) и справочнику mtk-fortuna (сверена с PDF: 78→2.0, 102→2.5);
# m: 40→1.9, 78→2.2, 102→2.8 — литерально из ГОСТ; остальное — в границах объединённых блоков m (m ≈ 1.1·s);
# сверить с каталогом поставщика (OQ-33).
rings_ext:
  "10": {s: 1, m: 1.2, d2: 9.5}
  "12": {s: 1, m: 1.2, d2: 11.3}
  "15": {s: 1, m: 1.2, d2: 14.1}
  "17": {s: 1.2, m: 1.4, d2: 16}
  "20": {s: 1.2, m: 1.4, d2: 18.6}
  "25": {s: 1.2, m: 1.4, d2: 23.5}
  "30": {s: 1.2, m: 1.4, d2: 28.5}
  "35": {s: 1.7, m: 1.9, d2: 33}
  "40": {s: 1.7, m: 1.9, d2: 37.5}
  "45": {s: 1.7, m: 1.9, d2: 42.5}
  "50": {s: 2, m: 2.2, d2: 47}
  "55": {s: 2, m: 2.2, d2: 52}
  "60": {s: 2, m: 2.2, d2: 57}
  "65": {s: 2.5, m: 2.8, d2: 62}
  "70": {s: 2.5, m: 2.8, d2: 67}
  "75": {s: 2.5, m: 2.8, d2: 72}
  "80": {s: 2.5, m: 2.8, d2: 76.5}
rings_int:
  "19": {s: 1, m: 1.1, d2: 20.2}
  "21": {s: 1, m: 1.1, d2: 22.4}
  "24": {s: 1.2, m: 1.3, d2: 25.5}
  "26": {s: 1.2, m: 1.3, d2: 27.5}
  "32": {s: 1.2, m: 1.3, d2: 33.8}
  "37": {s: 1.7, m: 1.9, d2: 39}
  "42": {s: 1.7, m: 1.9, d2: 44.5}
  "47": {s: 1.7, m: 1.9, d2: 49.5}
  "52": {s: 1.7, m: 1.9, d2: 55}
  "58": {s: 1.7, m: 1.9, d2: 61}
  "65": {s: 1.7, m: 1.9, d2: 68}
  "72": {s: 1.7, m: 1.9, d2: 75}
  "78": {s: 2, m: 2.2, d2: 81}
  "85": {s: 2, m: 2.2, d2: 88.5}
  "90": {s: 2, m: 2.2, d2: 93.5}
  "95": {s: 2, m: 2.2, d2: 98.5}
  "105": {s: 2.5, m: 2.8, d2: 109}
===== END FILE =====

## Расчётная записка и спецификации

===== FILE: specs/SPEC-10_PTK_CALC.md (строки 1–914) =====
# SPEC-10 — Расчёт редуктора ПТК (code-first, НЕ ПРАВИТЬ РУКАМИ)

Сгенерировано `main.py` (`egm/ptk.py`, уровень 1) из `specs/ptk_input.yaml` и тел
качения `specs/vendor_prices.yaml` → `rollers`. Схема — Д-08, Д-11; отверстия венца —
Д-16. Как задавать параметры — `instructions/INS-10_PTK_CALC.md`.
Момент M — допускаемый по контакту Герца, статике подшипника генератора и креплению венца (Д-41); трение (11) и ресурс не учтены (OQ-08).
Генератор — `limits.gen_types` (Д-42): `bearing` — тела на наружном кольце подшипника, `eccentric` — прямо на эксцентрике. Предел D — `limits.d_out_max`, `null` — без предела (Д-43).

## Входные параметры прогона

Заданы целиком в ручном конфиге `specs/ptk_input.yaml` (Д-79): каждый параметр — с
описанием в комментарии рядом; крепления венца — `ring_mounts`, крепёж — `fasteners`,
отбор креплений в таблицу — `mount_mode`. Логика и формулы параметров —
`instructions/INS-10_PTK_CALC.md`; дубликат конфига здесь не приводится.

## Результаты

| ID | u | Тело | $D_\text{ш}$ | $D_\text{ш}$ max | n | z | $a_\omega$ | Генератор | $D_\text{г}$ | $D_\text{В}$ | α max, ° | Отверстия | Вар. венца | $D_\text{отв}$ | D | B | M, Н·м (огр.) | M крепл., Н·м | Статус |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PTK-010-R8X16-10M5P2-8B0907 | 10 | R_D8x16 | 8.0 | 20.9 | 10 | 11 | 1.6 | 61807 | 47.0 | 66.2 | 32.7 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 79.7 | 94.0 | 69.0 | 204.5 (подшипник) | 315.6 | OK |
| PTK-010-R8X16-10M5P2-8F60AF | 10 | R_D8x16 | 8.0 | 21.32 | 10 | 11 | 1.6 | эксцентрик | 45.7 | 64.9 | 33.3 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 78.4 | 92.0 | 69.0 | 207 (крепление) | 310.5 | OK (Т4) |
| PTK-010-R8X8-10M5P2-070C3C | 10 | R_D8x8 | 8.0 | 20.9 | 10 | 11 | 1.6 | 61807 | 47.0 | 66.2 | 32.7 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 79.7 | 94.0 | 37.0 | 204.5 (подшипник) | 315.6 | OK |
| PTK-010-R8X8-10M5P2-FF6078 | 10 | R_D8x8 | 8.0 | 21.32 | 10 | 11 | 1.6 | эксцентрик | 45.7 | 64.9 | 33.3 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 78.4 | 92.0 | 37.0 | 207 (крепление) | 310.5 | OK (Т4) |
| PTK-010-R7X20-10M5P2-7D60D6 | 10 | R_D7x20 | 7.0 | 20.59 | 10 | 11 | 1.4 | 61806 | 42.0 | 58.8 | 32.2 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 72.3 | 86.0 | 85.0 | 162.2 (подшипник) | 286.3 | OK |
| PTK-010-R7X20-10M5P2-2EA179 | 10 | R_D7x20 | 7.0 | 21.32 | 10 | 11 | 1.4 | эксцентрик | 40.0 | 56.8 | 33.3 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 70.3 | 84.0 | 85.0 | 185.6 (крепление) | 278.4 | OK (Т4) |
| PTK-010-R6X6-10M5P2-B73626 | 10 | R_D6x6 | 6.0 | 20.19 | 10 | 11 | 1.2 | 61805 | 37.0 | 51.4 | 31.6 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 64.9 | 79.0 | 33.0 | 124.7 (подшипник) | 257.0 | OK |
| PTK-010-R6X6-10M5P2-8AD44D | 10 | R_D6x6 | 6.0 | 21.31 | 10 | 11 | 1.2 | эксцентрик | 34.3 | 48.7 | 33.3 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 62.2 | 76.0 | 29.0 | 164.2 (крепление) | 246.3 | OK (Т4) |
| PTK-010-R5X8-10M5P2-2ECBA4 | 10 | R_D5x8 | 5.0 | 19.65 | 10 | 11 | 1.0 | 61804 | 32.0 | 44.0 | 30.8 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 57.5 | 71.0 | 37.0 | 92.7 (подшипник) | 227.7 | OK |
| PTK-010-R5X8-10M5P2-D97113 | 10 | R_D5x8 | 5.0 | 21.25 | 10 | 11 | 1.0 | эксцентрик | 28.7 | 40.7 | 33.2 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 54.2 | 68.0 | 37.0 | 143.1 (крепление) | 214.6 | OK (Т4) |
| PTK-010-R5X5-10M5P2-979E07 | 10 | R_D5x5 | 5.0 | 19.65 | 10 | 11 | 1.0 | 61804 | 32.0 | 44.0 | 30.8 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 57.5 | 71.0 | 33.0 | 92.7 (подшипник) | 227.7 | OK |
| PTK-010-R5X5-10M5P2-FDAB21 | 10 | R_D5x5 | 5.0 | 21.25 | 10 | 11 | 1.0 | эксцентрик | 28.7 | 40.7 | 33.2 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 54.2 | 68.0 | 25.0 | 143.1 (крепление) | 214.6 | OK (Т4) |
| PTK-010-R3X8-10M3P2-A16061 | 10 | R_D3x8 | 3.0 | 20.29 | 10 | 11 | 0.6 | 61800 | 19.0 | 26.2 | 31.0 | 10×M3+2шт Ø3 (M3x12P2) | 2 | 37.6 | 49.0 | 37.0 | 19.9 (подшипник) | 49.6 | OK |
| PTK-010-R3X8-10M3P2-1A947D | 10 | R_D3x8 | 3.0 | 21.69 | 10 | 11 | 0.6 | эксцентрик | 17.3 | 24.5 | 33.1 | 10×M3+2шт Ø3 (M3x12P2) | 2 | 35.9 | 48.0 | 37.0 | 31.6 (крепление) | 47.4 | OK (Т4) |
| PTK-010-B3-10M3P2-C587B2 | 10 | B_D3 | 3.0 | 21.69 | 10 | 11 | 0.6 | эксцентрик | 17.3 | 24.5 | 33.1 | 10×M3+2шт Ø3 (M3x12P2) | 2 | 35.9 | 48.0 | 17.0 | 1.2 (контакт) | 47.4 | OK (Т2, Т3, Т4) |
| PTK-016-R8X16-10M5P2-079658 | 16 | R_D8x16 | 8.0 | 14.23 | 16 | 17 | 1.6 | 61812 | 78.0 | 97.2 | 32.3 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 110.7 | 125.0 | 69.0 | 292.3 (крепление) | 438.4 | OK |
| PTK-016-R8X16-10M5P2-EBEF90 | 16 | R_D8x16 | 8.0 | 14.5 | 16 | 17 | 1.6 | эксцентрик | 76.2 | 95.4 | 32.9 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 108.9 | 123.0 | 69.0 | 287.5 (крепление) | 431.2 | OK (Т4) |
| PTK-016-R8X8-10M5P2-519C3A | 16 | R_D8x8 | 8.0 | 14.23 | 16 | 17 | 1.6 | 61812 | 78.0 | 97.2 | 32.3 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 110.7 | 125.0 | 45.0 | 292.3 (крепление) | 438.4 | OK |
| PTK-016-R8X8-10M5P2-999A95 | 16 | R_D8x8 | 8.0 | 14.5 | 16 | 17 | 1.6 | эксцентрик | 76.2 | 95.4 | 32.9 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 108.9 | 123.0 | 37.0 | 287.5 (крепление) | 431.2 | OK (Т4) |
| PTK-016-R7X20-10M5P2-A6FA18 | 16 | R_D7x20 | 7.0 | 13.63 | 16 | 17 | 1.4 | 61811 | 72.0 | 88.8 | 31.1 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 102.3 | 116.0 | 85.0 | 270.1 (крепление) | 405.1 | OK |
| PTK-016-R7X20-10M5P2-B6A6DE | 16 | R_D7x20 | 7.0 | 14.5 | 16 | 17 | 1.4 | эксцентрик | 66.7 | 83.5 | 32.9 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 97.0 | 111.0 | 85.0 | 256.1 (крепление) | 384.1 | OK (Т4) |
| PTK-016-R6X6-10M5P2-C54A11 | 16 | R_D6x6 | 6.0 | 14.33 | 16 | 17 | 1.2 | 61809 | 58.0 | 72.4 | 32.5 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 85.9 | 100.0 | 33.0 | 226.8 (крепление) | 340.2 | OK |
| PTK-016-R6X6-10M5P2-1E58F3 | 16 | R_D6x6 | 6.0 | 14.47 | 16 | 17 | 1.2 | эксцентрик | 57.3 | 71.7 | 32.8 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 85.2 | 99.0 | 29.0 | 224.9 (крепление) | 337.4 | OK (Т4) |
| PTK-016-R5X8-10M5P2-66659B | 16 | R_D5x8 | 5.0 | 13.51 | 16 | 17 | 1.0 | 61808 | 52.0 | 64.0 | 30.8 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 77.5 | 91.0 | 37.0 | 204.6 (крепление) | 306.9 | OK |
| PTK-016-R5X8-10M5P2-424AEF | 16 | R_D5x8 | 5.0 | 14.46 | 16 | 17 | 1.0 | эксцентрик | 47.8 | 59.8 | 32.8 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 73.3 | 87.0 | 37.0 | 193.5 (крепление) | 290.3 | OK (Т4) |
| PTK-016-R5X5-10M5P2-96A041 | 16 | R_D5x5 | 5.0 | 13.51 | 16 | 17 | 1.0 | 61808 | 52.0 | 64.0 | 30.8 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 77.5 | 91.0 | 33.0 | 204.6 (крепление) | 306.9 | OK |
| PTK-016-R5X5-10M5P2-303BBF | 16 | R_D5x5 | 5.0 | 14.46 | 16 | 17 | 1.0 | эксцентрик | 47.8 | 59.8 | 32.8 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 73.3 | 87.0 | 25.0 | 193.5 (крепление) | 290.3 | OK (Т4) |
| PTK-016-R3X8-10M5P2-7841A0 | 16 | R_D3x8 | 3.0 | 13.23 | 16 | 17 | 0.6 | 61804 | 32.0 | 39.2 | 30.3 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 52.7 | 67.0 | 37.0 | 89.1 (подшипник) | 208.7 | OK |
| PTK-016-R3X8-10M5P2-4F895B | 16 | R_D3x8 | 3.0 | 14.37 | 16 | 17 | 0.6 | эксцентрик | 28.9 | 36.1 | 32.6 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 49.6 | 64.0 | 37.0 | 130.9 (крепление) | 196.4 | OK (Т4) |
| PTK-016-B3-10M5P2-40D6F0 | 16 | B_D3 | 3.0 | 14.37 | 16 | 17 | 0.6 | эксцентрик | 28.9 | 36.1 | 32.6 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 49.6 | 64.0 | 17.0 | 3.1 (контакт) | 196.4 | OK (Т2, Т3, Т4) |
| PTK-020-R8X16-22M6P2-4A32DD | 20 | R_D8x16 | 8.0 | 11.46 | 20 | 21 | 1.6 | 61816 | 100.0 | 119.2 | 31.9 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 133.8 | 149.0 | 69.0 | 1095 (крепление) | 1642.5 | OK |
| PTK-020-R8X16-22M6P2-0377C3 | 20 | R_D8x16 | 8.0 | 11.8 | 20 | 21 | 1.6 | эксцентрик | 96.5 | 115.7 | 32.8 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 130.3 | 145.0 | 69.0 | 1066.4 (крепление) | 1599.6 | OK (Т4) |
| PTK-020-R8X8-22M6P2-656315 | 20 | R_D8x8 | 8.0 | 11.46 | 20 | 21 | 1.6 | 61816 | 100.0 | 119.2 | 31.9 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 133.8 | 149.0 | 45.0 | 1095 (крепление) | 1642.5 | OK |
| PTK-020-R8X8-22M6P2-7C7CC0 | 20 | R_D8x8 | 8.0 | 11.8 | 20 | 21 | 1.6 | эксцентрик | 96.5 | 115.7 | 32.8 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 130.3 | 145.0 | 37.0 | 1066.4 (крепление) | 1599.6 | OK (Т4) |
| PTK-020-R7X20-10M5P2-388229 | 20 | R_D7x20 | 7.0 | 11.89 | 20 | 21 | 1.4 | 61813 | 85.0 | 101.8 | 32.6 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 115.3 | 129.0 | 85.0 | 304.4 (крепление) | 456.6 | OK |
| PTK-020-R7X20-10M5P2-EAC535 | 20 | R_D7x20 | 7.0 | 11.94 | 20 | 21 | 1.4 | эксцентрик | 84.6 | 101.4 | 32.7 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 114.9 | 129.0 | 85.0 | 303.3 (крепление) | 455.0 | OK (Т4) |
| PTK-020-R6X6-10M5P2-AFCBDF | 20 | R_D6x6 | 6.0 | 11.23 | 20 | 21 | 1.2 | 61812 | 78.0 | 92.4 | 31.0 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 105.9 | 120.0 | 45.0 | 279.6 (крепление) | 419.4 | OK |
| PTK-020-R6X6-10M5P2-CDD24C | 20 | R_D6x6 | 6.0 | 11.93 | 20 | 21 | 1.2 | эксцентрик | 72.6 | 87.0 | 32.7 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 100.5 | 114.0 | 29.0 | 265.3 (крепление) | 398.0 | OK (Т4) |
| PTK-020-R5X8-10M5P2-04E9EC | 20 | R_D5x8 | 5.0 | 11.23 | 20 | 21 | 1.0 | 61810 | 65.0 | 77.0 | 31.0 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 90.5 | 104.0 | 37.0 | 238.9 (крепление) | 358.4 | OK |
| PTK-020-R5X8-10M5P2-4FDD6C | 20 | R_D5x8 | 5.0 | 11.91 | 20 | 21 | 1.0 | эксцентрик | 60.6 | 72.6 | 32.6 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 86.1 | 100.0 | 37.0 | 227.3 (крепление) | 341.0 | OK (Т4) |
| PTK-020-R5X5-10M5P2-0A0407 | 20 | R_D5x5 | 5.0 | 11.23 | 20 | 21 | 1.0 | 61810 | 65.0 | 77.0 | 31.0 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 90.5 | 104.0 | 33.0 | 238.9 (крепление) | 358.4 | OK |
| PTK-020-R5X5-10M5P2-67323B | 20 | R_D5x5 | 5.0 | 11.91 | 20 | 21 | 1.0 | эксцентрик | 60.6 | 72.6 | 32.6 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 86.1 | 100.0 | 25.0 | 227.3 (крепление) | 341.0 | OK (Т4) |
| PTK-020-R3X8-10M5P2-DBE2F2 | 20 | R_D3x8 | 3.0 | 11.74 | 20 | 21 | 0.6 | 61805 | 37.0 | 44.2 | 32.2 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 57.7 | 72.0 | 37.0 | 124.8 (подшипник) | 228.5 | OK |
| PTK-020-R3X8-10M5P2-248D14 | 20 | R_D3x8 | 3.0 | 11.84 | 20 | 21 | 0.6 | эксцентрик | 36.6 | 43.8 | 32.5 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 57.3 | 71.0 | 37.0 | 151.3 (крепление) | 226.9 | OK (Т4) |
| PTK-020-B3-10M5P2-74A23C | 20 | B_D3 | 3.0 | 11.84 | 20 | 21 | 0.6 | эксцентрик | 36.6 | 43.8 | 32.5 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 57.3 | 71.0 | 17.0 | 4.8 (контакт) | 226.9 | OK (Т2, Т3, Т4) |
| PTK-025-R8X16-22M6P2-754C59 | 25 | R_D8x16 | 8.0 | 9.47 | 25 | 26 | 1.6 | 61820 | 125.0 | 144.2 | 32.0 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 158.8 | 174.0 | 69.0 | 1299.6 (крепление) | 1949.4 | OK |
| PTK-025-R8X16-22M6P2-0F2F2C | 25 | R_D8x16 | 8.0 | 9.67 | 25 | 26 | 1.6 | эксцентрик | 122.0 | 141.2 | 32.6 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 155.8 | 171.0 | 69.0 | 1275.1 (крепление) | 1912.6 | OK (Т4) |
| PTK-025-R8X8-22M6P2-2C1E5B | 25 | R_D8x8 | 8.0 | 9.47 | 25 | 26 | 1.6 | 61820 | 125.0 | 144.2 | 32.0 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 158.8 | 174.0 | 57.0 | 1299.6 (крепление) | 1949.4 | OK |
| PTK-025-R8X8-22M6P2-391A86 | 25 | R_D8x8 | 8.0 | 9.67 | 25 | 26 | 1.6 | эксцентрик | 122.0 | 141.2 | 32.6 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 155.8 | 171.0 | 37.0 | 1275.1 (крепление) | 1912.6 | OK (Т4) |
| PTK-025-R7X20-22M6P2-1327C5 | 25 | R_D7x20 | 7.0 | 9.42 | 25 | 26 | 1.4 | 61817 | 110.0 | 126.8 | 31.9 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 141.4 | 156.0 | 85.0 | 1157.2 (крепление) | 1735.8 | OK |
| PTK-025-R7X20-22M6P2-772B35 | 25 | R_D7x20 | 7.0 | 9.67 | 25 | 26 | 1.4 | эксцентрик | 106.8 | 123.6 | 32.6 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 138.2 | 153.0 | 85.0 | 1131 (крепление) | 1696.5 | OK (Т4) |
| PTK-025-R6X6-10M5P2-505845 | 25 | R_D6x6 | 6.0 | 9.48 | 25 | 26 | 1.2 | 61815 | 95.0 | 109.4 | 31.7 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 122.9 | 137.0 | 45.0 | 324.5 (крепление) | 486.7 | OK |
| PTK-025-R6X6-10M5P2-D85760 | 25 | R_D6x6 | 6.0 | 9.78 | 25 | 26 | 1.2 | эксцентрик | 91.7 | 106.1 | 32.6 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 119.6 | 134.0 | 29.0 | 315.7 (крепление) | 473.6 | OK (Т4) |
| PTK-025-R5X8-10M5P2-2182BD | 25 | R_D5x8 | 5.0 | 9.61 | 25 | 26 | 1.0 | 61812 | 78.0 | 90.0 | 32.1 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 103.5 | 117.0 | 45.0 | 273.3 (крепление) | 409.9 | OK |
| PTK-025-R5X8-10M5P2-E7AF17 | 25 | R_D5x8 | 5.0 | 9.76 | 25 | 26 | 1.0 | эксцентрик | 76.6 | 88.6 | 32.5 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 102.1 | 116.0 | 37.0 | 269.5 (крепление) | 404.3 | OK (Т4) |
| PTK-025-R5X5-10M5P2-01744D | 25 | R_D5x5 | 5.0 | 9.61 | 25 | 26 | 1.0 | 61812 | 78.0 | 90.0 | 32.1 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 103.5 | 117.0 | 45.0 | 273.3 (крепление) | 409.9 | OK |
| PTK-025-R5X5-10M5P2-AC2DD3 | 25 | R_D5x5 | 5.0 | 9.76 | 25 | 26 | 1.0 | эксцентрик | 76.6 | 88.6 | 32.5 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 102.1 | 116.0 | 25.0 | 269.5 (крепление) | 404.3 | OK (Т4) |
| PTK-025-R3X8-10M5P2-70E7B4 | 25 | R_D3x8 | 3.0 | 9.57 | 25 | 26 | 0.6 | 61807 | 47.0 | 54.2 | 32.0 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 67.7 | 82.0 | 37.0 | 178.7 (крепление) | 268.1 | OK |
| PTK-025-R3X8-10M5P2-A700AA | 25 | R_D3x8 | 3.0 | 9.7 | 25 | 26 | 0.6 | эксцентрик | 46.3 | 53.5 | 32.3 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 67.0 | 81.0 | 37.0 | 176.9 (крепление) | 265.3 | OK (Т4) |
| PTK-025-B3-10M5P2-7EC60B | 25 | B_D3 | 3.0 | 9.7 | 25 | 26 | 0.6 | эксцентрик | 46.3 | 53.5 | 32.3 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 67.0 | 81.0 | 17.0 | 7.5 (контакт) | 265.3 | OK (Т2, Т3, Т4) |
| PTK-032-R8X16-22M6P2-9E294B | 32 | R_D8x16 | 8.0 | 7.72 | 32 | 33 | 1.6 | — | 157.58 | 176.78 | 32.5 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 191.4 | 206.0 | 69.0 | — | 2349.6 | нет |
| PTK-032-R8X16-10M3P2-B06A75 | 32 | R_D8x16 | 8.0 | 8.01 | 32 | 33 | 1.6 | эксцентрик | 157.6 | 176.8 | 32.5 | 10×M3+2шт Ø3 (M3x12P2) | 2 | 188.2 | 200.0 | 69.0 | 165.6 (крепление) | 248.4 | OK (Т4) |
| PTK-032-R8X8-22M6P2-12A3E4 | 32 | R_D8x8 | 8.0 | 7.72 | 32 | 33 | 1.6 | — | 157.58 | 176.78 | 32.5 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 191.4 | 206.0 | 37.0 | — | 2349.6 | нет |
| PTK-032-R8X8-10M3P2-8F3875 | 32 | R_D8x8 | 8.0 | 8.01 | 32 | 33 | 1.6 | эксцентрик | 157.6 | 176.8 | 32.5 | 10×M3+2шт Ø3 (M3x12P2) | 2 | 188.2 | 200.0 | 37.0 | 165.6 (крепление) | 248.4 | OK (Т4) |
| PTK-032-R7X20-22M6P2-BAC1EE | 32 | R_D7x20 | 7.0 | 7.62 | 32 | 33 | 1.4 | 61822 | 140.0 | 156.8 | 32.2 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 171.4 | 186.0 | 85.0 | 1402.7 (крепление) | 2104.1 | OK |
| PTK-032-R7X20-22M6P2-1A4385 | 32 | R_D7x20 | 7.0 | 7.71 | 32 | 33 | 1.4 | эксцентрик | 138.1 | 154.9 | 32.5 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 169.5 | 185.0 | 85.0 | 1387.2 (крепление) | 2080.8 | OK (Т4) |
| PTK-032-R6X6-22M6P2-E942C3 | 32 | R_D6x6 | 6.0 | 7.62 | 32 | 33 | 1.2 | 61819 | 120.0 | 134.4 | 32.2 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 149.0 | 164.0 | 57.0 | 1219.4 (крепление) | 1829.1 | OK |
| PTK-032-R6X6-22M6P2-D4BE19 | 32 | R_D6x6 | 6.0 | 7.71 | 32 | 33 | 1.2 | эксцентрик | 118.5 | 132.9 | 32.5 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 147.5 | 163.0 | 29.0 | 1207.1 (крепление) | 1810.7 | OK (Т4) |
| PTK-032-R5X8-22M6P2-19B83D | 32 | R_D5x8 | 5.0 | 7.62 | 32 | 33 | 1.0 | 61816 | 100.0 | 112.0 | 32.2 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 126.6 | 142.0 | 45.0 | 1036.1 (крепление) | 1554.1 | OK |
| PTK-032-R5X8-10M5P2-2CBB5C | 32 | R_D5x8 | 5.0 | 7.79 | 32 | 33 | 1.0 | эксцентрик | 98.9 | 110.9 | 32.4 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 124.4 | 138.0 | 37.0 | 328.4 (крепление) | 492.6 | OK (Т4) |
| PTK-032-R5X5-22M6P2-793017 | 32 | R_D5x5 | 5.0 | 7.62 | 32 | 33 | 1.0 | 61816 | 100.0 | 112.0 | 32.2 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 126.6 | 142.0 | 45.0 | 1036.1 (крепление) | 1554.1 | OK |
| PTK-032-R5X5-10M5P2-3F07B6 | 32 | R_D5x5 | 5.0 | 7.79 | 32 | 33 | 1.0 | эксцентрик | 98.9 | 110.9 | 32.4 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 124.4 | 138.0 | 25.0 | 328.4 (крепление) | 492.6 | OK (Т4) |
| PTK-032-R3X8-10M5P2-1E1E34 | 32 | R_D3x8 | 3.0 | 7.18 | 32 | 33 | 0.6 | 61810 | 65.0 | 72.2 | 30.2 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 85.7 | 100.0 | 37.0 | 226.3 (крепление) | 339.4 | OK |
| PTK-032-R3X8-10M5P2-7AE1CB | 32 | R_D3x8 | 3.0 | 7.74 | 32 | 33 | 0.6 | эксцентрик | 59.8 | 67.0 | 32.2 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 80.5 | 94.0 | 37.0 | 212.5 (крепление) | 318.8 | OK (Т4) |
| PTK-032-B3-10M5P2-DEDB0E | 32 | B_D3 | 3.0 | 7.74 | 32 | 33 | 0.6 | эксцентрик | 59.8 | 67.0 | 32.2 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 80.5 | 94.0 | 17.0 | 12.3 (контакт) | 318.8 | OK (Т2, Т3, Т4) |
| PTK-040-R8X16-22M6P2-0C160E | 40 | R_D8x16 | 8.0 | 6.28 | 40 | 41 | 1.6 | — | 198.3 | 217.5 | 32.5 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 232.2 | 247.0 | 69.0 | — | 2850.5 | нет |
| PTK-040-R8X16-22M6P2-0343C4 | 40 | R_D8x16 | 8.0 | 6.27 | 40 | 41 | 1.6 | эксцентрик | 198.4 | 217.6 | 32.4 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 232.2 | 247.0 | 69.0 | — | 2850.5 | нет (Т4) |
| PTK-040-R8X8-22M6P2-95EB68 | 40 | R_D8x8 | 8.0 | 6.28 | 40 | 41 | 1.6 | — | 198.3 | 217.5 | 32.5 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 232.2 | 247.0 | 37.0 | — | 2850.5 | нет |
| PTK-040-R8X8-22M6P2-201151 | 40 | R_D8x8 | 8.0 | 6.27 | 40 | 41 | 1.6 | эксцентрик | 198.4 | 217.6 | 32.4 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 232.2 | 247.0 | 37.0 | — | 2850.5 | нет (Т4) |
| PTK-040-R7X20-22M6P2-76A018 | 40 | R_D7x20 | 7.0 | 6.27 | 40 | 41 | 1.4 | — | 173.67 | 190.47 | 32.4 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 205.1 | 220.0 | 85.0 | — | 2517.8 | нет |
| PTK-040-R7X20-22M6P2-F1EFD7 | 40 | R_D7x20 | 7.0 | 6.27 | 40 | 41 | 1.4 | эксцентрик | 173.7 | 190.5 | 32.4 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 205.1 | 220.0 | 85.0 | — | 2517.8 | нет (Т4) |
| PTK-040-R6X6-22M6P2-650479 | 40 | R_D6x6 | 6.0 | 6.27 | 40 | 41 | 1.2 | — | 149.04 | 163.44 | 32.4 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 178.1 | 193.0 | 29.0 | — | 2186.4 | нет |
| PTK-040-R6X6-22M6P2-E2D3CD | 40 | R_D6x6 | 6.0 | 6.26 | 40 | 41 | 1.2 | эксцентрик | 149.1 | 163.5 | 32.4 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 178.1 | 193.0 | 29.0 | 1457.6 (крепление) | 2186.4 | OK (Т4) |
| PTK-040-R5X8-22M6P2-A1C64A | 40 | R_D5x8 | 5.0 | 6.23 | 40 | 41 | 1.0 | 61820 | 125.0 | 137.0 | 32.2 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 151.6 | 167.0 | 57.0 | 1240.7 (крепление) | 1861.0 | OK |
| PTK-040-R5X8-22M6P2-5D1664 | 40 | R_D5x8 | 5.0 | 6.25 | 40 | 41 | 1.0 | эксцентрик | 124.5 | 136.5 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 151.1 | 166.0 | 37.0 | 1236.6 (крепление) | 1854.9 | OK (Т4) |
| PTK-040-R5X5-22M6P2-3F1C4A | 40 | R_D5x5 | 5.0 | 6.23 | 40 | 41 | 1.0 | 61820 | 125.0 | 137.0 | 32.2 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 151.6 | 167.0 | 57.0 | 1240.7 (крепление) | 1861.0 | OK |
| PTK-040-R5X5-22M6P2-2DF37C | 40 | R_D5x5 | 5.0 | 6.25 | 40 | 41 | 1.0 | эксцентрик | 124.5 | 136.5 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 151.1 | 166.0 | 25.0 | 1236.6 (крепление) | 1854.9 | OK (Т4) |
| PTK-040-R3X8-10M5P2-C1B79F | 40 | R_D3x8 | 3.0 | 6.09 | 40 | 41 | 0.6 | 61812 | 78.0 | 85.2 | 31.3 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 98.7 | 113.0 | 45.0 | 260.6 (крепление) | 390.9 | OK |
| PTK-040-R3X8-10M5P2-4EE27D | 40 | R_D3x8 | 3.0 | 6.29 | 40 | 41 | 0.6 | эксцентрик | 75.2 | 82.4 | 32.2 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 95.9 | 110.0 | 37.0 | 253.2 (крепление) | 379.8 | OK (Т4) |
| PTK-040-B3-10M5P2-80BC3D | 40 | B_D3 | 3.0 | 6.29 | 40 | 41 | 0.6 | эксцентрик | 75.2 | 82.4 | 32.2 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 95.9 | 110.0 | 17.0 | 19.2 (контакт) | 379.8 | OK (Т2, Т3, Т4) |
| PTK-050-R8X16-22M6P2-986467 | 50 | R_D8x16 | 8.0 | 5.09 | 50 | 51 | 1.6 | — | 249.21 | 268.41 | 32.4 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 283.1 | 298.0 | 69.0 | — | 3475.3 | нет |
| PTK-050-R8X16-22M6P2-0C64BB | 50 | R_D8x16 | 8.0 | 5.08 | 50 | 51 | 1.6 | эксцентрик | 249.3 | 268.5 | 32.4 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 283.1 | 298.0 | 69.0 | — | 3475.3 | нет (Т4) |
| PTK-050-R8X8-22M6P2-84F4C5 | 50 | R_D8x8 | 8.0 | 5.09 | 50 | 51 | 1.6 | — | 249.21 | 268.41 | 32.4 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 283.1 | 298.0 | 37.0 | — | 3475.3 | нет |
| PTK-050-R8X8-22M6P2-ED6334 | 50 | R_D8x8 | 8.0 | 5.08 | 50 | 51 | 1.6 | эксцентрик | 249.3 | 268.5 | 32.4 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 283.1 | 298.0 | 37.0 | — | 3475.3 | нет (Т4) |
| PTK-050-R7X20-22M6P2-CE97E4 | 50 | R_D7x20 | 7.0 | 5.08 | 50 | 51 | 1.4 | — | 218.25 | 235.05 | 32.4 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 249.7 | 265.0 | 85.0 | — | 3065.3 | нет |
| PTK-050-R7X20-22M6P2-DD4090 | 50 | R_D7x20 | 7.0 | 5.08 | 50 | 51 | 1.4 | эксцентрик | 218.3 | 235.1 | 32.4 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 249.7 | 265.0 | 85.0 | — | 3065.3 | нет (Т4) |
| PTK-050-R6X6-22M6P2-4DCB40 | 50 | R_D6x6 | 6.0 | 5.08 | 50 | 51 | 1.2 | — | 187.3 | 201.7 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 216.3 | 231.0 | 29.0 | — | 2655.3 | нет |
| PTK-050-R6X6-22M6P2-3E50C6 | 50 | R_D6x6 | 6.0 | 5.08 | 50 | 51 | 1.2 | эксцентрик | 187.3 | 201.7 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 216.3 | 231.0 | 29.0 | — | 2655.3 | нет (Т4) |
| PTK-050-R5X8-22M6P2-1D56A2 | 50 | R_D5x8 | 5.0 | 5.07 | 50 | 51 | 1.0 | — | 156.34 | 168.34 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 183.0 | 198.0 | 37.0 | — | 2246.5 | нет |
| PTK-050-R5X8-22M6P2-7B07E5 | 50 | R_D5x8 | 5.0 | 5.07 | 50 | 51 | 1.0 | эксцентрик | 156.4 | 168.4 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 183.0 | 198.0 | 37.0 | 1497.7 (крепление) | 2246.5 | OK (Т4) |
| PTK-050-R5X5-22M6P2-20A347 | 50 | R_D5x5 | 5.0 | 5.07 | 50 | 51 | 1.0 | — | 156.34 | 168.34 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 183.0 | 198.0 | 25.0 | — | 2246.5 | нет |
| PTK-050-R5X5-22M6P2-1AD71F | 50 | R_D5x5 | 5.0 | 5.07 | 50 | 51 | 1.0 | эксцентрик | 156.4 | 168.4 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 183.0 | 198.0 | 25.0 | 1497.7 (крепление) | 2246.5 | OK (Т4) |
| PTK-050-R3X8-10M5P2-E6B80C | 50 | R_D3x8 | 3.0 | 5.07 | 50 | 51 | 0.6 | 61815 | 95.0 | 102.2 | 32.0 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 115.7 | 130.0 | 45.0 | 305.5 (крепление) | 458.2 | OK |
| PTK-050-R3X8-10M5P2-4AFC2C | 50 | R_D3x8 | 3.0 | 5.1 | 50 | 51 | 0.6 | эксцентрик | 94.5 | 101.7 | 32.1 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 115.2 | 129.0 | 37.0 | 304.1 (крепление) | 456.2 | OK (Т4) |
| PTK-050-B3-10M5P2-7415AD | 50 | B_D3 | 3.0 | 5.1 | 50 | 51 | 0.6 | эксцентрик | 94.5 | 101.7 | 32.1 | 10×M5+2шт Ø5 (M5x12P2) | 2 | 115.2 | 129.0 | 17.0 | 30 (контакт) | 456.2 | OK (Т2, Т3, Т4) |
| PTK-063-R8X16-22M6P2-DDA520 | 63 | R_D8x16 | 8.0 | 4.08 | 63 | 64 | 1.6 | — | 315.39 | 334.59 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 1 | 349.2 | 364.0 | 69.0 | — | 4286.8 | нет |
| PTK-063-R8X16-22M6P2-DA30EE | 63 | R_D8x16 | 8.0 | 4.08 | 63 | 64 | 1.6 | эксцентрик | 315.4 | 334.6 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 1 | 349.2 | 364.0 | 69.0 | — | 4286.8 | нет (Т4) |
| PTK-063-R8X8-22M6P2-C47FC5 | 63 | R_D8x8 | 8.0 | 4.08 | 63 | 64 | 1.6 | — | 315.39 | 334.59 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 1 | 349.2 | 364.0 | 37.0 | — | 4286.8 | нет |
| PTK-063-R8X8-22M6P2-D0C75B | 63 | R_D8x8 | 8.0 | 4.08 | 63 | 64 | 1.6 | эксцентрик | 315.4 | 334.6 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 1 | 349.2 | 364.0 | 37.0 | — | 4286.8 | нет (Т4) |
| PTK-063-R7X20-22M6P2-87BC1B | 63 | R_D7x20 | 7.0 | 4.08 | 63 | 64 | 1.4 | — | 276.22 | 293.02 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 1 | 307.7 | 323.0 | 85.0 | — | 3777.3 | нет |
| PTK-063-R7X20-22M6P2-E7C184 | 63 | R_D7x20 | 7.0 | 4.07 | 63 | 64 | 1.4 | эксцентрик | 276.3 | 293.1 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 1 | 307.7 | 323.0 | 85.0 | — | 3777.3 | нет (Т4) |
| PTK-063-R6X6-22M6P2-F361EE | 63 | R_D6x6 | 6.0 | 4.07 | 63 | 64 | 1.2 | — | 237.04 | 251.44 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 1 | 266.1 | 281.0 | 29.0 | — | 3266.6 | нет |
| PTK-063-R6X6-22M6P2-7D2FF2 | 63 | R_D6x6 | 6.0 | 4.07 | 63 | 64 | 1.2 | эксцентрик | 237.1 | 251.5 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 1 | 266.1 | 281.0 | 29.0 | — | 3266.6 | нет (Т4) |
| PTK-063-R5X8-22M6P2-ECA0D7 | 63 | R_D5x8 | 5.0 | 4.06 | 63 | 64 | 1.0 | — | 197.86 | 209.86 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 1 | 224.5 | 240.0 | 37.0 | — | 2756.0 | нет |
| PTK-063-R5X8-22M6P2-51F025 | 63 | R_D5x8 | 5.0 | 4.06 | 63 | 64 | 1.0 | эксцентрик | 197.9 | 209.9 | 32.2 | 22×M6+2шт Ø6 (M6x24P2) | 1 | 224.5 | 240.0 | 37.0 | — | 2756.0 | нет (Т4) |
| PTK-063-R5X5-22M6P2-A81518 | 63 | R_D5x5 | 5.0 | 4.06 | 63 | 64 | 1.0 | — | 197.86 | 209.86 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 1 | 224.5 | 240.0 | 25.0 | — | 2756.0 | нет |
| PTK-063-R5X5-22M6P2-64F71F | 63 | R_D5x5 | 5.0 | 4.06 | 63 | 64 | 1.0 | эксцентрик | 197.9 | 209.9 | 32.2 | 22×M6+2шт Ø6 (M6x24P2) | 1 | 224.5 | 240.0 | 25.0 | — | 2756.0 | нет (Т4) |
| PTK-063-R3X8-22M6P2-BDBB72 | 63 | R_D3x8 | 3.0 | 4.02 | 63 | 64 | 0.6 | 61819 | 120.0 | 127.2 | 32.0 | 22×M6+2шт Ø6 (M6x24P2) | 1 | 141.8 | 157.0 | 57.0 | 1160.5 (крепление) | 1740.7 | OK |
| PTK-063-R3X8-22M6P2-2D6433 | 63 | R_D3x8 | 3.0 | 4.04 | 63 | 64 | 0.6 | эксцентрик | 119.5 | 126.7 | 32.1 | 22×M6+2шт Ø6 (M6x24P2) | 1 | 141.3 | 156.0 | 37.0 | 1156.4 (крепление) | 1734.6 | OK (Т4) |
| PTK-063-B3-22M6P2-240036 | 63 | B_D3 | 3.0 | 4.04 | 63 | 64 | 0.6 | эксцентрик | 119.5 | 126.7 | 32.1 | 22×M6+2шт Ø6 (M6x24P2) | 1 | 141.3 | 156.0 | 17.0 | 47.6 (контакт) | 1734.6 | OK (Т2, Т3, Т4) |
| PTK-080-R8X16-22M6P2-6A3AD7 | 80 | R_D8x16 | 8.0 | 3.24 | 80 | 81 | 1.6 | — | 401.94 | 421.14 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 435.8 | 451.0 | 69.0 | — | 5349.9 | нет |
| PTK-080-R8X16-22M6P2-075C32 | 80 | R_D8x16 | 8.0 | 3.24 | 80 | 81 | 1.6 | эксцентрик | 402.0 | 421.2 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 435.8 | 451.0 | 69.0 | — | 5349.9 | нет (Т4) |
| PTK-080-R8X8-22M6P2-8B2D21 | 80 | R_D8x8 | 8.0 | 3.24 | 80 | 81 | 1.6 | — | 401.94 | 421.14 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 435.8 | 451.0 | 37.0 | — | 5349.9 | нет |
| PTK-080-R8X8-22M6P2-AEA3B3 | 80 | R_D8x8 | 8.0 | 3.24 | 80 | 81 | 1.6 | эксцентрик | 402.0 | 421.2 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 435.8 | 451.0 | 37.0 | — | 5349.9 | нет (Т4) |
| PTK-080-R7X20-22M6P2-7CFD36 | 80 | R_D7x20 | 7.0 | 3.24 | 80 | 81 | 1.4 | — | 352.01 | 368.81 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 383.5 | 399.0 | 85.0 | — | 4707.8 | нет |
| PTK-080-R7X20-22M6P2-CAEAE8 | 80 | R_D7x20 | 7.0 | 3.24 | 80 | 81 | 1.4 | эксцентрик | 352.1 | 368.9 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 383.5 | 399.0 | 85.0 | — | 4707.8 | нет (Т4) |
| PTK-080-R6X6-22M6P2-64AA97 | 80 | R_D6x6 | 6.0 | 3.23 | 80 | 81 | 1.2 | — | 302.08 | 316.48 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 331.1 | 346.0 | 29.0 | — | 4064.6 | нет |
| PTK-080-R6X6-22M6P2-11A46B | 80 | R_D6x6 | 6.0 | 3.23 | 80 | 81 | 1.2 | эксцентрик | 302.1 | 316.5 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 331.1 | 346.0 | 29.0 | — | 4064.6 | нет (Т4) |
| PTK-080-R5X8-22M6P2-81E92A | 80 | R_D5x8 | 5.0 | 3.23 | 80 | 81 | 1.0 | — | 252.15 | 264.15 | 32.2 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 278.8 | 294.0 | 37.0 | — | 3422.5 | нет |
| PTK-080-R5X8-22M6P2-C662FE | 80 | R_D5x8 | 5.0 | 3.23 | 80 | 81 | 1.0 | эксцентрик | 252.2 | 264.2 | 32.2 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 278.8 | 294.0 | 37.0 | — | 3422.5 | нет (Т4) |
| PTK-080-R5X5-22M6P2-7AB35A | 80 | R_D5x5 | 5.0 | 3.23 | 80 | 81 | 1.0 | — | 252.15 | 264.15 | 32.2 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 278.8 | 294.0 | 25.0 | — | 3422.5 | нет |
| PTK-080-R5X5-22M6P2-15CFA2 | 80 | R_D5x5 | 5.0 | 3.23 | 80 | 81 | 1.0 | эксцентрик | 252.2 | 264.2 | 32.2 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 278.8 | 294.0 | 25.0 | — | 3422.5 | нет (Т4) |
| PTK-080-R3X8-22M6P2-A0F08F | 80 | R_D3x8 | 3.0 | 3.21 | 80 | 81 | 0.6 | — | 152.28 | 159.48 | 32.0 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 174.1 | 189.0 | 37.0 | — | 2137.3 | нет |
| PTK-080-R3X8-22M6P2-5063C8 | 80 | R_D3x8 | 3.0 | 3.21 | 80 | 81 | 0.6 | эксцентрик | 152.3 | 159.5 | 32.0 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 174.1 | 189.0 | 37.0 | 1424.9 (крепление) | 2137.3 | OK (Т4) |
| PTK-080-B3-22M6P2-F9ADAB | 80 | B_D3 | 3.0 | 3.21 | 80 | 81 | 0.6 | эксцентрик | 152.3 | 159.5 | 32.0 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 174.1 | 189.0 | 17.0 | 76.8 (контакт) | 2137.3 | OK (Т2, Т3, Т4) |
| PTK-100-R8X16-22M6P2-AE37A5 | 100 | R_D8x16 | 8.0 | 2.61 | 100 | 101 | 1.6 | — | 503.76 | 522.96 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 537.6 | 553.0 | 69.0 | — | 6599.6 | нет |
| PTK-100-R8X16-22M6P2-69977F | 100 | R_D8x16 | 8.0 | 2.61 | 100 | 101 | 1.6 | эксцентрик | 503.8 | 523.0 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 537.6 | 553.0 | 69.0 | — | 6599.6 | нет (Т4) |
| PTK-100-R8X8-22M6P2-86E7F0 | 100 | R_D8x8 | 8.0 | 2.61 | 100 | 101 | 1.6 | — | 503.76 | 522.96 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 537.6 | 553.0 | 37.0 | — | 6599.6 | нет |
| PTK-100-R8X8-22M6P2-4C9144 | 100 | R_D8x8 | 8.0 | 2.61 | 100 | 101 | 1.6 | эксцентрик | 503.8 | 523.0 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 537.6 | 553.0 | 37.0 | — | 6599.6 | нет (Т4) |
| PTK-100-R7X20-22M6P2-0B73A4 | 100 | R_D7x20 | 7.0 | 2.61 | 100 | 101 | 1.4 | — | 441.18 | 457.98 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 472.6 | 488.0 | 85.0 | — | 5801.6 | нет |
| PTK-100-R7X20-22M6P2-A8E08E | 100 | R_D7x20 | 7.0 | 2.61 | 100 | 101 | 1.4 | эксцентрик | 441.2 | 458.0 | 32.3 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 472.6 | 488.0 | 85.0 | — | 5801.6 | нет (Т4) |
| PTK-100-R6X6-22M6P2-0A6BA9 | 100 | R_D6x6 | 6.0 | 2.6 | 100 | 101 | 1.2 | — | 378.6 | 393.0 | 32.2 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 407.7 | 423.0 | 29.0 | — | 5004.9 | нет |
| PTK-100-R6X6-22M6P2-0E270A | 100 | R_D6x6 | 6.0 | 2.6 | 100 | 101 | 1.2 | эксцентрик | 378.7 | 393.1 | 32.2 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 407.7 | 423.0 | 29.0 | — | 5004.9 | нет (Т4) |
| PTK-100-R5X8-22M6P2-12DB1E | 100 | R_D5x8 | 5.0 | 2.6 | 100 | 101 | 1.0 | — | 316.02 | 328.02 | 32.2 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 342.7 | 358.0 | 37.0 | — | 4207.0 | нет |
| PTK-100-R5X8-22M6P2-EF2819 | 100 | R_D5x8 | 5.0 | 2.6 | 100 | 101 | 1.0 | эксцентрик | 316.1 | 328.1 | 32.2 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 342.7 | 358.0 | 37.0 | — | 4207.0 | нет (Т4) |
| PTK-100-R5X5-22M6P2-5887FF | 100 | R_D5x5 | 5.0 | 2.6 | 100 | 101 | 1.0 | — | 316.02 | 328.02 | 32.2 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 342.7 | 358.0 | 25.0 | — | 4207.0 | нет |
| PTK-100-R5X5-22M6P2-C7A9A4 | 100 | R_D5x5 | 5.0 | 2.6 | 100 | 101 | 1.0 | эксцентрик | 316.1 | 328.1 | 32.2 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 342.7 | 358.0 | 25.0 | — | 4207.0 | нет (Т4) |
| PTK-100-R3X8-22M6P2-CC7493 | 100 | R_D3x8 | 3.0 | 2.58 | 100 | 101 | 0.6 | — | 190.85 | 198.05 | 32.0 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 212.7 | 228.0 | 37.0 | — | 2611.1 | нет |
| PTK-100-R3X8-22M6P2-512671 | 100 | R_D3x8 | 3.0 | 2.58 | 100 | 101 | 0.6 | эксцентрик | 190.9 | 198.1 | 32.0 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 212.7 | 228.0 | 37.0 | — | 2611.1 | нет (Т4) |
| PTK-100-B3-22M6P2-2D98E7 | 100 | B_D3 | 3.0 | 2.58 | 100 | 101 | 0.6 | эксцентрик | 190.9 | 198.1 | 32.0 | 22×M6+2шт Ø6 (M6x24P2) | 2 | 212.7 | 228.0 | 17.0 | — | 2611.1 | нет (Т2, Т3, Т4) |

### Расшифровка колонок

| Колонка | Поле в ptk_configs.json | Ед. | Смысл |
|---|---|---|---|
| ID | `id` | — | маркировка исполнения (Д-80): `PTK-<u>-<тело>-<отверстия>-<хэш геометрии>`; по нему генерируются 2D/3D. Детали — `parts[]`: `<ID>.01A`… венцы; снимок параметров — `geom` |
| u | `u` | — | передаточное число: вход — генератор волн, выход — сепаратор |
| Тело | `roller` | — | ключ `vendor_prices.yaml → rollers` (Д-37) |
| $D_\text{ш}$ | `Drol` | мм | диаметр тела качения |
| $D_\text{ш}$ max | `Drol_max` | мм | наибольший $D_\text{ш}$, при котором D ≤ `d_out_max`; «—» — предел не задан (Д-43) |
| n | `n` | шт | тел в ряду, n = u |
| z | `z` | шт | число впадин венца, z = u + 1 (Д-31) |
| $a_\omega$ | `a_w` | мм | эксцентриситет генератора: $a_k D_\text{ш}$ или `a_w` тела (Д-38) |
| Генератор | `gen`, `bearing` | — | `bearing`: ключ `vendor_prices.yaml → bearings`, наименьший с D ≥ 2R_Σ min − $D_\text{ш}$ и d ≥ `shaft_d_min` + 2(a_ω + `ecc_wall_min`) (Д-40); `eccentric`: «эксцентрик» — тела без подшипника (Д-42) |
| $D_\text{г}$ | `Dgen` | мм | поверхность качения тел: D подшипника (Д-40) или наружный Ø эксцентрика, вверх до `dgen_step` (Д-42); $R_\Sigma$ = ($D_\text{г}$ + $D_\text{ш}$)/2 — `R_sum`; условие, задавшее R_Σ min, — `R_by` (подрез, сепаратор, вал) |
| $D_\text{В}$ | `d_root` | мм | диаметр впадин $2(R_\Sigma + a_\omega) + D_\text{ш}$ |
| α max | `alpha_max` | ° | наибольший угол передачи движения профилю (Д-38) |
| Отверстия | `holes`, `mount` | — | крепёжные (они же технологические) отверстия венца: число × резьба + штифты; в скобках — ключ крепления `ring_mounts` (Д-33) |
| Вар. венца | `ring_variants` | шт | число разных сверловок венца в пакете рядов (Д-19): 1 — все венцы одинаковы; сдвиги — в разделе «Фазировка рядов», по каждой конфигурации — `phasing` |
| $D_\text{отв}$ | `d_bc` | мм | окружность центров отверстий, вверх до `d_bc_step` (Д-35) |
| D | `d_out` | мм | наружный диаметр, вверх до `d_out_step` (Д-35) |
| B | `width` | мм | осевая ширина пакета: ряды × max(длина тела, B подшипника) + зазоры (Д-40); у `eccentric` — длина тела |
| M | `M`, `M_by` | Н·м | допускаемый выходной момент пакета: min(по Герцу `M_H`, по C0 подшипника `M_B` — только `bearing`, M крепл./safety); в скобках — что ограничивает (Д-41, Д-42) |
| M крепл. | `t_hold` | Н·м | момент, удерживаемый трением в стыке от затяжки болтов венца |
| Статус | `ok` | — | OK — все проверки пройдены; нет — причина в разделе ниже |


## Фазировка рядов и сверловка венцов (Д-19)

### Крепление `M6x24P2`

Сверловка венца: 22×M6 через 16.3636°, штифты Ø6 в промежутках [0, 11]; порядок симметрии сверловки N = 2 (σ = 180°). Не зависит от тела качения, поэтому дана по u.

| u (z = u + 1) | p, ° | g, ° | Венцов | Ряд | φ, ° | δ/p | s, ° | Сепаратор, ° | Вариант |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 32.7273 | 16.3636 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.75 | 8.1818 | 18 | B |
| | | | | 3 | 180 | 0.5 | 0 | 18 | A |
| | | | | 4 | 270 | 0.25 | 8.1818 | 0 | B |
| 16 | 21.1765 | 10.5882 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 5.2941 | 11.25 | B |
| | | | | 3 | 180 | 0.5 | 0 | 11.25 | A |
| | | | | 4 | 270 | 0.75 | 5.2941 | 0 | B |
| 20 | 17.1429 | 8.5714 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 4.2857 | 9 | B |
| | | | | 3 | 180 | 0.5 | 0 | 9 | A |
| | | | | 4 | 270 | 0.75 | 4.2857 | 0 | B |
| 25 | 13.8462 | 13.8462 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.5 | 6.9231 | 3.6 | B |
| | | | | 3 | 180 | 0 | 0 | 7.2 | A |
| | | | | 4 | 270 | 0.5 | 6.9231 | 10.8 | B |
| 32 | 10.9091 | 5.4545 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 2.7273 | 5.625 | B |
| | | | | 3 | 180 | 0.5 | 0 | 5.625 | A |
| | | | | 4 | 270 | 0.75 | 2.7273 | 0 | B |
| 40 | 8.7805 | 4.3902 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 2.1951 | 4.5 | B |
| | | | | 3 | 180 | 0.5 | 0 | 4.5 | A |
| | | | | 4 | 270 | 0.75 | 2.1951 | 0 | B |
| 50 | 7.0588 | 3.5294 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.75 | 1.7647 | 3.6 | B |
| | | | | 3 | 180 | 0.5 | 0 | 3.6 | A |
| | | | | 4 | 270 | 0.25 | 1.7647 | 0 | B |
| 63 | 5.625 | 5.625 | 1 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0 | 0 | 4.2857 | A |
| | | | | 3 | 180 | 0 | 0 | 2.8571 | A |
| | | | | 4 | 270 | 0 | 0 | 1.4286 | A |
| 80 | 4.4444 | 2.2222 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 1.1111 | 2.25 | B |
| | | | | 3 | 180 | 0.5 | 0 | 2.25 | A |
| | | | | 4 | 270 | 0.75 | 1.1111 | 0 | B |
| 100 | 3.5644 | 1.7822 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 0.8911 | 1.8 | B |
| | | | | 3 | 180 | 0.5 | 0 | 1.8 | A |
| | | | | 4 | 270 | 0.75 | 0.8911 | 0 | B |

### Крепление `M5x12P2`

Сверловка венца: 10×M5 через 36°, штифты Ø5 в промежутках [0, 5]; порядок симметрии сверловки N = 2 (σ = 180°). Не зависит от тела качения, поэтому дана по u.

| u (z = u + 1) | p, ° | g, ° | Венцов | Ряд | φ, ° | δ/p | s, ° | Сепаратор, ° | Вариант |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 32.7273 | 16.3636 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.75 | 8.1818 | 18 | B |
| | | | | 3 | 180 | 0.5 | 0 | 18 | A |
| | | | | 4 | 270 | 0.25 | 8.1818 | 0 | B |
| 16 | 21.1765 | 10.5882 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 5.2941 | 11.25 | B |
| | | | | 3 | 180 | 0.5 | 0 | 11.25 | A |
| | | | | 4 | 270 | 0.75 | 5.2941 | 0 | B |
| 20 | 17.1429 | 8.5714 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 4.2857 | 9 | B |
| | | | | 3 | 180 | 0.5 | 0 | 9 | A |
| | | | | 4 | 270 | 0.75 | 4.2857 | 0 | B |
| 25 | 13.8462 | 13.8462 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.5 | 6.9231 | 3.6 | B |
| | | | | 3 | 180 | 0 | 0 | 7.2 | A |
| | | | | 4 | 270 | 0.5 | 6.9231 | 10.8 | B |
| 32 | 10.9091 | 5.4545 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 2.7273 | 5.625 | B |
| | | | | 3 | 180 | 0.5 | 0 | 5.625 | A |
| | | | | 4 | 270 | 0.75 | 2.7273 | 0 | B |
| 40 | 8.7805 | 4.3902 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 2.1951 | 4.5 | B |
| | | | | 3 | 180 | 0.5 | 0 | 4.5 | A |
| | | | | 4 | 270 | 0.75 | 2.1951 | 0 | B |
| 50 | 7.0588 | 3.5294 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.75 | 1.7647 | 3.6 | B |
| | | | | 3 | 180 | 0.5 | 0 | 3.6 | A |
| | | | | 4 | 270 | 0.25 | 1.7647 | 0 | B |
| 63 | 5.625 | 5.625 | 1 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0 | 0 | 4.2857 | A |
| | | | | 3 | 180 | 0 | 0 | 2.8571 | A |
| | | | | 4 | 270 | 0 | 0 | 1.4286 | A |
| 80 | 4.4444 | 2.2222 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 1.1111 | 2.25 | B |
| | | | | 3 | 180 | 0.5 | 0 | 2.25 | A |
| | | | | 4 | 270 | 0.75 | 1.1111 | 0 | B |
| 100 | 3.5644 | 1.7822 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 0.8911 | 1.8 | B |
| | | | | 3 | 180 | 0.5 | 0 | 1.8 | A |
| | | | | 4 | 270 | 0.75 | 0.8911 | 0 | B |

### Крепление `M4x12P2`

Сверловка венца: 10×M4 через 36°, штифты Ø4 в промежутках [0, 5]; порядок симметрии сверловки N = 2 (σ = 180°). Не зависит от тела качения, поэтому дана по u.

| u (z = u + 1) | p, ° | g, ° | Венцов | Ряд | φ, ° | δ/p | s, ° | Сепаратор, ° | Вариант |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 32.7273 | 16.3636 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.75 | 8.1818 | 18 | B |
| | | | | 3 | 180 | 0.5 | 0 | 18 | A |
| | | | | 4 | 270 | 0.25 | 8.1818 | 0 | B |
| 16 | 21.1765 | 10.5882 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 5.2941 | 11.25 | B |
| | | | | 3 | 180 | 0.5 | 0 | 11.25 | A |
| | | | | 4 | 270 | 0.75 | 5.2941 | 0 | B |
| 20 | 17.1429 | 8.5714 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 4.2857 | 9 | B |
| | | | | 3 | 180 | 0.5 | 0 | 9 | A |
| | | | | 4 | 270 | 0.75 | 4.2857 | 0 | B |
| 25 | 13.8462 | 13.8462 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.5 | 6.9231 | 3.6 | B |
| | | | | 3 | 180 | 0 | 0 | 7.2 | A |
| | | | | 4 | 270 | 0.5 | 6.9231 | 10.8 | B |
| 32 | 10.9091 | 5.4545 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 2.7273 | 5.625 | B |
| | | | | 3 | 180 | 0.5 | 0 | 5.625 | A |
| | | | | 4 | 270 | 0.75 | 2.7273 | 0 | B |
| 40 | 8.7805 | 4.3902 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 2.1951 | 4.5 | B |
| | | | | 3 | 180 | 0.5 | 0 | 4.5 | A |
| | | | | 4 | 270 | 0.75 | 2.1951 | 0 | B |
| 50 | 7.0588 | 3.5294 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.75 | 1.7647 | 3.6 | B |
| | | | | 3 | 180 | 0.5 | 0 | 3.6 | A |
| | | | | 4 | 270 | 0.25 | 1.7647 | 0 | B |
| 63 | 5.625 | 5.625 | 1 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0 | 0 | 4.2857 | A |
| | | | | 3 | 180 | 0 | 0 | 2.8571 | A |
| | | | | 4 | 270 | 0 | 0 | 1.4286 | A |
| 80 | 4.4444 | 2.2222 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 1.1111 | 2.25 | B |
| | | | | 3 | 180 | 0.5 | 0 | 2.25 | A |
| | | | | 4 | 270 | 0.75 | 1.1111 | 0 | B |
| 100 | 3.5644 | 1.7822 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 0.8911 | 1.8 | B |
| | | | | 3 | 180 | 0.5 | 0 | 1.8 | A |
| | | | | 4 | 270 | 0.75 | 0.8911 | 0 | B |

### Крепление `M3x12P2`

Сверловка венца: 10×M3 через 36°, штифты Ø3 в промежутках [0, 5]; порядок симметрии сверловки N = 2 (σ = 180°). Не зависит от тела качения, поэтому дана по u.

| u (z = u + 1) | p, ° | g, ° | Венцов | Ряд | φ, ° | δ/p | s, ° | Сепаратор, ° | Вариант |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 32.7273 | 16.3636 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.75 | 8.1818 | 18 | B |
| | | | | 3 | 180 | 0.5 | 0 | 18 | A |
| | | | | 4 | 270 | 0.25 | 8.1818 | 0 | B |
| 16 | 21.1765 | 10.5882 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 5.2941 | 11.25 | B |
| | | | | 3 | 180 | 0.5 | 0 | 11.25 | A |
| | | | | 4 | 270 | 0.75 | 5.2941 | 0 | B |
| 20 | 17.1429 | 8.5714 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 4.2857 | 9 | B |
| | | | | 3 | 180 | 0.5 | 0 | 9 | A |
| | | | | 4 | 270 | 0.75 | 4.2857 | 0 | B |
| 25 | 13.8462 | 13.8462 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.5 | 6.9231 | 3.6 | B |
| | | | | 3 | 180 | 0 | 0 | 7.2 | A |
| | | | | 4 | 270 | 0.5 | 6.9231 | 10.8 | B |
| 32 | 10.9091 | 5.4545 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 2.7273 | 5.625 | B |
| | | | | 3 | 180 | 0.5 | 0 | 5.625 | A |
| | | | | 4 | 270 | 0.75 | 2.7273 | 0 | B |
| 40 | 8.7805 | 4.3902 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 2.1951 | 4.5 | B |
| | | | | 3 | 180 | 0.5 | 0 | 4.5 | A |
| | | | | 4 | 270 | 0.75 | 2.1951 | 0 | B |
| 50 | 7.0588 | 3.5294 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.75 | 1.7647 | 3.6 | B |
| | | | | 3 | 180 | 0.5 | 0 | 3.6 | A |
| | | | | 4 | 270 | 0.25 | 1.7647 | 0 | B |
| 63 | 5.625 | 5.625 | 1 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0 | 0 | 4.2857 | A |
| | | | | 3 | 180 | 0 | 0 | 2.8571 | A |
| | | | | 4 | 270 | 0 | 0 | 1.4286 | A |
| 80 | 4.4444 | 2.2222 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 1.1111 | 2.25 | B |
| | | | | 3 | 180 | 0.5 | 0 | 2.25 | A |
| | | | | 4 | 270 | 0.75 | 1.1111 | 0 | B |
| 100 | 3.5644 | 1.7822 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 0.8911 | 1.8 | B |
| | | | | 3 | 180 | 0.5 | 0 | 1.8 | A |
| | | | | 4 | 270 | 0.75 | 0.8911 | 0 | B |

### Крепление `M3x8P2`

Сверловка венца: 6×M3 через 60°, штифты Ø3 в промежутках [0, 3]; порядок симметрии сверловки N = 2 (σ = 180°). Не зависит от тела качения, поэтому дана по u.

| u (z = u + 1) | p, ° | g, ° | Венцов | Ряд | φ, ° | δ/p | s, ° | Сепаратор, ° | Вариант |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 32.7273 | 16.3636 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.75 | 8.1818 | 18 | B |
| | | | | 3 | 180 | 0.5 | 0 | 18 | A |
| | | | | 4 | 270 | 0.25 | 8.1818 | 0 | B |
| 16 | 21.1765 | 10.5882 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 5.2941 | 11.25 | B |
| | | | | 3 | 180 | 0.5 | 0 | 11.25 | A |
| | | | | 4 | 270 | 0.75 | 5.2941 | 0 | B |
| 20 | 17.1429 | 8.5714 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 4.2857 | 9 | B |
| | | | | 3 | 180 | 0.5 | 0 | 9 | A |
| | | | | 4 | 270 | 0.75 | 4.2857 | 0 | B |
| 25 | 13.8462 | 13.8462 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.5 | 6.9231 | 3.6 | B |
| | | | | 3 | 180 | 0 | 0 | 7.2 | A |
| | | | | 4 | 270 | 0.5 | 6.9231 | 10.8 | B |
| 32 | 10.9091 | 5.4545 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 2.7273 | 5.625 | B |
| | | | | 3 | 180 | 0.5 | 0 | 5.625 | A |
| | | | | 4 | 270 | 0.75 | 2.7273 | 0 | B |
| 40 | 8.7805 | 4.3902 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 2.1951 | 4.5 | B |
| | | | | 3 | 180 | 0.5 | 0 | 4.5 | A |
| | | | | 4 | 270 | 0.75 | 2.1951 | 0 | B |
| 50 | 7.0588 | 3.5294 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.75 | 1.7647 | 3.6 | B |
| | | | | 3 | 180 | 0.5 | 0 | 3.6 | A |
| | | | | 4 | 270 | 0.25 | 1.7647 | 0 | B |
| 63 | 5.625 | 5.625 | 1 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0 | 0 | 4.2857 | A |
| | | | | 3 | 180 | 0 | 0 | 2.8571 | A |
| | | | | 4 | 270 | 0 | 0 | 1.4286 | A |
| 80 | 4.4444 | 2.2222 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 1.1111 | 2.25 | B |
| | | | | 3 | 180 | 0.5 | 0 | 2.25 | A |
| | | | | 4 | 270 | 0.75 | 1.1111 | 0 | B |
| 100 | 3.5644 | 1.7822 | 2 | 1 | 0 | 0 | 0 | 0 | A |
| | | | | 2 | 90 | 0.25 | 0.8911 | 1.8 | B |
| | | | | 3 | 180 | 0.5 | 0 | 1.8 | A |
| | | | | 4 | 270 | 0.75 | 0.8911 | 0 | B |

| Колонка | Поле `phasing[]` | Смысл |
|---|---|---|
| p | — | шаг впадин венца, 360°/z |
| g | — | 360°/НОК(z, N): наименьший поворот, при котором профиль и сверловка одновременно совпадают сами с собой; сдвиги считаются по модулю g |
| Венцов | `ring_variants` | число разных венцов в пакете |
| Ряд, φ | `row`, `phi` | номер ряда и фаза эксцентрика генератора относительно ряда 1 |
| δ/p | `delta_p` | сдвиг профиля ряда относительно ряда 1 в долях шага впадин, (φ mod p)/p |
| s | `s` | поворот сверловки относительно профиля венца (впадина 0 на 0°) в сторону φ — по нему сверлить; `s_arc_mm` — то же по дуге Ø окр. отв., мм |
| Сепаратор | `cage` | смещение гнёзд ряда в сепараторе, φ mod 360°/n |
| Вариант | `variant` | буква венца — группа равного сдвига сверловки s по порядку рядов (§6.4 INS-10): одинаковые буквы — одинаковые детали (одна УП, один номер) |

Угловая фаза передаётся штифтами H7; болты в отверстиях с зазором фазу не держат.

## Нереализуемые конфигурации

- u=32, R_D8x16, bearing: нет подшипника генератора с D ≥ 157.6 и d ≥ 11.2 мм в vendor_prices.yaml → bearings (Д-40)
- u=32, R_D8x16, bearing: D 206 > 200: тела Dш 8 при n=32 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 7.72 мм (OQ-05)
- u=32, R_D8x8, bearing: нет подшипника генератора с D ≥ 157.6 и d ≥ 11.2 мм в vendor_prices.yaml → bearings (Д-40)
- u=32, R_D8x8, bearing: D 206 > 200: тела Dш 8 при n=32 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 7.72 мм (OQ-05)
- u=40, R_D8x16, bearing: нет подшипника генератора с D ≥ 198.3 и d ≥ 11.2 мм в vendor_prices.yaml → bearings (Д-40)
- u=40, R_D8x16, bearing: D 247 > 200: тела Dш 8 при n=40 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 6.28 мм (OQ-05)
- u=40, R_D8x16, eccentric: D 247 > 200: тела Dш 8 при n=40 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 6.27 мм (OQ-05)
- u=40, R_D8x8, bearing: нет подшипника генератора с D ≥ 198.3 и d ≥ 11.2 мм в vendor_prices.yaml → bearings (Д-40)
- u=40, R_D8x8, bearing: D 247 > 200: тела Dш 8 при n=40 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 6.28 мм (OQ-05)
- u=40, R_D8x8, eccentric: D 247 > 200: тела Dш 8 при n=40 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 6.27 мм (OQ-05)
- u=40, R_D7x20, bearing: нет подшипника генератора с D ≥ 173.7 и d ≥ 10.8 мм в vendor_prices.yaml → bearings (Д-40)
- u=40, R_D7x20, bearing: D 220 > 200: тела Dш 7 при n=40 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 6.27 мм (OQ-05)
- u=40, R_D7x20, eccentric: D 220 > 200: тела Dш 7 при n=40 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 6.27 мм (OQ-05)
- u=40, R_D6x6, bearing: нет подшипника генератора с D ≥ 149.0 и d ≥ 10.4 мм в vendor_prices.yaml → bearings (Д-40)
- u=50, R_D8x16, bearing: нет подшипника генератора с D ≥ 249.2 и d ≥ 11.2 мм в vendor_prices.yaml → bearings (Д-40)
- u=50, R_D8x16, bearing: D 298 > 200: тела Dш 8 при n=50 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 5.09 мм (OQ-05)
- u=50, R_D8x16, eccentric: D 298 > 200: тела Dш 8 при n=50 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 5.08 мм (OQ-05)
- u=50, R_D8x8, bearing: нет подшипника генератора с D ≥ 249.2 и d ≥ 11.2 мм в vendor_prices.yaml → bearings (Д-40)
- u=50, R_D8x8, bearing: D 298 > 200: тела Dш 8 при n=50 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 5.09 мм (OQ-05)
- u=50, R_D8x8, eccentric: D 298 > 200: тела Dш 8 при n=50 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 5.08 мм (OQ-05)
- u=50, R_D7x20, bearing: нет подшипника генератора с D ≥ 218.3 и d ≥ 10.8 мм в vendor_prices.yaml → bearings (Д-40)
- u=50, R_D7x20, bearing: D 265 > 200: тела Dш 7 при n=50 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 5.08 мм (OQ-05)
- u=50, R_D7x20, eccentric: D 265 > 200: тела Dш 7 при n=50 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 5.08 мм (OQ-05)
- u=50, R_D6x6, bearing: нет подшипника генератора с D ≥ 187.3 и d ≥ 10.4 мм в vendor_prices.yaml → bearings (Д-40)
- u=50, R_D6x6, bearing: D 231 > 200: тела Dш 6 при n=50 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 5.08 мм (OQ-05)
- u=50, R_D6x6, eccentric: D 231 > 200: тела Dш 6 при n=50 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 5.08 мм (OQ-05)
- u=50, R_D5x8, bearing: нет подшипника генератора с D ≥ 156.3 и d ≥ 10.0 мм в vendor_prices.yaml → bearings (Д-40)
- u=50, R_D5x5, bearing: нет подшипника генератора с D ≥ 156.3 и d ≥ 10.0 мм в vendor_prices.yaml → bearings (Д-40)
- u=63, R_D8x16, bearing: нет подшипника генератора с D ≥ 315.4 и d ≥ 11.2 мм в vendor_prices.yaml → bearings (Д-40)
- u=63, R_D8x16, bearing: D 364 > 200: тела Dш 8 при n=63 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 4.08 мм (OQ-05)
- u=63, R_D8x16, eccentric: D 364 > 200: тела Dш 8 при n=63 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 4.08 мм (OQ-05)
- u=63, R_D8x8, bearing: нет подшипника генератора с D ≥ 315.4 и d ≥ 11.2 мм в vendor_prices.yaml → bearings (Д-40)
- u=63, R_D8x8, bearing: D 364 > 200: тела Dш 8 при n=63 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 4.08 мм (OQ-05)
- u=63, R_D8x8, eccentric: D 364 > 200: тела Dш 8 при n=63 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 4.08 мм (OQ-05)
- u=63, R_D7x20, bearing: нет подшипника генератора с D ≥ 276.2 и d ≥ 10.8 мм в vendor_prices.yaml → bearings (Д-40)
- u=63, R_D7x20, bearing: D 323 > 200: тела Dш 7 при n=63 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 4.08 мм (OQ-05)
- u=63, R_D7x20, eccentric: D 323 > 200: тела Dш 7 при n=63 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 4.07 мм (OQ-05)
- u=63, R_D6x6, bearing: нет подшипника генератора с D ≥ 237.0 и d ≥ 10.4 мм в vendor_prices.yaml → bearings (Д-40)
- u=63, R_D6x6, bearing: D 281 > 200: тела Dш 6 при n=63 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 4.07 мм (OQ-05)
- u=63, R_D6x6, eccentric: D 281 > 200: тела Dш 6 при n=63 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 4.07 мм (OQ-05)
- u=63, R_D5x8, bearing: нет подшипника генератора с D ≥ 197.9 и d ≥ 10.0 мм в vendor_prices.yaml → bearings (Д-40)
- u=63, R_D5x8, bearing: D 240 > 200: тела Dш 5 при n=63 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 4.06 мм (OQ-05)
- u=63, R_D5x8, eccentric: D 240 > 200: тела Dш 5 при n=63 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 4.06 мм (OQ-05)
- u=63, R_D5x5, bearing: нет подшипника генератора с D ≥ 197.9 и d ≥ 10.0 мм в vendor_prices.yaml → bearings (Д-40)
- u=63, R_D5x5, bearing: D 240 > 200: тела Dш 5 при n=63 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 4.06 мм (OQ-05)
- u=63, R_D5x5, eccentric: D 240 > 200: тела Dш 5 при n=63 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 4.06 мм (OQ-05)
- u=80, R_D8x16, bearing: нет подшипника генератора с D ≥ 401.9 и d ≥ 11.2 мм в vendor_prices.yaml → bearings (Д-40)
- u=80, R_D8x16, bearing: D 451 > 200: тела Dш 8 при n=80 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 3.24 мм (OQ-05)
- u=80, R_D8x16, eccentric: D 451 > 200: тела Dш 8 при n=80 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 3.24 мм (OQ-05)
- u=80, R_D8x8, bearing: нет подшипника генератора с D ≥ 401.9 и d ≥ 11.2 мм в vendor_prices.yaml → bearings (Д-40)
- u=80, R_D8x8, bearing: D 451 > 200: тела Dш 8 при n=80 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 3.24 мм (OQ-05)
- u=80, R_D8x8, eccentric: D 451 > 200: тела Dш 8 при n=80 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 3.24 мм (OQ-05)
- u=80, R_D7x20, bearing: нет подшипника генератора с D ≥ 352.0 и d ≥ 10.8 мм в vendor_prices.yaml → bearings (Д-40)
- u=80, R_D7x20, bearing: D 399 > 200: тела Dш 7 при n=80 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 3.24 мм (OQ-05)
- u=80, R_D7x20, eccentric: D 399 > 200: тела Dш 7 при n=80 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 3.24 мм (OQ-05)
- u=80, R_D6x6, bearing: нет подшипника генератора с D ≥ 302.1 и d ≥ 10.4 мм в vendor_prices.yaml → bearings (Д-40)
- u=80, R_D6x6, bearing: D 346 > 200: тела Dш 6 при n=80 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 3.23 мм (OQ-05)
- u=80, R_D6x6, eccentric: D 346 > 200: тела Dш 6 при n=80 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 3.23 мм (OQ-05)
- u=80, R_D5x8, bearing: нет подшипника генератора с D ≥ 252.1 и d ≥ 10.0 мм в vendor_prices.yaml → bearings (Д-40)
- u=80, R_D5x8, bearing: D 294 > 200: тела Dш 5 при n=80 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 3.23 мм (OQ-05)
- u=80, R_D5x8, eccentric: D 294 > 200: тела Dш 5 при n=80 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 3.23 мм (OQ-05)
- u=80, R_D5x5, bearing: нет подшипника генератора с D ≥ 252.1 и d ≥ 10.0 мм в vendor_prices.yaml → bearings (Д-40)
- u=80, R_D5x5, bearing: D 294 > 200: тела Dш 5 при n=80 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 3.23 мм (OQ-05)
- u=80, R_D5x5, eccentric: D 294 > 200: тела Dш 5 при n=80 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 3.23 мм (OQ-05)
- u=80, R_D3x8, bearing: нет подшипника генератора с D ≥ 152.3 и d ≥ 9.2 мм в vendor_prices.yaml → bearings (Д-40)
- u=100, R_D8x16, bearing: нет подшипника генератора с D ≥ 503.8 и d ≥ 11.2 мм в vendor_prices.yaml → bearings (Д-40)
- u=100, R_D8x16, bearing: D 553 > 200: тела Dш 8 при n=100 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 2.61 мм (OQ-05)
- u=100, R_D8x16, eccentric: D 553 > 200: тела Dш 8 при n=100 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 2.61 мм (OQ-05)
- u=100, R_D8x8, bearing: нет подшипника генератора с D ≥ 503.8 и d ≥ 11.2 мм в vendor_prices.yaml → bearings (Д-40)
- u=100, R_D8x8, bearing: D 553 > 200: тела Dш 8 при n=100 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 2.61 мм (OQ-05)
- u=100, R_D8x8, eccentric: D 553 > 200: тела Dш 8 при n=100 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 2.61 мм (OQ-05)
- u=100, R_D7x20, bearing: нет подшипника генератора с D ≥ 441.2 и d ≥ 10.8 мм в vendor_prices.yaml → bearings (Д-40)
- u=100, R_D7x20, bearing: D 488 > 200: тела Dш 7 при n=100 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 2.61 мм (OQ-05)
- u=100, R_D7x20, eccentric: D 488 > 200: тела Dш 7 при n=100 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 2.61 мм (OQ-05)
- u=100, R_D6x6, bearing: нет подшипника генератора с D ≥ 378.6 и d ≥ 10.4 мм в vendor_prices.yaml → bearings (Д-40)
- u=100, R_D6x6, bearing: D 423 > 200: тела Dш 6 при n=100 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 2.6 мм (OQ-05)
- u=100, R_D6x6, eccentric: D 423 > 200: тела Dш 6 при n=100 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 2.6 мм (OQ-05)
- u=100, R_D5x8, bearing: нет подшипника генератора с D ≥ 316.0 и d ≥ 10.0 мм в vendor_prices.yaml → bearings (Д-40)
- u=100, R_D5x8, bearing: D 358 > 200: тела Dш 5 при n=100 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 2.6 мм (OQ-05)
- u=100, R_D5x8, eccentric: D 358 > 200: тела Dш 5 при n=100 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 2.6 мм (OQ-05)
- u=100, R_D5x5, bearing: нет подшипника генератора с D ≥ 316.0 и d ≥ 10.0 мм в vendor_prices.yaml → bearings (Д-40)
- u=100, R_D5x5, bearing: D 358 > 200: тела Dш 5 при n=100 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 2.6 мм (OQ-05)
- u=100, R_D5x5, eccentric: D 358 > 200: тела Dш 5 при n=100 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 2.6 мм (OQ-05)
- u=100, R_D3x8, bearing: нет подшипника генератора с D ≥ 190.9 и d ≥ 9.2 мм в vendor_prices.yaml → bearings (Д-40)
- u=100, R_D3x8, bearing: D 228 > 200: тела Dш 3 при n=100 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 2.58 мм (OQ-05)
- u=100, R_D3x8, eccentric: D 228 > 200: тела Dш 3 при n=100 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 2.58 мм (OQ-05)
- u=100, B_D3, eccentric: D 228 > 200: тела Dш 3 при n=100 с отверстиями 22×M6+2шт Ø6 не вмещаются; Dш max ≈ 2.58 мм (OQ-05)

## Предупреждения

- u=10, R_D8x16, bearing: эксцентрик: остаток дисбаланса 32.02 из 158.9 г·мм — отверстия балансировки не помещаются (Д-46)
- u=10, R_D8x8, bearing: эксцентрик: остаток дисбаланса 6.76 из 133.6 г·мм — отверстия балансировки не помещаются (Д-46)
- u=10, R_D7x20, bearing: эксцентрик: остаток дисбаланса 40.75 из 114.9 г·мм — отверстия балансировки не помещаются (Д-46)
- u=10, R_D6x6, bearing: эксцентрик: остаток дисбаланса 14.57 из 53.8 г·мм — отверстия балансировки не помещаются (Д-46)
- u=10, R_D5x8, bearing: эксцентрик: остаток дисбаланса 16.52 из 32.9 г·мм — отверстия балансировки не помещаются (Д-46)
- u=10, R_D5x5, bearing: эксцентрик: остаток дисбаланса 14.2 из 30.5 г·мм — отверстия балансировки не помещаются (Д-46)
- u=10, R_D3x8, bearing: эксцентрик: остаток дисбаланса 4.87 из 4.9 г·мм — отверстия балансировки не помещаются (Д-46)
- u=10, R_D3x8, bearing: ряд 3: стенка эксцентрика у паза шпонки 0.56 < ecc_wall_min 1 мм — изменить key_angle (Д-46)
- u=10, R_D3x8, bearing: ряд 4: стенка эксцентрика у паза шпонки 0.56 < ecc_wall_min 1 мм — изменить key_angle (Д-46)
- u=10, R_D3x8, eccentric: эксцентрик: остаток дисбаланса 2.06 из 10.2 г·мм — отверстия балансировки не помещаются (Д-46)
- u=10, B_D3, eccentric: эксцентрик: остаток дисбаланса 0.61 из 3.7 г·мм — отверстия балансировки не помещаются (Д-46)
- u=16, R_D3x8, bearing: эксцентрик: остаток дисбаланса 3.42 из 18.1 г·мм — отверстия балансировки не помещаются (Д-46)

Итого: 91 реализуемых из 150; исключено по технологии — 10
(обоснование — «Технологические ограничения» в конце, Д-45). Коды Т# в колонке «Статус» —
технологические примечания к исполнению.

## Профиль венца и порядок расчёта (Д-38)

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
   момент и износ — CP-08.

### Силовой расчёт (Д-40, Д-41)

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
M = min($M_H$, $M_B$, M крепл. / safety), в скобках — что ограничивает.
Генератор `eccentric` (Д-42): тела катятся прямо по эксцентрику, $D_\text{г}$ — его наружный
диаметр (вверх до `dgen_step`, не меньше `shaft_d_min` + 2($a_\omega$ + `ecc_wall_min`)); пара
тело/эксцентрик на всей длине тела, $M_B$ нет. В (12) $\omega_\text{к} = -\omega$ задана
кинематически (кольцо — сам эксцентрик), а не из равновесия кольца: скольжение в $K_\text{г}$
порядка $\omega D_\text{г}/2$, потери и износ выше, чем с подшипником (OQ-10).
Не учтены: трение (11), (12), ресурс подшипника, контакт тело/паз сепаратора (OQ-08, CP-32).

### Профиль и нагрузки по исполнениям (Д-38)

R_о/R, R_в/R — (8), (9) при φ = 90° (α = α max), на 1 Н реакции генератора.

| ID | $a_\omega$ | $R_\Sigma$ | $R_\Sigma$ задан | $D_\text{г}$ | α max, ° | $R_\text{о}/R$ | $R_\text{в}/R$ | r верш., мм | перемычка сеп., мм | Статус |
|---|---|---|---|---|---|---|---|---|---|---|
| PTK-010-R8X16-10M5P2-8B0907 | 1.6 | 27.5 | подрез | 47.0 | 32.7 | 0.58 | 1.19 | 0.288 | 7.91 | OK |
| PTK-010-R8X16-10M5P2-8F60AF | 1.6 | 26.85 | подрез | 45.7 | 33.3 | 0.60 | 1.19 | 0.066 | 7.51 | OK |
| PTK-010-R8X8-10M5P2-070C3C | 1.6 | 27.5 | подрез | 47.0 | 32.7 | 0.58 | 1.19 | 0.288 | 7.91 | OK |
| PTK-010-R8X8-10M5P2-FF6078 | 1.6 | 26.85 | подрез | 45.7 | 33.3 | 0.60 | 1.19 | 0.066 | 7.51 | OK |
| PTK-010-R7X20-10M5P2-7D60D6 | 1.4 | 24.5 | подрез | 42.0 | 32.2 | 0.57 | 1.18 | 0.406 | 7.19 | OK |
| PTK-010-R7X20-10M5P2-2EA179 | 1.4 | 23.5 | подрез | 40.0 | 33.3 | 0.60 | 1.19 | 0.06 | 6.57 | OK |
| PTK-010-R6X6-10M5P2-B73626 | 1.2 | 21.5 | подрез | 37.0 | 31.6 | 0.56 | 1.17 | 0.528 | 6.47 | OK |
| PTK-010-R6X6-10M5P2-8AD44D | 1.2 | 20.15 | подрез | 34.3 | 33.3 | 0.60 | 1.19 | 0.054 | 5.64 | OK |
| PTK-010-R5X8-10M5P2-2ECBA4 | 1.0 | 18.5 | подрез | 32.0 | 30.8 | 0.54 | 1.16 | 0.659 | 5.75 | OK |
| PTK-010-R5X8-10M5P2-D97113 | 1.0 | 16.85 | подрез | 28.7 | 33.2 | 0.59 | 1.19 | 0.064 | 4.73 | OK |
| PTK-010-R5X5-10M5P2-979E07 | 1.0 | 18.5 | подрез | 32.0 | 30.8 | 0.54 | 1.16 | 0.659 | 5.75 | OK |
| PTK-010-R5X5-10M5P2-FDAB21 | 1.0 | 16.85 | подрез | 28.7 | 33.2 | 0.59 | 1.19 | 0.064 | 4.73 | OK |
| PTK-010-R3X8-10M3P2-A16061 | 0.6 | 11.0 | подрез | 19.0 | 31.0 | 0.55 | 1.16 | 0.357 | 3.39 | OK |
| PTK-010-R3X8-10M3P2-1A947D | 0.6 | 10.15 | подрез | 17.3 | 33.1 | 0.59 | 1.19 | 0.052 | 2.87 | OK |
| PTK-010-B3-10M3P2-C587B2 | 0.6 | 10.15 | подрез | 17.3 | 33.1 | 0.59 | 1.19 | 0.052 | 2.87 | OK |
| PTK-016-R8X16-10M5P2-079658 | 1.6 | 43.0 | подрез | 78.0 | 32.3 | 0.60 | 1.18 | 0.245 | 8.09 | OK |
| PTK-016-R8X16-10M5P2-EBEF90 | 1.6 | 42.1 | подрез | 76.2 | 32.9 | 0.61 | 1.19 | 0.057 | 7.74 | OK |
| PTK-016-R8X8-10M5P2-519C3A | 1.6 | 43.0 | подрез | 78.0 | 32.3 | 0.60 | 1.18 | 0.245 | 8.09 | OK |
| PTK-016-R8X8-10M5P2-999A95 | 1.6 | 42.1 | подрез | 76.2 | 32.9 | 0.61 | 1.19 | 0.057 | 7.74 | OK |
| PTK-016-R7X20-10M5P2-A6FA18 | 1.4 | 39.5 | подрез | 72.0 | 31.1 | 0.57 | 1.17 | 0.622 | 7.81 | OK |
| PTK-016-R7X20-10M5P2-B6A6DE | 1.4 | 36.85 | подрез | 66.7 | 32.9 | 0.61 | 1.19 | 0.052 | 6.78 | OK |
| PTK-016-R6X6-10M5P2-C54A11 | 1.2 | 32.0 | подрез | 58.0 | 32.5 | 0.60 | 1.19 | 0.131 | 5.97 | OK |
| PTK-016-R6X6-10M5P2-1E58F3 | 1.2 | 31.65 | подрез | 57.3 | 32.8 | 0.61 | 1.19 | 0.058 | 5.83 | OK |
| PTK-016-R5X8-10M5P2-66659B | 1.0 | 28.5 | подрез | 52.0 | 30.8 | 0.56 | 1.16 | 0.509 | 5.69 | OK |
| PTK-016-R5X8-10M5P2-424AEF | 1.0 | 26.4 | подрез | 47.8 | 32.8 | 0.61 | 1.19 | 0.054 | 4.87 | OK |
| PTK-016-R5X5-10M5P2-96A041 | 1.0 | 28.5 | подрез | 52.0 | 30.8 | 0.56 | 1.16 | 0.509 | 5.69 | OK |
| PTK-016-R5X5-10M5P2-303BBF | 1.0 | 26.4 | подрез | 47.8 | 32.8 | 0.61 | 1.19 | 0.054 | 4.87 | OK |
| PTK-016-R3X8-10M5P2-7841A0 | 0.6 | 17.5 | подрез | 32.0 | 30.3 | 0.55 | 1.16 | 0.397 | 3.57 | OK |
| PTK-016-R3X8-10M5P2-4F895B | 0.6 | 15.95 | подрез | 28.9 | 32.6 | 0.60 | 1.19 | 0.055 | 2.97 | OK |
| PTK-016-B3-10M5P2-40D6F0 | 0.6 | 15.95 | подрез | 28.9 | 32.6 | 0.60 | 1.19 | 0.055 | 2.97 | OK |
| PTK-020-R8X16-22M6P2-4A32DD | 1.6 | 54.0 | подрез | 100.0 | 31.9 | 0.59 | 1.18 | 0.343 | 8.34 | OK |
| PTK-020-R8X16-22M6P2-0377C3 | 1.6 | 52.25 | подрез | 96.5 | 32.8 | 0.61 | 1.19 | 0.051 | 7.8 | OK |
| PTK-020-R8X8-22M6P2-656315 | 1.6 | 54.0 | подрез | 100.0 | 31.9 | 0.59 | 1.18 | 0.343 | 8.34 | OK |
| PTK-020-R8X8-22M6P2-7C7CC0 | 1.6 | 52.25 | подрез | 96.5 | 32.8 | 0.61 | 1.19 | 0.051 | 7.8 | OK |
| PTK-020-R7X20-10M5P2-388229 | 1.4 | 46.0 | подрез | 85.0 | 32.6 | 0.61 | 1.19 | 0.09 | 6.91 | OK |
| PTK-020-R7X20-10M5P2-EAC535 | 1.4 | 45.8 | подрез | 84.6 | 32.7 | 0.61 | 1.19 | 0.058 | 6.85 | OK |
| PTK-020-R6X6-10M5P2-AFCBDF | 1.2 | 42.0 | подрез | 78.0 | 31.0 | 0.57 | 1.17 | 0.517 | 6.73 | OK |
| PTK-020-R6X6-10M5P2-CDD24C | 1.2 | 39.3 | подрез | 72.6 | 32.7 | 0.61 | 1.19 | 0.056 | 5.88 | OK |
| PTK-020-R5X8-10M5P2-04E9EC | 1.0 | 35.0 | подрез | 65.0 | 31.0 | 0.57 | 1.17 | 0.431 | 5.61 | OK |
| PTK-020-R5X8-10M5P2-4FDD6C | 1.0 | 32.8 | подрез | 60.6 | 32.6 | 0.61 | 1.19 | 0.055 | 4.92 | OK |
| PTK-020-R5X5-10M5P2-0A0407 | 1.0 | 35.0 | подрез | 65.0 | 31.0 | 0.57 | 1.17 | 0.431 | 5.61 | OK |
| PTK-020-R5X5-10M5P2-67323B | 1.0 | 32.8 | подрез | 60.6 | 32.6 | 0.61 | 1.19 | 0.055 | 4.92 | OK |
| PTK-020-R3X8-10M5P2-DBE2F2 | 0.6 | 20.0 | подрез | 37.0 | 32.2 | 0.60 | 1.18 | 0.086 | 3.05 | OK |
| PTK-020-R3X8-10M5P2-248D14 | 0.6 | 19.8 | подрез | 36.6 | 32.5 | 0.61 | 1.18 | 0.053 | 2.99 | OK |
| PTK-020-B3-10M5P2-74A23C | 0.6 | 19.8 | подрез | 36.6 | 32.5 | 0.61 | 1.18 | 0.053 | 2.99 | OK |
| PTK-025-R8X16-22M6P2-754C59 | 1.6 | 66.5 | подрез | 125.0 | 32.0 | 0.60 | 1.18 | 0.252 | 8.23 | OK |
| PTK-025-R8X16-22M6P2-0F2F2C | 1.6 | 65.0 | подрез | 122.0 | 32.6 | 0.62 | 1.19 | 0.054 | 7.85 | OK |
| PTK-025-R8X8-22M6P2-2C1E5B | 1.6 | 66.5 | подрез | 125.0 | 32.0 | 0.60 | 1.18 | 0.252 | 8.23 | OK |
| PTK-025-R8X8-22M6P2-391A86 | 1.6 | 65.0 | подрез | 122.0 | 32.6 | 0.62 | 1.19 | 0.054 | 7.85 | OK |
| PTK-025-R7X20-22M6P2-1327C5 | 1.4 | 58.5 | подрез | 110.0 | 31.9 | 0.60 | 1.18 | 0.262 | 7.28 | OK |
| PTK-025-R7X20-22M6P2-772B35 | 1.4 | 56.9 | подрез | 106.8 | 32.6 | 0.62 | 1.19 | 0.05 | 6.88 | OK |
| PTK-025-R6X6-10M5P2-505845 | 1.2 | 50.5 | подрез | 95.0 | 31.7 | 0.59 | 1.18 | 0.273 | 6.33 | OK |
| PTK-025-R6X6-10M5P2-D85760 | 1.2 | 48.85 | подрез | 91.7 | 32.6 | 0.61 | 1.19 | 0.053 | 5.91 | OK |
| PTK-025-R5X8-10M5P2-2182BD | 1.0 | 41.5 | подрез | 78.0 | 32.1 | 0.60 | 1.18 | 0.149 | 5.13 | OK |
| PTK-025-R5X8-10M5P2-E7AF17 | 1.0 | 40.8 | подрез | 76.6 | 32.5 | 0.61 | 1.19 | 0.056 | 4.95 | OK |
| PTK-025-R5X5-10M5P2-01744D | 1.0 | 41.5 | подрез | 78.0 | 32.1 | 0.60 | 1.18 | 0.149 | 5.13 | OK |
| PTK-025-R5X5-10M5P2-AC2DD3 | 1.0 | 40.8 | подрез | 76.6 | 32.5 | 0.61 | 1.19 | 0.056 | 4.95 | OK |
| PTK-025-R3X8-10M5P2-70E7B4 | 0.6 | 25.0 | подрез | 47.0 | 32.0 | 0.60 | 1.18 | 0.103 | 3.1 | OK |
| PTK-025-R3X8-10M5P2-A700AA | 0.6 | 24.65 | подрез | 46.3 | 32.3 | 0.61 | 1.18 | 0.056 | 3.01 | OK |
| PTK-025-B3-10M5P2-7EC60B | 0.6 | 24.65 | подрез | 46.3 | 32.3 | 0.61 | 1.18 | 0.056 | 3.01 | OK |
| PTK-032-R8X16-22M6P2-9E294B | 1.6 | 82.788 | подрез | 157.58 | 32.5 | 0.62 | 1.19 | 0.05 | 7.88 | нет |
| PTK-032-R8X16-10M3P2-B06A75 | 1.6 | 82.8 | подрез | 157.6 | 32.5 | 0.62 | 1.19 | 0.051 | 7.89 | OK |
| PTK-032-R8X8-22M6P2-12A3E4 | 1.6 | 82.788 | подрез | 157.58 | 32.5 | 0.62 | 1.19 | 0.05 | 7.88 | нет |
| PTK-032-R8X8-10M3P2-8F3875 | 1.6 | 82.8 | подрез | 157.6 | 32.5 | 0.62 | 1.19 | 0.051 | 7.89 | OK |
| PTK-032-R7X20-22M6P2-BAC1EE | 1.4 | 73.5 | подрез | 140.0 | 32.2 | 0.61 | 1.18 | 0.152 | 7.11 | OK |
| PTK-032-R7X20-22M6P2-1A4385 | 1.4 | 72.55 | подрез | 138.1 | 32.5 | 0.62 | 1.19 | 0.055 | 6.92 | OK |
| PTK-032-R6X6-22M6P2-E942C3 | 1.2 | 63.0 | подрез | 120.0 | 32.2 | 0.61 | 1.18 | 0.13 | 6.09 | OK |
| PTK-032-R6X6-22M6P2-D4BE19 | 1.2 | 62.25 | подрез | 118.5 | 32.5 | 0.62 | 1.19 | 0.054 | 5.94 | OK |
| PTK-032-R5X8-22M6P2-19B83D | 1.0 | 52.5 | подрез | 100.0 | 32.2 | 0.61 | 1.18 | 0.109 | 5.08 | OK |
| PTK-032-R5X8-10M5P2-2CBB5C | 1.0 | 51.95 | подрез | 98.9 | 32.4 | 0.62 | 1.18 | 0.052 | 4.97 | OK |
| PTK-032-R5X5-22M6P2-793017 | 1.0 | 52.5 | подрез | 100.0 | 32.2 | 0.61 | 1.18 | 0.109 | 5.08 | OK |
| PTK-032-R5X5-10M5P2-3F07B6 | 1.0 | 51.95 | подрез | 98.9 | 32.4 | 0.62 | 1.18 | 0.052 | 4.97 | OK |
| PTK-032-R3X8-10M5P2-1E1E34 | 0.6 | 34.0 | подрез | 65.0 | 30.2 | 0.56 | 1.16 | 0.333 | 3.54 | OK |
| PTK-032-R3X8-10M5P2-7AE1CB | 0.6 | 31.4 | подрез | 59.8 | 32.2 | 0.61 | 1.18 | 0.055 | 3.03 | OK |
| PTK-032-B3-10M5P2-DEDB0E | 0.6 | 31.4 | подрез | 59.8 | 32.2 | 0.61 | 1.18 | 0.055 | 3.03 | OK |
| PTK-040-R8X16-22M6P2-0C160E | 1.6 | 103.151 | подрез | 198.3 | 32.5 | 0.62 | 1.18 | 0.05 | 7.91 | нет |
| PTK-040-R8X16-22M6P2-0343C4 | 1.6 | 103.2 | подрез | 198.4 | 32.4 | 0.62 | 1.18 | 0.054 | 7.92 | нет |
| PTK-040-R8X8-22M6P2-95EB68 | 1.6 | 103.151 | подрез | 198.3 | 32.5 | 0.62 | 1.18 | 0.05 | 7.91 | нет |
| PTK-040-R8X8-22M6P2-201151 | 1.6 | 103.2 | подрез | 198.4 | 32.4 | 0.62 | 1.18 | 0.054 | 7.92 | нет |
| PTK-040-R7X20-22M6P2-76A018 | 1.4 | 90.335 | подрез | 173.67 | 32.4 | 0.62 | 1.18 | 0.05 | 6.93 | нет |
| PTK-040-R7X20-22M6P2-F1EFD7 | 1.4 | 90.35 | подрез | 173.7 | 32.4 | 0.62 | 1.18 | 0.051 | 6.94 | нет |
| PTK-040-R6X6-22M6P2-650479 | 1.2 | 77.518 | подрез | 149.04 | 32.4 | 0.62 | 1.18 | 0.05 | 5.96 | нет |
| PTK-040-R6X6-22M6P2-E2D3CD | 1.2 | 77.55 | подрез | 149.1 | 32.4 | 0.62 | 1.18 | 0.053 | 5.96 | OK |
| PTK-040-R5X8-22M6P2-A1C64A | 1.0 | 65.0 | подрез | 125.0 | 32.2 | 0.62 | 1.18 | 0.074 | 5.03 | OK |
| PTK-040-R5X8-22M6P2-5D1664 | 1.0 | 64.75 | подрез | 124.5 | 32.3 | 0.62 | 1.18 | 0.054 | 4.99 | OK |
| PTK-040-R5X5-22M6P2-3F1C4A | 1.0 | 65.0 | подрез | 125.0 | 32.2 | 0.62 | 1.18 | 0.074 | 5.03 | OK |
| PTK-040-R5X5-22M6P2-2DF37C | 1.0 | 64.75 | подрез | 124.5 | 32.3 | 0.62 | 1.18 | 0.054 | 4.99 | OK |
| PTK-040-R3X8-10M5P2-C1B79F | 0.6 | 40.5 | подрез | 78.0 | 31.3 | 0.59 | 1.17 | 0.169 | 3.25 | OK |
| PTK-040-R3X8-10M5P2-4EE27D | 0.6 | 39.1 | подрез | 75.2 | 32.2 | 0.61 | 1.18 | 0.053 | 3.03 | OK |
| PTK-040-B3-10M5P2-80BC3D | 0.6 | 39.1 | подрез | 75.2 | 32.2 | 0.61 | 1.18 | 0.053 | 3.03 | OK |
| PTK-050-R8X16-22M6P2-986467 | 1.6 | 128.606 | подрез | 249.21 | 32.4 | 0.62 | 1.18 | 0.05 | 7.93 | нет |
| PTK-050-R8X16-22M6P2-0C64BB | 1.6 | 128.65 | подрез | 249.3 | 32.4 | 0.62 | 1.18 | 0.053 | 7.93 | нет |
| PTK-050-R8X8-22M6P2-84F4C5 | 1.6 | 128.606 | подрез | 249.21 | 32.4 | 0.62 | 1.18 | 0.05 | 7.93 | нет |
| PTK-050-R8X8-22M6P2-ED6334 | 1.6 | 128.65 | подрез | 249.3 | 32.4 | 0.62 | 1.18 | 0.053 | 7.93 | нет |
| PTK-050-R7X20-22M6P2-CE97E4 | 1.4 | 112.627 | подрез | 218.25 | 32.4 | 0.62 | 1.18 | 0.05 | 6.95 | нет |
| PTK-050-R7X20-22M6P2-DD4090 | 1.4 | 112.65 | подрез | 218.3 | 32.4 | 0.62 | 1.18 | 0.051 | 6.95 | нет |
| PTK-050-R6X6-22M6P2-4DCB40 | 1.2 | 96.648 | подрез | 187.3 | 32.3 | 0.62 | 1.18 | 0.05 | 5.97 | нет |
| PTK-050-R6X6-22M6P2-3E50C6 | 1.2 | 96.65 | подрез | 187.3 | 32.3 | 0.62 | 1.18 | 0.05 | 5.97 | нет |
| PTK-050-R5X8-22M6P2-1D56A2 | 1.0 | 80.669 | подрез | 156.34 | 32.3 | 0.62 | 1.18 | 0.05 | 4.99 | нет |
| PTK-050-R5X8-22M6P2-7B07E5 | 1.0 | 80.7 | подрез | 156.4 | 32.3 | 0.62 | 1.18 | 0.052 | 5.0 | OK |
| PTK-050-R5X5-22M6P2-20A347 | 1.0 | 80.669 | подрез | 156.34 | 32.3 | 0.62 | 1.18 | 0.05 | 4.99 | нет |
| PTK-050-R5X5-22M6P2-1AD71F | 1.0 | 80.7 | подрез | 156.4 | 32.3 | 0.62 | 1.18 | 0.052 | 5.0 | OK |
| PTK-050-R3X8-10M5P2-E6B80C | 0.6 | 49.0 | подрез | 95.0 | 32.0 | 0.61 | 1.18 | 0.069 | 3.07 | OK |
| PTK-050-R3X8-10M5P2-4AFC2C | 0.6 | 48.75 | подрез | 94.5 | 32.1 | 0.62 | 1.18 | 0.053 | 3.04 | OK |
| PTK-050-B3-10M5P2-7415AD | 0.6 | 48.75 | подрез | 94.5 | 32.1 | 0.62 | 1.18 | 0.053 | 3.04 | OK |
| PTK-063-R8X16-22M6P2-DDA520 | 1.6 | 161.697 | подрез | 315.39 | 32.3 | 0.62 | 1.18 | 0.05 | 7.94 | нет |
| PTK-063-R8X16-22M6P2-DA30EE | 1.6 | 161.7 | подрез | 315.4 | 32.3 | 0.62 | 1.18 | 0.05 | 7.94 | нет |
| PTK-063-R8X8-22M6P2-C47FC5 | 1.6 | 161.697 | подрез | 315.39 | 32.3 | 0.62 | 1.18 | 0.05 | 7.94 | нет |
| PTK-063-R8X8-22M6P2-D0C75B | 1.6 | 161.7 | подрез | 315.4 | 32.3 | 0.62 | 1.18 | 0.05 | 7.94 | нет |
| PTK-063-R7X20-22M6P2-87BC1B | 1.4 | 141.608 | подрез | 276.22 | 32.3 | 0.62 | 1.18 | 0.05 | 6.96 | нет |
| PTK-063-R7X20-22M6P2-E7C184 | 1.4 | 141.65 | подрез | 276.3 | 32.3 | 0.62 | 1.18 | 0.052 | 6.97 | нет |
| PTK-063-R6X6-22M6P2-F361EE | 1.2 | 121.518 | подрез | 237.04 | 32.3 | 0.62 | 1.18 | 0.05 | 5.98 | нет |
| PTK-063-R6X6-22M6P2-7D2FF2 | 1.2 | 121.55 | подрез | 237.1 | 32.3 | 0.62 | 1.18 | 0.052 | 5.99 | нет |
| PTK-063-R5X8-22M6P2-ECA0D7 | 1.0 | 101.428 | подрез | 197.86 | 32.3 | 0.62 | 1.18 | 0.05 | 5.0 | нет |
| PTK-063-R5X8-22M6P2-51F025 | 1.0 | 101.45 | подрез | 197.9 | 32.2 | 0.62 | 1.18 | 0.051 | 5.0 | нет |
| PTK-063-R5X5-22M6P2-A81518 | 1.0 | 101.428 | подрез | 197.86 | 32.3 | 0.62 | 1.18 | 0.05 | 5.0 | нет |
| PTK-063-R5X5-22M6P2-64F71F | 1.0 | 101.45 | подрез | 197.9 | 32.2 | 0.62 | 1.18 | 0.051 | 5.0 | нет |
| PTK-063-R3X8-22M6P2-BDBB72 | 0.6 | 61.5 | подрез | 120.0 | 32.0 | 0.61 | 1.18 | 0.063 | 3.07 | OK |
| PTK-063-R3X8-22M6P2-2D6433 | 0.6 | 61.25 | подрез | 119.5 | 32.1 | 0.62 | 1.18 | 0.05 | 3.04 | OK |
| PTK-063-B3-22M6P2-240036 | 0.6 | 61.25 | подрез | 119.5 | 32.1 | 0.62 | 1.18 | 0.05 | 3.04 | OK |
| PTK-080-R8X16-22M6P2-6A3AD7 | 1.6 | 204.971 | подрез | 401.94 | 32.3 | 0.62 | 1.18 | 0.05 | 7.96 | нет |
| PTK-080-R8X16-22M6P2-075C32 | 1.6 | 205.0 | подрез | 402.0 | 32.3 | 0.62 | 1.18 | 0.051 | 7.96 | нет |
| PTK-080-R8X8-22M6P2-8B2D21 | 1.6 | 204.971 | подрез | 401.94 | 32.3 | 0.62 | 1.18 | 0.05 | 7.96 | нет |
| PTK-080-R8X8-22M6P2-AEA3B3 | 1.6 | 205.0 | подрез | 402.0 | 32.3 | 0.62 | 1.18 | 0.051 | 7.96 | нет |
| PTK-080-R7X20-22M6P2-7CFD36 | 1.4 | 179.506 | подрез | 352.01 | 32.3 | 0.62 | 1.18 | 0.05 | 6.97 | нет |
| PTK-080-R7X20-22M6P2-CAEAE8 | 1.4 | 179.55 | подрез | 352.1 | 32.3 | 0.62 | 1.18 | 0.052 | 6.98 | нет |
| PTK-080-R6X6-22M6P2-64AA97 | 1.2 | 154.04 | подрез | 302.08 | 32.3 | 0.62 | 1.18 | 0.05 | 5.99 | нет |
| PTK-080-R6X6-22M6P2-11A46B | 1.2 | 154.05 | подрез | 302.1 | 32.3 | 0.62 | 1.18 | 0.05 | 5.99 | нет |
| PTK-080-R5X8-22M6P2-81E92A | 1.0 | 128.574 | подрез | 252.15 | 32.2 | 0.62 | 1.18 | 0.05 | 5.01 | нет |
| PTK-080-R5X8-22M6P2-C662FE | 1.0 | 128.6 | подрез | 252.2 | 32.2 | 0.62 | 1.18 | 0.051 | 5.01 | нет |
| PTK-080-R5X5-22M6P2-7AB35A | 1.0 | 128.574 | подрез | 252.15 | 32.2 | 0.62 | 1.18 | 0.05 | 5.01 | нет |
| PTK-080-R5X5-22M6P2-15CFA2 | 1.0 | 128.6 | подрез | 252.2 | 32.2 | 0.62 | 1.18 | 0.051 | 5.01 | нет |
| PTK-080-R3X8-22M6P2-A0F08F | 0.6 | 77.64 | подрез | 152.28 | 32.0 | 0.62 | 1.18 | 0.05 | 3.04 | нет |
| PTK-080-R3X8-22M6P2-5063C8 | 0.6 | 77.65 | подрез | 152.3 | 32.0 | 0.62 | 1.18 | 0.05 | 3.05 | OK |
| PTK-080-B3-22M6P2-F9ADAB | 0.6 | 77.65 | подрез | 152.3 | 32.0 | 0.62 | 1.18 | 0.05 | 3.05 | OK |
| PTK-100-R8X16-22M6P2-AE37A5 | 1.6 | 255.882 | подрез | 503.76 | 32.3 | 0.63 | 1.18 | 0.05 | 7.96 | нет |
| PTK-100-R8X16-22M6P2-69977F | 1.6 | 255.9 | подрез | 503.8 | 32.3 | 0.63 | 1.18 | 0.051 | 7.97 | нет |
| PTK-100-R8X8-22M6P2-86E7F0 | 1.6 | 255.882 | подрез | 503.76 | 32.3 | 0.63 | 1.18 | 0.05 | 7.96 | нет |
| PTK-100-R8X8-22M6P2-4C9144 | 1.6 | 255.9 | подрез | 503.8 | 32.3 | 0.63 | 1.18 | 0.051 | 7.97 | нет |
| PTK-100-R7X20-22M6P2-0B73A4 | 1.4 | 224.092 | подрез | 441.18 | 32.3 | 0.62 | 1.18 | 0.05 | 6.98 | нет |
| PTK-100-R7X20-22M6P2-A8E08E | 1.4 | 224.1 | подрез | 441.2 | 32.3 | 0.62 | 1.18 | 0.05 | 6.98 | нет |
| PTK-100-R6X6-22M6P2-0A6BA9 | 1.2 | 192.301 | подрез | 378.6 | 32.2 | 0.62 | 1.18 | 0.05 | 6.0 | нет |
| PTK-100-R6X6-22M6P2-0E270A | 1.2 | 192.35 | подрез | 378.7 | 32.2 | 0.62 | 1.18 | 0.052 | 6.0 | нет |
| PTK-100-R5X8-22M6P2-12DB1E | 1.0 | 160.511 | подрез | 316.02 | 32.2 | 0.62 | 1.18 | 0.05 | 5.01 | нет |
| PTK-100-R5X8-22M6P2-EF2819 | 1.0 | 160.55 | подрез | 316.1 | 32.2 | 0.62 | 1.18 | 0.051 | 5.02 | нет |
| PTK-100-R5X5-22M6P2-5887FF | 1.0 | 160.511 | подрез | 316.02 | 32.2 | 0.62 | 1.18 | 0.05 | 5.01 | нет |
| PTK-100-R5X5-22M6P2-C7A9A4 | 1.0 | 160.55 | подрез | 316.1 | 32.2 | 0.62 | 1.18 | 0.051 | 5.02 | нет |
| PTK-100-R3X8-22M6P2-CC7493 | 0.6 | 96.927 | подрез | 190.85 | 32.0 | 0.62 | 1.18 | 0.05 | 3.05 | нет |
| PTK-100-R3X8-22M6P2-512671 | 0.6 | 96.95 | подрез | 190.9 | 32.0 | 0.62 | 1.18 | 0.051 | 3.05 | нет |
| PTK-100-B3-22M6P2-2D98E7 | 0.6 | 96.95 | подрез | 190.9 | 32.0 | 0.62 | 1.18 | 0.051 | 3.05 | нет |

## Передаточные числа u > 100 (Д-11)

Одноступенчатый ПТК считается только для u ≤ 100 (Д-11). Для больших u применяется двухступенчатая схема; каждая ступень рассчитывается этим же калькулятором как самостоятельный редуктор.

| u | u1 | u2 | u1·u2 | Точно |
|---|---|---|---|---|
| 101 | 10 | 10 | 100 | нет, ближайшее |
| 120 | 12 | 10 | 120 | да |
| 150 | 15 | 10 | 150 | да |
| 200 | 20 | 10 | 200 | да |
| 300 | 20 | 15 | 300 | да |
| 500 | 25 | 20 | 500 | да |
| 1000 | 40 | 25 | 1000 | да |
| 2500 | 50 | 50 | 2500 | да |

## Детали .02 сепаратор, .03 эксцентрик (Д-46)

Балансировка ряда (Д-36): U = U_диска + m_подш·aω + (n/2)·m_тела·aω; отверстия — со стороны
эксцентриситета. Пазы шпонки — по рядам, отсюда варианты .03A…; чертежи — `python -m egm.cad <ID>.03A`.

| ID | Генератор | Dэ × t, мм | Пазы шпонки, ° | U, г·мм | Отв. балансировки | Остаток, г·мм | Сепаратор dс / Dс × B | Окна w × h | Перемычка | Шайбы .05 dвн / D, h торец / между |
|---|---|---|---|---|---|---|---|---|---|---|
| PTK-010-R8X16-10M5P2-8B0907 | 61807 | 35 × 7 | 45, 315, 225, 135 | 158.88 | 2×Ø12.7, r 11.4 | 32.02 | 51.48 / 58.52 × 69 | 8.05 × 16.05 | 7.858 | 67.2 / 94, 1 / 1 |
| PTK-010-R8X16-10M5P2-8F60AF | эксцентрик | 45.7 × 16 | 45, 315, 225, 135 | 380.14 | 1×Ø15.7, r 15.6 | 0.82 | 50.18 / 57.22 × 69 | 8.05 × 16.05 | 7.456 | 65.9 / 92, 1 / 1 |
| PTK-010-R8X8-10M5P2-070C3C | 61807 | 35 × 7 | 45, 315, 225, 135 | 133.62 | 2×Ø12.7, r 11.4 | 6.76 | 51.48 / 58.52 × 37 | 8.05 × 8.05 | 7.858 | 67.2 / 94, 1 / 1 |
| PTK-010-R8X8-10M5P2-FF6078 | эксцентрик | 45.7 × 8 | 45, 315, 225, 135 | 190.07 | 1×Ø15.7, r 15.6 | 0.41 | 50.18 / 57.22 × 37 | 8.05 × 8.05 | 7.456 | 65.9 / 92, 1 / 1 |
| PTK-010-R7X20-10M5P2-7D60D6 | 61806 | 30 × 7 | 45, 315, 225, 135 | 114.94 | 2×Ø10.1, r 10.09 | 40.75 | 45.92 / 52.08 × 85 | 7.05 × 20.05 | 7.14 | 59.8 / 86, 1 / 1 |
| PTK-010-R7X20-10M5P2-2EA179 | эксцентрик | 40 × 20 | 45, 315, 225, 135 | 318.5 | 3×Ø7.6, r 16.39 | 0.44 | 43.92 / 50.08 × 85 | 7.05 × 20.05 | 6.522 | 57.8 / 84, 1 / 1 |
| PTK-010-R6X6-10M5P2-B73626 | 61805 | 25 × 7 | 45, 315, 225, 135 | 53.84 | 3×Ø7.1, r 8.57 | 14.57 | 40.36 / 45.64 × 33 | 6.05 × 6.05 | 6.422 | 52.4 / 79, 1.5 / 2 |
| PTK-010-R6X6-10M5P2-8AD44D | эксцентрик | 34.3 × 6 | 45, 315, 225, 135 | 60.22 | 3×Ø6.6, r 13.85 | -0.02 | 37.66 / 42.94 × 29 | 6.05 × 6.05 | 5.588 | 49.7 / 76, 1 / 1 |
| PTK-010-R5X8-10M5P2-2ECBA4 | 61804 | 20 × 7 | 45, 315, 225, 135 | 32.85 | 3×Ø4.6, r 7.38 | 16.52 | 34.8 / 39.2 × 37 | 5.05 × 8.05 | 5.704 | 45 / 71, 1 / 1 |
| PTK-010-R5X8-10M5P2-D97113 | эксцентрик | 28.7 × 8 | 45, 315, 225, 135 | 46.79 | 3×Ø5.6, r 11.37 | -0.04 | 31.5 / 35.9 × 37 | 5.05 × 8.05 | 4.684 | 41.7 / 68, 1 / 1 |
| PTK-010-R5X5-10M5P2-979E07 | 61804 | 20 × 7 | 45, 315, 225, 135 | 30.54 | 3×Ø4.6, r 7.38 | 14.2 | 34.8 / 39.2 × 33 | 5.05 × 5.05 | 5.704 | 45 / 71, 2 / 3 |
| PTK-010-R5X5-10M5P2-FDAB21 | эксцентрик | 28.7 × 5 | 45, 315, 225, 135 | 29.25 | 3×Ø5.6, r 11.37 | -0.03 | 31.5 / 35.9 × 25 | 5.05 × 5.05 | 4.684 | 41.7 / 68, 1 / 1 |
| PTK-010-R3X8-10M3P2-A16061 | 61800 | 10 × 5 | 45, 315, 225, 135 | 4.87 | нет | 4.87 | 20.68 / 23.32 × 37 | 3.05 × 8.05 | 3.34 | 27.2 / 49, 1 / 1 |
| PTK-010-R3X8-10M3P2-1A947D | эксцентрик | 17.3 × 8 | 45, 315, 225, 135 | 10.19 | 3×Ø3.1, r 6.57 | 2.06 | 18.98 / 21.62 × 37 | 3.05 × 8.05 | 2.815 | 25.5 / 48, 1 / 1 |
| PTK-010-B3-10M3P2-C587B2 | эксцентрик | 17.3 × 3 | 45, 315, 225, 135 | 3.65 | 3×Ø3.1, r 6.57 | 0.61 | 18.98 / 21.62 × 17 | 3.05 × 3.05 | 2.815 | 25.5 / 48, 1 / 1 |
| PTK-016-R8X16-10M5P2-079658 | 61812 | 60 × 10 | 45, 315, 225, 135 | 521.7 | 3×Ø11.1, r 24.85 | 0.15 | 82.48 / 89.52 × 69 | 8.05 × 16.05 | 8.041 | 98.2 / 125, 1 / 1 |
| PTK-016-R8X16-10M5P2-EBEF90 | эксцентрик | 76.2 × 16 | 45, 315, 225, 135 | 997.26 | 1×Ø18.5, r 29.45 | 2.98 | 80.68 / 87.72 × 69 | 8.05 × 16.05 | 7.69 | 96.4 / 123, 1 / 1 |
| PTK-016-R8X8-10M5P2-519C3A | 61812 | 60 × 10 | 45, 315, 225, 135 | 481.29 | 1×Ø19.3, r 20.95 | 0.17 | 82.48 / 89.52 × 45 | 8.05 × 8.05 | 8.041 | 98.2 / 125, 2 / 3 |
| PTK-016-R8X8-10M5P2-999A95 | эксцентрик | 76.2 × 8 | 45, 315, 225, 135 | 498.63 | 1×Ø18.5, r 29.45 | 1.49 | 80.68 / 87.72 × 37 | 8.05 × 8.05 | 7.69 | 96.4 / 123, 1 / 1 |
| PTK-016-R7X20-10M5P2-A6FA18 | 61811 | 55 × 9 | 45, 315, 225, 135 | 361.37 | 1×Ø18.7, r 18.55 | 1.43 | 75.92 / 82.08 × 85 | 7.05 × 20.05 | 7.761 | 89.8 / 116, 1 / 1 |
| PTK-016-R7X20-10M5P2-B6A6DE | эксцентрик | 66.7 × 20 | 45, 315, 225, 135 | 835.69 | 2×Ø11.1, r 28.16 | 0.01 | 70.62 / 76.78 × 85 | 7.05 × 20.05 | 6.727 | 84.5 / 111, 1 / 1 |
| PTK-016-R6X6-10M5P2-C54A11 | 61809 | 45 × 7 | 45, 315, 225, 135 | 141.93 | 1×Ø14.6, r 15.4 | 0.26 | 61.36 / 66.64 × 33 | 6.05 × 6.05 | 5.921 | 73.4 / 100, 1.5 / 2 |
| PTK-016-R6X6-10M5P2-1E58F3 | эксцентрик | 57.3 × 6 | 45, 315, 225, 135 | 158.53 | 1×Ø14, r 21.85 | 0.11 | 60.66 / 65.94 × 29 | 6.05 × 6.05 | 5.784 | 72.7 / 99, 1 / 1 |
| PTK-016-R5X8-10M5P2-66659B | 61808 | 40 × 7 | 45, 315, 225, 135 | 95.59 | 3×Ø7, r 16.37 | 0.01 | 54.8 / 59.2 × 37 | 5.05 × 8.05 | 5.641 | 65 / 91, 1 / 1 |
| PTK-016-R5X8-10M5P2-424AEF | эксцентрик | 47.8 × 8 | 45, 315, 225, 135 | 122.56 | 2×Ø8, r 19.87 | 0.37 | 50.6 / 55 × 37 | 5.05 × 8.05 | 4.822 | 60.8 / 87, 1 / 1 |
| PTK-016-R5X5-10M5P2-96A041 | 61808 | 40 × 7 | 45, 315, 225, 135 | 91.89 | 1×Ø12.4, r 13.8 | 0.32 | 54.8 / 59.2 × 33 | 5.05 × 5.05 | 5.641 | 65 / 91, 2 / 3 |
| PTK-016-R5X5-10M5P2-303BBF | эксцентрик | 47.8 × 5 | 45, 315, 225, 135 | 76.6 | 2×Ø8, r 19.87 | 0.23 | 50.6 / 55 × 25 | 5.05 × 5.05 | 4.822 | 60.8 / 87, 1 / 1 |
| PTK-016-R3X8-10M5P2-7841A0 | 61804 | 20 × 7 | 45, 315, 225, 135 | 18.14 | 3×Ø4.4, r 7.22 | 3.42 | 33.68 / 36.32 × 37 | 3.05 × 8.05 | 3.521 | 40.2 / 67, 1 / 1 |
| PTK-016-R3X8-10M5P2-4F895B | эксцентрик | 28.9 × 8 | 45, 315, 225, 135 | 26.85 | 3×Ø4, r 11.99 | 0.11 | 30.58 / 33.22 × 37 | 3.05 × 8.05 | 2.916 | 37.1 / 64, 1 / 1 |
| PTK-016-B3-10M5P2-40D6F0 | эксцентрик | 28.9 × 3 | 45, 315, 225, 135 | 9.8 | 1×Ø7.1, r 10.5 | 0.01 | 30.58 / 33.22 × 17 | 3.05 × 3.05 | 2.916 | 37.1 / 64, 1 / 1 |
| PTK-020-R8X16-22M6P2-4A32DD | 61816 | 80 × 10 | 45, 315, 225, 135 | 856.64 | 1×Ø21.6, r 29.8 | -0.56 | 104.48 / 111.52 × 69 | 8.05 × 16.05 | 8.294 | 120.2 / 149, 1 / 1 |
| PTK-020-R8X16-22M6P2-0377C3 | эксцентрик | 96.5 × 16 | 45, 315, 225, 135 | 1570.8 | 2×Ø13.9, r 41.87 | 0.23 | 100.98 / 108.02 × 69 | 8.05 × 16.05 | 7.747 | 116.7 / 145, 1 / 1 |
| PTK-020-R8X8-22M6P2-656315 | 61816 | 80 × 10 | 45, 315, 225, 135 | 806.14 | 1×Ø20.8, r 30.2 | 0.58 | 104.48 / 111.52 × 45 | 8.05 × 8.05 | 8.294 | 120.2 / 149, 2 / 3 |
| PTK-020-R8X8-22M6P2-7C7CC0 | эксцентрик | 96.5 × 8 | 45, 315, 225, 135 | 785.4 | 2×Ø13.9, r 41.87 | 0.12 | 100.98 / 108.02 × 37 | 8.05 × 8.05 | 7.747 | 116.7 / 145, 1 / 1 |
| PTK-020-R7X20-10M5P2-388229 | 61813 | 65 × 10 | 45, 315, 225, 135 | 539.9 | 1×Ø19.4, r 23.2 | 1.57 | 88.92 / 95.08 × 85 | 7.05 × 20.05 | 6.86 | 102.8 / 129, 1 / 1 |
| PTK-020-R7X20-10M5P2-EAC535 | эксцентрик | 84.6 × 20 | 45, 315, 225, 135 | 1320.13 | 2×Ø12.2, r 36.57 | -0.17 | 88.52 / 94.68 × 85 | 7.05 × 20.05 | 6.798 | 102.4 / 129, 1 / 1 |
| PTK-020-R6X6-10M5P2-AFCBDF | 61812 | 60 × 10 | 45, 315, 225, 135 | 346.65 | 1×Ø15.9, r 22.25 | -0.16 | 81.36 / 86.64 × 45 | 6.05 × 6.05 | 6.678 | 93.4 / 120, 3 / 5 |
| PTK-020-R6X6-10M5P2-CDD24C | эксцентрик | 72.6 × 6 | 45, 315, 225, 135 | 249.95 | 1×Ø15.3, r 28.85 | 0.13 | 75.96 / 81.24 × 29 | 6.05 × 6.05 | 5.833 | 88 / 114, 1 / 1 |
| PTK-020-R5X8-10M5P2-04E9EC | 61810 | 50 × 7 | 45, 315, 225, 135 | 146.28 | 2×Ø9.3, r 20.31 | -0.39 | 67.8 / 72.2 × 37 | 5.05 × 8.05 | 5.556 | 78 / 104, 1 / 1 |
| PTK-020-R5X8-10M5P2-4FDD6C | эксцентрик | 60.6 × 8 | 45, 315, 225, 135 | 193.46 | 1×Ø12.8, r 23.9 | 0.32 | 63.4 / 67.8 × 37 | 5.05 × 8.05 | 4.868 | 73.6 / 100, 1 / 1 |
| PTK-020-R5X5-10M5P2-0A0407 | 61810 | 50 × 7 | 45, 315, 225, 135 | 141.66 | 1×Ø13.4, r 18.3 | -0.16 | 67.8 / 72.2 × 33 | 5.05 × 5.05 | 5.556 | 78 / 104, 2 / 3 |
| PTK-020-R5X5-10M5P2-67323B | эксцентрик | 60.6 × 5 | 45, 315, 225, 135 | 120.91 | 1×Ø12.8, r 23.9 | 0.2 | 63.4 / 67.8 × 25 | 5.05 × 5.05 | 4.868 | 73.6 / 100, 1 / 1 |
| PTK-020-R3X8-10M5P2-DBE2F2 | 61805 | 25 × 7 | 45, 315, 225, 135 | 25.59 | 3×Ø4.9, r 9.53 | -0.25 | 38.68 / 41.32 × 37 | 3.05 × 8.05 | 3.001 | 45.2 / 72, 1 / 1 |
| PTK-020-R3X8-10M5P2-248D14 | эксцентрик | 36.6 × 8 | 45, 315, 225, 135 | 42.31 | 1×Ø7.8, r 14 | 0.29 | 38.28 / 40.92 × 37 | 3.05 × 8.05 | 2.938 | 44.8 / 71, 1 / 1 |
| PTK-020-B3-10M5P2-74A23C | эксцентрик | 36.6 × 3 | 45, 315, 225, 135 | 15.53 | 3×Ø4.3, r 15.71 | 0.03 | 38.28 / 40.92 × 17 | 3.05 × 3.05 | 2.938 | 44.8 / 71, 1 / 1 |
| PTK-025-R8X16-22M6P2-754C59 | 61820 | 100 × 13 | 45, 315, 225, 135 | 1661.14 | 3×Ø12.7, r 44.17 | 3.06 | 129.48 / 136.52 × 69 | 8.05 × 16.05 | 8.178 | 145.2 / 174, 1 / 1 |
| PTK-025-R8X16-22M6P2-0F2F2C | эксцентрик | 122 × 16 | 45, 315, 225, 135 | 2475.46 | 1×Ø22.3, r 50.45 | 0.6 | 126.48 / 133.52 × 69 | 8.05 × 16.05 | 7.802 | 142.2 / 171, 1 / 1 |
| PTK-025-R8X8-22M6P2-2C1E5B | 61820 | 100 × 13 | 45, 315, 225, 135 | 1598 | 2×Ø15.4, r 42.86 | -1.29 | 129.48 / 136.52 × 57 | 8.05 × 8.05 | 8.178 | 145.2 / 174, 3.5 / 6 |
| PTK-025-R8X8-22M6P2-391A86 | эксцентрик | 122 × 8 | 45, 315, 225, 135 | 1237.73 | 1×Ø22.3, r 50.45 | 0.3 | 126.48 / 133.52 × 37 | 8.05 × 8.05 | 7.802 | 142.2 / 171, 1 / 1 |
| PTK-025-R7X20-22M6P2-1327C5 | 61817 | 85 × 13 | 45, 315, 225, 135 | 1107.91 | 1×Ø20.6, r 32.6 | -0.89 | 113.92 / 120.08 × 85 | 7.05 × 20.05 | 7.228 | 127.8 / 156, 1 / 1 |
| PTK-025-R7X20-22M6P2-772B35 | эксцентрик | 106.8 × 20 | 45, 315, 225, 135 | 2074.8 | 3×Ø10.9, r 48.3 | -5.06 | 110.72 / 116.88 × 85 | 7.05 × 20.05 | 6.827 | 124.6 / 153, 1 / 1 |
| PTK-025-R6X6-10M5P2-505845 | 61815 | 75 × 10 | 45, 315, 225, 135 | 524.18 | 1×Ø17.1, r 29.15 | -1.34 | 98.36 / 103.64 × 45 | 6.05 × 6.05 | 6.278 | 110.4 / 137, 3 / 5 |
| PTK-025-R6X6-10M5P2-D85760 | эксцентрик | 91.7 × 6 | 45, 315, 225, 135 | 393.25 | 1×Ø16.8, r 37.65 | 0.16 | 95.06 / 100.34 × 29 | 6.05 × 6.05 | 5.864 | 107.1 / 134, 1 / 1 |
| PTK-025-R5X8-10M5P2-2182BD | 61812 | 60 × 10 | 45, 315, 225, 135 | 290.97 | 1×Ø14.4, r 22.8 | -0.52 | 80.8 / 85.2 × 45 | 5.05 × 8.05 | 5.077 | 91 / 117, 2 / 3 |
| PTK-025-R5X8-10M5P2-E7AF17 | эксцентрик | 76.6 × 8 | 45, 315, 225, 135 | 304.82 | 2×Ø9.7, r 33.43 | -1.47 | 79.4 / 83.8 × 37 | 5.05 × 8.05 | 4.901 | 89.6 / 116, 1 / 1 |
| PTK-025-R5X5-10M5P2-01744D | 61812 | 60 × 10 | 45, 315, 225, 135 | 285.19 | 2×Ø9.7, r 25.12 | 0.43 | 80.8 / 85.2 × 45 | 5.05 × 5.05 | 5.077 | 91 / 117, 3.5 / 6 |
| PTK-025-R5X5-10M5P2-AC2DD3 | эксцентрик | 76.6 × 5 | 45, 315, 225, 135 | 190.51 | 2×Ø9.7, r 33.43 | -0.92 | 79.4 / 83.8 × 25 | 5.05 × 5.05 | 4.901 | 89.6 / 116, 1 / 1 |
| PTK-025-R3X8-10M5P2-70E7B4 | 61807 | 35 × 7 | 45, 315, 225, 135 | 43.97 | 1×Ø9, r 12.6 | -0.08 | 48.68 / 51.32 × 37 | 3.05 × 8.05 | 3.051 | 55.2 / 82, 1 / 1 |
| PTK-025-R3X8-10M5P2-A700AA | эксцентрик | 46.3 × 8 | 45, 315, 225, 135 | 66.77 | 2×Ø5.9, r 19.79 | -0.15 | 47.98 / 50.62 × 37 | 3.05 × 8.05 | 2.963 | 54.5 / 81, 1 / 1 |
| PTK-025-B3-10M5P2-7EC60B | эксцентрик | 46.3 × 3 | 45, 315, 225, 135 | 24.62 | 1×Ø8.5, r 18.5 | -0.1 | 47.98 / 50.62 × 17 | 3.05 × 3.05 | 2.963 | 54.5 / 81, 1 / 1 |
| PTK-032-R8X16-10M3P2-B06A75 | эксцентрик | 157.6 × 16 | 45, 315, 225, 135 | 4081.86 | 3×Ø13.9, r 72.41 | 0.02 | 162.08 / 169.12 × 69 | 8.05 × 16.05 | 7.837 | 177.8 / 200, 1 / 1 |
| PTK-032-R8X8-10M3P2-8F3875 | эксцентрик | 157.6 × 8 | 45, 315, 225, 135 | 2040.93 | 3×Ø13.9, r 72.41 | 0.01 | 162.08 / 169.12 × 37 | 8.05 × 8.05 | 7.837 | 177.8 / 200, 1 / 1 |
| PTK-032-R7X20-22M6P2-BAC1EE | 61822 | 110 × 16 | 45, 315, 225, 135 | 2168.93 | 1×Ø22.3, r 44.25 | -1.78 | 143.92 / 150.08 × 85 | 7.05 × 20.05 | 7.057 | 157.8 / 186, 1 / 1 |
| PTK-032-R7X20-22M6P2-1A4385 | эксцентрик | 138.1 × 20 | 45, 315, 225, 135 | 3427.68 | 1×Ø21.8, r 58.55 | -3.38 | 142.02 / 148.18 × 85 | 7.05 × 20.05 | 6.87 | 155.9 / 185, 1 / 1 |
| PTK-032-R6X6-22M6P2-E942C3 | 61819 | 95 × 13 | 45, 315, 225, 135 | 1074.53 | 1×Ø18.7, r 38.35 | -0.33 | 123.36 / 128.64 × 57 | 6.05 × 6.05 | 6.041 | 135.4 / 164, 4.5 / 8 |
| PTK-032-R6X6-22M6P2-D4BE19 | эксцентрик | 118.5 × 6 | 45, 315, 225, 135 | 648.91 | 1×Ø18.7, r 50.1 | 0.83 | 121.86 / 127.14 × 29 | 6.05 × 6.05 | 5.894 | 133.9 / 163, 1 / 1 |
| PTK-032-R5X8-22M6P2-19B83D | 61816 | 80 × 10 | 45, 315, 225, 135 | 492 | 2×Ø10.8, r 34.58 | 1.94 | 102.8 / 107.2 × 45 | 5.05 × 8.05 | 5.026 | 113 / 142, 2 / 3 |
| PTK-032-R5X8-10M5P2-2CBB5C | эксцентрик | 98.9 × 8 | 45, 315, 225, 135 | 502.17 | 2×Ø10.8, r 44.04 | 0.01 | 101.7 / 106.1 × 37 | 5.05 × 8.05 | 4.918 | 111.9 / 138, 1 / 1 |
| PTK-032-R5X5-22M6P2-793017 | 61816 | 80 × 10 | 45, 315, 225, 135 | 484.6 | 1×Ø15.6, r 32.2 | 1.47 | 102.8 / 107.2 × 45 | 5.05 × 5.05 | 5.026 | 113 / 142, 3.5 / 6 |
| PTK-032-R5X5-10M5P2-3F07B6 | эксцентрик | 98.9 × 5 | 45, 315, 225, 135 | 313.85 | 2×Ø10.8, r 44.04 | 0.01 | 101.7 / 106.1 × 25 | 5.05 × 5.05 | 4.918 | 111.9 / 138, 1 / 1 |
| PTK-032-R3X8-10M5P2-1E1E34 | 61810 | 50 × 7 | 45, 315, 225, 135 | 84.63 | 1×Ø10, r 19.6 | 0.04 | 66.68 / 69.32 × 37 | 3.05 × 8.05 | 3.486 | 73.2 / 100, 1 / 1 |
| PTK-032-R3X8-10M5P2-7AE1CB | эксцентрик | 59.8 × 8 | 45, 315, 225, 135 | 110.09 | 1×Ø9.5, r 24.75 | -0.08 | 61.48 / 64.12 × 37 | 3.05 × 8.05 | 2.976 | 68 / 94, 1 / 1 |
| PTK-032-B3-10M5P2-DEDB0E | эксцентрик | 59.8 × 3 | 45, 315, 225, 135 | 40.75 | 2×Ø6.5, r 26.24 | 0.16 | 61.48 / 64.12 × 17 | 3.05 × 3.05 | 2.976 | 68 / 94, 1 / 1 |
| PTK-040-R6X6-22M6P2-E2D3CD | эксцентрик | 149.1 × 6 | 45, 315, 225, 135 | 1018.8 | 3×Ø11.6, r 68.92 | 1.08 | 152.46 / 157.74 × 29 | 6.05 × 6.05 | 5.912 | 164.5 / 193, 1 / 1 |
| PTK-040-R5X8-22M6P2-A1C64A | 61820 | 100 × 13 | 45, 315, 225, 135 | 983.96 | 3×Ø9.6, r 45.17 | 1.37 | 127.8 / 132.2 × 57 | 5.05 × 8.05 | 4.977 | 138 / 167, 3.5 / 6 |
| PTK-040-R5X8-22M6P2-5D1664 | эксцентрик | 124.5 × 8 | 45, 315, 225, 135 | 789.18 | 3×Ø9.7, r 57.38 | -0.43 | 127.3 / 131.7 × 37 | 5.05 × 8.05 | 4.938 | 137.5 / 166, 1 / 1 |
| PTK-040-R5X5-22M6P2-3F1C4A | 61820 | 100 × 13 | 45, 315, 225, 135 | 974.71 | 2×Ø11.8, r 44.08 | 1.26 | 127.8 / 132.2 × 57 | 5.05 × 5.05 | 4.977 | 138 / 167, 5 / 9 |
| PTK-040-R5X5-22M6P2-2DF37C | эксцентрик | 124.5 × 5 | 45, 315, 225, 135 | 493.24 | 3×Ø9.7, r 57.38 | -0.27 | 127.3 / 131.7 × 25 | 5.05 × 5.05 | 4.938 | 137.5 / 166, 1 / 1 |
| PTK-040-R3X8-10M5P2-C1B79F | 61812 | 60 × 10 | 45, 315, 225, 135 | 170.66 | 1×Ø10.7, r 24.25 | -0.51 | 79.68 / 82.32 × 45 | 3.05 × 8.05 | 3.202 | 86.2 / 113, 2 / 3 |
| PTK-040-R3X8-10M5P2-4EE27D | эксцентрик | 75.2 × 8 | 45, 315, 225, 135 | 172.68 | 1×Ø10.5, r 31.95 | -1.06 | 76.88 / 79.52 × 37 | 3.05 × 8.05 | 2.982 | 83.4 / 110, 1 / 1 |
| PTK-040-B3-10M5P2-80BC3D | эксцентрик | 75.2 × 3 | 45, 315, 225, 135 | 64.09 | 1×Ø10.4, r 32 | 0.07 | 76.88 / 79.52 × 17 | 3.05 × 3.05 | 2.982 | 83.4 / 110, 1 / 1 |
| PTK-050-R5X8-22M6P2-7B07E5 | эксцентрик | 156.4 × 8 | 45, 315, 225, 135 | 1237.31 | 1×Ø19.1, r 68.65 | 2.06 | 159.2 / 163.6 × 37 | 5.05 × 8.05 | 4.946 | 169.4 / 198, 1 / 1 |
| PTK-050-R5X5-22M6P2-1AD71F | эксцентрик | 156.4 × 5 | 45, 315, 225, 135 | 773.32 | 1×Ø19.1, r 68.65 | 1.29 | 159.2 / 163.6 × 25 | 5.05 × 5.05 | 4.946 | 169.4 / 198, 1 / 1 |
| PTK-050-R3X8-10M5P2-E6B80C | 61815 | 75 × 10 | 45, 315, 225, 135 | 258.76 | 2×Ø8, r 33.09 | 0.05 | 96.68 / 99.32 × 45 | 3.05 × 8.05 | 3.021 | 103.2 / 130, 2 / 3 |
| PTK-050-R3X8-10M5P2-4AFC2C | эксцентрик | 94.5 × 8 | 45, 315, 225, 135 | 270.94 | 3×Ø6.5, r 43.59 | 1.12 | 96.18 / 98.82 × 37 | 3.05 × 8.05 | 2.989 | 102.7 / 129, 1 / 1 |
| PTK-050-B3-10M5P2-7415AD | эксцентрик | 94.5 × 3 | 45, 315, 225, 135 | 100.77 | 2×Ø8, r 42.84 | -0.09 | 96.18 / 98.82 × 17 | 3.05 × 3.05 | 2.989 | 102.7 / 129, 1 / 1 |
| PTK-063-R3X8-22M6P2-BDBB72 | 61819 | 95 × 13 | 45, 315, 225, 135 | 532.87 | 1×Ø12.8, r 40.7 | -1.59 | 121.68 / 124.32 × 57 | 3.05 × 8.05 | 3.015 | 128.2 / 157, 3.5 / 6 |
| PTK-063-R3X8-22M6P2-2D6433 | эксцентрик | 119.5 × 8 | 45, 315, 225, 135 | 431 | 1×Ø12.8, r 52.95 | 3.1 | 121.18 / 123.82 × 37 | 3.05 × 8.05 | 2.99 | 127.7 / 156, 1 / 1 |
| PTK-063-B3-22M6P2-240036 | эксцентрик | 119.5 × 3 | 45, 315, 225, 135 | 160.58 | 1×Ø12.8, r 52.95 | 0.12 | 121.18 / 123.82 × 17 | 3.05 × 3.05 | 2.99 | 127.7 / 156, 1 / 1 |
| PTK-080-R3X8-22M6P2-5063C8 | эксцентрик | 152.3 × 8 | 45, 315, 225, 135 | 697.09 | 2×Ø10, r 70.74 | 1.38 | 153.98 / 156.62 × 37 | 3.05 × 8.05 | 2.995 | 160.5 / 189, 1 / 1 |
| PTK-080-B3-22M6P2-F9ADAB | эксцентрик | 152.3 × 3 | 45, 315, 225, 135 | 260.08 | 3×Ø8.1, r 71.69 | 0.48 | 153.98 / 156.62 × 17 | 3.05 × 3.05 | 2.995 | 160.5 / 189, 1 / 1 |

## Технологические ограничения (Д-45)

| Код | Пара | Следствие для расчёта | Обоснование |
|---|---|---|---|
| Т1 | шарик / наружное кольцо подшипника | исключено из результатов SPEC-10 | без жёлоба контакт точечный: допускаемая сила на шарик — десятки Н (B_D3, u = 10: M ≈ 1 Н·м, CP-32); жёлоб на закалённой шлифованной дорожке покупного подшипника не изготовить |
| Т2 | шарик / эксцентрик | контакт с жёлобом r = groove_f·Dш: k_y = 2/Dш − 1/(groove_f·Dш); Герц в круговом приближении — оценка | жёлоб точится и шлифуется на эксцентрике .03 (своё изготовление); на чертёж .03 — радиус и биение жёлоба (CP-28) |
| Т3 | шарик / венец | жёлоба в венце нет: шарик на профиле как на плоскости — обычно ограничивает M | жёлоб по траектории (6) — сферической фрезой (SM-1, ось C) или профильным электродом ЭЭС; не заложен — OQ-11 |
| Т4 | тело / эксцентрик без подшипника | M без проверки по скорости входа; η и износ не считаются | скольжение ≈ ω·Dг/2: твёрдость эксцентрика не ниже тел, смазка; предел скорости — OQ-10 после калибровки OQ-08 |

### Исключённые по технологии исполнения

| ID | u | Тело | Генератор | Код |
|---|---|---|---|---|
| PTK-010-B3-22M6P2-A9E010 | 10 | B_D3 | bearing | Т1 |
| PTK-016-B3-22M6P2-E75053 | 16 | B_D3 | bearing | Т1 |
| PTK-020-B3-22M6P2-BF56C9 | 20 | B_D3 | bearing | Т1 |
| PTK-025-B3-22M6P2-E4CC87 | 25 | B_D3 | bearing | Т1 |
| PTK-032-B3-22M6P2-966F6C | 32 | B_D3 | bearing | Т1 |
| PTK-040-B3-22M6P2-BFE17E | 40 | B_D3 | bearing | Т1 |
| PTK-050-B3-22M6P2-12B65F | 50 | B_D3 | bearing | Т1 |
| PTK-063-B3-22M6P2-5169EE | 63 | B_D3 | bearing | Т1 |
| PTK-080-B3-22M6P2-A7B1AA | 80 | B_D3 | bearing | Т1 |
| PTK-100-B3-22M6P2-D6E346 | 100 | B_D3 | bearing | Т1 |
===== END FILE =====
===== FILE: specs/SPEC-11_PTK_DESIGN.md (строки 10–13) =====

| Параметр | K10 | K20 | Описание |
|---|---|---|---|
| ID | PTK-063-R3X8-22M6P2-BDBB72 | PTK-063-R3X8-22M6P2-BDBB72 | ID исполнения шага 1 (SPEC-10). |
===== END FILE =====

===== FILE: specs/SPEC-11_PTK_DESIGN.md (строки 29–39) =====
|---|---|---|---|
| PTK-063-R3X8-22M6P2-BDBB72.03A-K10 | PTK-063-R3X8-22M6P2-BDBB72.03A | 45 | 1 |
| PTK-063-R3X8-22M6P2-BDBB72.03B-K10 | PTK-063-R3X8-22M6P2-BDBB72.03B | 315 | 2 |
| PTK-063-R3X8-22M6P2-BDBB72.03C-K10 | PTK-063-R3X8-22M6P2-BDBB72.03C | 225 | 3 |
| PTK-063-R3X8-22M6P2-BDBB72.03D-K10 | PTK-063-R3X8-22M6P2-BDBB72.03D | 135 | 4 |
| PTK-063-R3X8-22M6P2-BDBB72.03A-K20 | PTK-063-R3X8-22M6P2-BDBB72.03A | 45 | 1 |
| PTK-063-R3X8-22M6P2-BDBB72.03B-K20 | PTK-063-R3X8-22M6P2-BDBB72.03B | 315 | 2 |
| PTK-063-R3X8-22M6P2-BDBB72.03C-K20 | PTK-063-R3X8-22M6P2-BDBB72.03C | 225 | 3 |
| PTK-063-R3X8-22M6P2-BDBB72.03D-K20 | PTK-063-R3X8-22M6P2-BDBB72.03D | 135 | 4 |

## Номенклатура
===== END FILE =====

===== FILE: specs/SPEC-11_PTK_DESIGN.md (строки 73–79) =====
| **τ ступицы** | Касательное напряжение кручения в ступице .12 | Проверка прочности ступицы при передаче выходного момента. [τ] — допускаемое значение (обычно 25 МПа для сталей 40Х/35ХМ). Если τ > [τ] — ступица не проходит по кручению, нужен больший Ø ступицы или более прочный материал.
| **τ среза штифта** | Касательное напряжение среза в штифте соединения | Проверка штифта на срез силой, передаваемой от сепаратора к ступице. [τ] — допускаемое напряжение сдвига штифта (обычно 80 МПа). Если τ > [τ] — штифт не проходит, нужно увеличить Ø или число штифтов.
| **σсм стенки** | Напряжение смятия стенки сепаратора .02 под штифтом | Проверка тонкостенной обечайки .02C на продавливание штифтом. [σсм] — допускаемое смятие (обычно 150 МПа). Если σсм > [σсм] — стенка не проходит, нужно увеличить толщину или Ø штифта.
| **σсм ступицы** | Напряжение смятия ступицы .12 под штифтом | Проверка ступицы .12 на продавливание штифтом. [σсм] — допускаемое смятие (обычно 150 МПа). Если σсм > [σсм] — ступица не проходит, нужно увеличить толщину стенки или число штифтов.
| **τ среза к торцу** | Касательное напряжение среза перемычки от штифта до торца детали | Проверка перемычки между отверстием штифта и внешним торцем (внутреннего кольца .09 или наружной поверхности). [τ] — допускаемое значение (обычно 90 МПа). Если τ > [τ] — перемычка не проходит, нужно увеличить Ø отверстия или сместить штифт.
| **r_h .09** | Радиус заплечика подшипника .09 (da/2) | Внутренняя граница опорного обода .12A. Используется для проверки толщины обода: s_об = r0 − r_h, где r0 — отверстие бурта/кольца. Если s_об < требуется — конструктив вырождается (L2/L4 → L3).

===== END FILE =====

===== FILE: specs/SPEC-11_PTK_DESIGN.md (строки 120–123) =====

### Проработка K10 — ✗ ОШИБКА

**ID:** PTK-063-R3X8-22M6P2-BDBB72
===== END FILE =====

===== FILE: specs/SPEC-11_PTK_DESIGN.md (строки 167–172) =====
  - τ среза штифта: 66.2 МПа — касательное напряжение среза штифта
  - σсм стенки .02: 41.1 МПа — смятие стенки сепаратора под штифтом
  - σсм ступицы .12: 34.6 МПа — смятие ступицы под штифтом
  - τ среза к торцу: 20.6 МПа — срез перемычки от штифта до торца

#### Выход: вал в ступице
===== END FILE =====

===== FILE: specs/SPEC-11_PTK_DESIGN.md (строки 216–219) =====

### Проработка K20 — ✓ OK

**ID:** PTK-063-R3X8-22M6P2-BDBB72
===== END FILE =====

## Регистры

===== FILE: specs/DECISIONS.md (строки 97–97) =====
- Д-41: допускаемый момент (egm/ptk_force.py): R_i = R_max·sin φ_i на 0 < φ < π, реакции (8), (9) без трения; Герц тело/наружное кольцо и тело/венец (венец — плоскость), [σ_H] — sigma_H_line/sigma_H_point; статика подшипника R_max·|Σ sin φ·e| ≤ C0/s0_brg; худшее из 8 положений генератора; M = min(M_H, M_B, M крепл./safety), ограничение — в SPEC-10; ошибка — только M < M_min; не учтены: трение (11), ресурс подшипника, контакт тело/паз (OQ-08, CP-31).
===== END FILE =====

===== FILE: specs/DECISIONS.md (строки 106–106) =====
- Д-42: тип генератора ПТК — ptk_input.json → limits.gen_types, считаются все из списка: bearing — тела на наружном кольце подшипника .08 (Д-40); eccentric — тела прямо на эксцентрике .03, без .08; тип — в хэше ID (GEOM_REV = 6) и колонке SPEC-10 «Генератор»; модель нагрузки обоих типов — жёсткий генератор (Д-41), не адаптивный по Янгулову; скольжение тело/эксцентрик не оценено — OQ-10.
===== END FILE =====

===== FILE: specs/DECISIONS.md (строки 348–348) =====
| OQ-08 | gamma_min, mu_ring, mu_slot — подтвердить по литературе ВППТК (Янгулов, ТПУ) или испытанием                                                                                                                                     | коэффициенты χ, a, b формулы (11) и sigma_H_line/sigma_H_point (Д-41) — испытанием |
===== END FILE =====

===== FILE: specs/DECISIONS.md (строки 350–350) =====
| OQ-10 | Генератор `eccentric` (Д-42): допустимость скольжения тело/эксцентрик (≈ ω·D_г/2), материал и твёрдость эксцентрика, смазка; потери и η по (11), (12) — после калибровки a, b, χ (OQ-08), CP-32                                 | открыт |
===== END FILE =====

===== FILE: specs/DECISIONS.md (строки 543–544) =====
- Д-116: предел сепаратора входит в момент, постановка переворачивается (2026-11-15; CP-94, CP-95, CP-96; уточняет Д-41): (1) момент исполнения — `M = min(M_H, M_B, t_hold/safety, M_sep)`, где `M_sep` — предел по переносу момента через ряд окон, изгибу перемычки и контакту ролика в окне; до его появления «✓» в SPEC-10 недостоверен (K20 проходит с 1160.5 Н·м при оценке предела сепаратора 250…500 Н·м). (2) Постановка шага 1 меняется: на входе требуемый момент `M_req`, на выходе — Dш, R_Σ (через обод), тип генератора и крепление при минимальном габарите; крепление подбирается по моменту, а не берётся наименьшим. (3) `gen_type: rim` (подшипник плюс обод) — штатный способ отвязать R_Σ от каталога подшипников. Обоснование: M ≈ R_max·u·a_ω·Σsin²φ — радиус центров тел R_Σ на момент по контакту не влияет, но окружная сила на сепаратор F_t = M/R_Σ падает с ростом R_Σ, а толщина стенки t = 2.2·a_ω растёт только с Dш. Порядок работ: CP-94 → CP-97 → CP-96 → CP-95.
- Д-117: схема с неподвижным сепаратором — не принимается для ПТК (2026-11-15; ответ на предложение альтернативной схемы): сепаратор не выходит из силовой цепи, он становится реактивным звеном с T ≈ T_вых·n/(n+1) и несёт почти тот же момент; выигрыш только в том, что он не вращается и крепится с двух сторон на большом радиусе. Схема `fixed: cage, output: ring` остаётся заделом для другого продукта — мотор-редуктора со встроенной ПТК (ротор вместо входного вала, эксцентрик — полое кольцо, .10 и .15 исчезают, i = n + 1). Для текущего ПТК схема не меняется: `fixed: ring, output: cage` (Д-11).
===== END FILE =====

===== FILE: specs/DECISIONS.md (строки 639–639) =====
| OQ-44 | Допускаемое напряжение в перемычке сепаратора (CP-94): концентратор K в углах окон, скругление, требование по запасу S_sep и учёт кромочного контакта ролика со стенкой 1.32 мм; от ответа зависит M_sep и, следовательно, достоверность «✓» по всем исполнениям | открыт |
===== END FILE =====
===== FILE: specs/CODE_PLAN.md (строки 75–78) =====
| CP-94 | Предел по переносу момента через ряд окон (M_sep) — расчётная проверка шага 1, которой сейчас нет. Факт: `M = min(M_H, M_B, t_hold/safety)` (`egm/ptk.py`), сепаратор в минимум не входит, поэтому K20 проходит с «✓» при M 1160.5 Н·м, а оценка модели даёт предел сепаратора 250…500 Н·м. Три проверки: (1) перенос момента через ряд окон у выходного торца — рама Виренделя: V = M_ряд/(n·R_Σ), M_изг = V·L_окн/2, W = t·b²/6, σ = M_изг/W (K20: ≈450 МПа при 1160.5, ≈600 при полном моменте); (2) местный изгиб перемычки нагрузкой своего ряда — балка с заделкой, L = L_окн, W = t·b²/6 (≈100/200 МПа при F 300/600 Н); (3) контакт тела со стороной окна — Герц по линии l = L_окн (σH ≈ 960/1360 МПа) плюс кромочный контакт (ролик доходит до края стенки 1.32 мм). Допускаемое — многоцикловая усталость (нагружение на каждый оборот входа): [σ] = σ₋₁/(K·S), K ≈ 2 в углах окон (40Х: σ₋₁ 509, S 2.5 → ≈100 МПа). Стенка t = 2.2·a_ω задана кинематикой (запас по `sep_web_min` 0.06 мм), поднимать нельзя; рычаги — b через n, L_окн = длина ролика + зазор, скругление углов, путь момента. Выход: M_sep в min(...), M_by «сепаратор», причина sep_why, SUP-коэффициенты (K_окн, S_sep, k_edge) в ptk_input, глоссарий в ptk_doc, пересчёт K10/K20 — ожидается падение M до 250…500 Н·м и смена M_by, self_test на K20 (σ перемычки ≤ [σ]) | egm/ptk.py, egm/ptk_force.py, egm/ptk_profile.py, egm/ptk_doc.py, specs/SPEC-10_PTK_CALC.md, specs/ptk_input.yaml, docs/Силовой расчет ПТК/Силовой расчет ПТК.md | Д-116, Д-41, OQ-08 | CP-32 | открыт — первый по порядку (CP-95/CP-96 без него идут вслепую) |
| CP-95 | Инверсия постановки: вход — требуемый момент M_req, выход — Dш, R_Σ (через обод), тип генератора и крепление при минимальном габарите D. Сейчас задаётся u, перебираются тела и крепления, минимизируется габарит, а M получается следствием (`ptk.py`, шаг 1); крепление берётся наименьшее и его предел становится M (K20: крепл./safety = 1740.7/1.5 → 1160.5). Нужно: `M_req` в ptk_input, решение перебором по (Dш, R_Σ, gen_type, крепление) с отбором по всем пределам (M_H, M_B, M_крепл, M_sep) и минимумом D; крепление подбирается по моменту, а не «первое наименьшее»; таблица исполнений SPEC-10 получает колонку «M_req»; меняются ID исполнений (Д-80). Порядок: после CP-94 | egm/ptk.py, egm/ptk_doc.py, specs/SPEC-10_PTK_CALC.md, specs/ptk_input.yaml | Д-116, Д-41, Д-80 | CP-94 | открыт |
| CP-96 | `gen_type: rim` (подшипник плюс обод) — новый тип генератора: геометрия свободна как у `eccentric` (Dг с шагом `dgen_step`), качение как у `bearing`. Подшипник садится на минимальный радиус эксцентрика, дорожка обода имеет длину ровно l, обод закаливается как дорожка под ролик. Сейчас у `bearing` Dг жёстко равен D подшипника и контакт по min(l, B), у `eccentric` — скольжение (OQ-10). Проверки: жёсткость обода на изгиб (тела нагружают половину окружности, тонкий обод сплющивается в овал — иначе распределение нагрузки по телам плывёт), C0 малого подшипника (Dг обода разгружает контакт, но уменьшает подшипник → M_B может стать главным; вариант — шире или игольчатый), посадка обода на наружное кольцо с натягом, масса и инерция входа. GEN_TYPES, ptk_input gen_types, выбор подшипника по C0 | egm/ptk.py, egm/ptk_profile.py, egm/ptk_doc.py, specs/ptk_input.yaml, specs/SPEC-10_PTK_CALC.md, specs/vendor_prices.yaml | Д-116, Д-40, OQ-10 | CP-94 | открыт |
| CP-97 | Каталог тел качения 4–6 мм (`specs/vendor_prices.yaml` → rollers): сейчас только R_D2x4, R_D3x8, B_D3, поэтому Dш не растёт — перебирать нечего. При u 63 потолок Dш 4.02 мм по `d_out_max` 200 (D 157), при u 80/100 тело 3 мм уже не помещается. Добавить Dш 4, 5, 6 мм с длинами l и ценами, пометив, какие подтверждены поставщиком (как OQ-26 для штифтов). Ловушка: длинный ролик поднимает контакт, но удлиняет окно, а изгиб перемычки растёт ∝ l² — для сепаратора лучше больше коротких рядов, чем длинные ролики; выбор тел согласуется с CP-94/CP-96 | specs/vendor_prices.yaml, egm/ptk.py (GEOM/каталог тел), specs/ptk_input.yaml | CP-94, CP-96 | CP-96 | открыт |
===== END FILE =====

## Силовой расчёт: окна и сепаратор

(docs/Силовой расчет ПТК/Силовой расчет ПТК.md: раздел /перемычк/ не найден)
(docs/Силовой расчет ПТК/Силовой расчет ПТК.md: раздел /сепаратор/ не найден)

## Точка регистрации self_test

===== FILE: main.py (строки 206–216) =====
                           ("techdraw_sheet", __import__("egm.cad.techdraw_sheet", fromlist=["self_test"]).self_test),
                           ("hub", __import__("egm.cad.ptk_hub", fromlist=["self_test"]).self_test),
                           ("shaft_cad", __import__("egm.cad.ptk_shaft", fromlist=["self_test"]).self_test),
                           ("materials", __import__("egm.materials", fromlist=["self_test"]).self_test),
                           ("tech_proc", __import__("egm.tech_proc", fromlist=["self_test"]).self_test),
                           ("materials_cfg", __import__("egm.materials", fromlist=["check_repo"]).check_repo),
                           ("srccheck", __import__("egm.srccheck", fromlist=["self_test"]).self_test),
                           ("join", __import__("egm.ptk_join", fromlist=["self_test"]).self_test),
                           ("shafts", shafts.self_test),
                           ("shafts_cfg", shafts.check_repo),
                           ("shaft_doc", shaft_doc.self_test),
===== END FILE =====

## Выжимка чисел (сгенерировано из specs/ptk_configs.yaml и specs/ptk_designs.yaml)

| Проработка | M шага 1, Н·м | M_by | D, мм | M трения венца / запас | d_bc |
|---|---|---|---|---|---|
| `PTK-050-R5X5-22M6P2-20A347` | 0.0 |  | 198.0 | 2246.5 / None | 183.0 |
| `PTK-050-R5X5-22M6P2-1AD71F` | 1497.7 | крепление | 198.0 | 2246.5 / None | 183.0 |
| `PTK-050-R3X8-10M5P2-E6B80C` | 305.5 | крепление | 130.0 | 458.2 / None | 115.7 |
| `PTK-050-R3X8-10M5P2-4AFC2C` | 304.1 | крепление | 129.0 | 456.2 / None | 115.2 |
| `PTK-063-R5X5-22M6P2-A81518` | 0.0 |  | 240.0 | 2756.0 / None | 224.5 |
| `PTK-063-R5X5-22M6P2-64F71F` | 0.0 |  | 240.0 | 2756.0 / None | 224.5 |
| `PTK-063-R3X8-22M6P2-BDBB72` | 1160.5 | крепление | 157.0 | 1740.7 / None | 141.8 |
| `PTK-063-R3X8-22M6P2-2D6433` | 1156.4 | крепление | 156.0 | 1734.6 / None | 141.3 |

### YAML-дамп строк шага 1 (K10/K20; файл целиком — 56 тыс. строк, в CTX не влезает)

```yaml
- u: 63
  roller: R_D3x8
  Drol: 3.0
  id: PTK-063-R3X8-22M6P2-BDBB72
  n: 63
  z: 64
  a_w: 0.6
  R_sum: 61.5
  R_by: подрез
  Dgen: 120.0
  bearing: '61819'
  gen: bearing
  d_root: 127.2
  d_tip: 124.8
  alpha_max: 32.0
  r_tip: 0.063
  sep_web: 3.07
  holes: 22×M6+2шт Ø6
  mount: M6x24P2
  d_bc: 141.8
  d_out: 157.0
  width: 57.0
  Drol_max: 4.02
  t_hold: 1740.7
  M_H: 4124.9
  M_B: 2842.4
  M: 1160.5
  M_by: крепление
  ring_variants: 1
  phasing:
  - row: 1
    phi: 0.0
    delta_p: 0.0
    s: 0.0
    cage: 0.0
    variant: A
    s_arc_mm: 0.0
  - row: 2
    phi: 90.0
    delta_p: 0.0
    s: 0.0
    cage: 4.2857
    variant: A
    s_arc_mm: 0.0
  - row: 3
    phi: 180.0
    delta_p: 0.0
    s: 0.0
    cage: 2.8571
    variant: A
    s_arc_mm: 0.0
  - row: 4
    phi: 270.0
    delta_p: 0.0
    s: 0.0
    cage: 1.4286
    variant: A
    s_arc_mm: 0.0
  parts:
  - id: PTK-063-R3X8-22M6P2-BDBB72.01A
    name: венец
    variant: A
    s: 0.0
    s_arc_mm: 0.0
    rows:
    - 1
    - 2
    - 3
    - 4
  - id: PTK-063-R3X8-22M6P2-BDBB72.02
    name: сепаратор
    variant: ''
    rows:
    - 1
    - 2
    - 3
    - 4
  - id: PTK-063-R3X8-22M6P2-BDBB72.03A
    name: эксцентрик
    variant: A
    key_angle: 45.0
    rows:
    - 1
  - id: PTK-063-R3X8-22M6P2-BDBB72.03B
    name: эксцентрик
    variant: B
    key_angle: 315.0
    rows:
    - 2
  - id: PTK-063-R3X8-22M6P2-BDBB72.03C
    name: эксцентрик
    variant: C
    key_angle: 225.0
    rows:
    - 3
  - id: PTK-063-R3X8-22M6P2-BDBB72.03D
    name: эксцентрик
    variant: D
    key_angle: 135.0
    rows:
    - 4
  - id: PTK-063-R3X8-22M6P2-BDBB72.05A
    name: межрядная шайба
    variant: A
    h: 3.5
    pos:
    - 0
    - 4
    rows:
    - 1
    - 4
  - id: PTK-063-R3X8-22M6P2-BDBB72.05B
    name: межрядная шайба
    variant: B
    h: 6.0
    pos:
    - 1
    - 2
    - 3
    rows:
    - 1
    - 2
    - 3
    - 4
  geom:
    rev: 6.0
    u: 63.0
    gen: bearing
    roller:
      type: roller
      d: 3.0
      l: 8.0
      a_w: null
      wall_min: null
    bearing:
      d: 95.0
      D: 120.0
      B: 13.0
    limits:
      a_k: 0.2
      r_tip_min: 0.05
      sep_web_min: 1.0
      shaft_d_min: 6.0
      ecc_wall_min: 1.0
      wall_min: 4.0
      row_gap: 1.0
      rows: 4.0
      row_phases:
      - 0.0
      - 90.0
      - 180.0
      - 270.0
      d_bc_step: 0.1
      d_out_step: 1.0
      dgen_step: 0.1
      sep_gap: 0.05
    ring_holes:
      bolt: M6
      n: 22.0
      pins: 2.0
      pin_d: 6.0
      head_margin: 0.5
    fastener:
      d_clear: 6.6
      dk: 10.0
  ok: true
  errors: []
  warnings: []
  tech: []
  excluded: ''
  sep:
    n: 63
    r_in: 60.84
    r_out: 62.16
    w: 3.05
    h: 8.05
    length: 57.0
    web: 3.015
    rows:
    - row: 1
      cage: 0.0
      z0: 3.475
    - row: 2
      cage: 4.2857
      z0: 17.475
    - row: 3
      cage: 2.8571
      z0: 31.475
    - row: 4
      cage: 1.4286
      z0: 45.475
  ecc:
    De: 95.0
    t: 13.0
    a: 0.6000000000000001
    d_shaft: 6.0
    key_b: 2.0
    key_t2: 1.0
    m_brg_g: 150.8
    m_brg_est: true
    groove_r: null
    U:
      disk: 434.01
      brg: 90.47
      bodies: 8.39
      sum: 532.87
    bal:
      n: 1
      d: 12.8
      r: 40.7
      U_rem: 534.46
      res: -1.59
      holes:
      - - 40.7
        - 0.0
    rows:
    - row: 1
      phi: 0.0
      key_angle: 45.0
      key_wall: 43.92
    - row: 2
      phi: 90.0
      key_angle: 315.0
      key_wall: 43.92
    - row: 3
      phi: 180.0
      key_angle: 225.0
      key_wall: 43.07
    - row: 4
      phi: 270.0
      key_angle: 135.0
      key_wall: 43.07
  spacer:
    r_in: 64.1
    d_out: 157.0
    h_end: 3.5
    h_mid: 6.0
    web: 3.5
    pos:
    - pos: 0
      z: 0.0
      h: 3.5
      variant: A
    - pos: 1
      z: 11.5
      h: 6.0
      variant: B
    - pos: 2
      z: 25.5
      h: 6.0
      variant: B
    - pos: 3
      z: 39.5
      h: 6.0
      variant: B
    - pos: 4
      z: 53.5
      h: 3.5
      variant: A
```


| Проработка | ok | u | R_Σ | Dш | окна n | стенка t | d_req | τ | σсм | .09 |
|---|---|---|---|---|---|---|---|---|---|---|
| K10 | False | None | None | None | None | None | None | None | None | 61815 |
| K20 | True | None | None | None | None | None | None | None | None | 61815 |
