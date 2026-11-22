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
import yaml
from pathlib import Path as _Path
import json
import math
from dataclasses import asdict, dataclass, field, fields, replace
from fractions import Fraction

from egm import materials, ptk_force, ptk_parts, ptk_profile

SEP_K = 1.1    # полутолщина кольца сепаратора / a_ω (egm/calc_vptc.py: hc = 2.2·e)
GEN_TYPES = ("bearing", "eccentric", "rim")   # Д-42; CP-96: rim — малый подшипник + обод .18


@dataclass
class PtkLimits:
    d_out_max: float = 110.0      # D max — наружный Ø редуктора, мм (Д-08); None — без предела (Д-43)
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
    u_list: tuple = (10, 16, 20, 25, 32, 40, 50, 63)
    u_range: tuple = ()           # CP-103 (A-5): [u_min, u_max] явно; () — края u_list (Д-119)

    # Д-119: границы одноступенчатого диапазона не задаются в ptk_input.yaml, а берутся
    # из u_list — первый и последний элементы. В хэш ID не входят (заменяли u_min/u_max).
    @property
    def u_min(self) -> int:
        """Нижняя граница одноступенчатого u — первый элемент u_list (Д-08)."""
        return int(self.u_range[0]) if self.u_range else int(self.u_list[0])

    @property
    def u_max(self) -> int:
        """Верхняя граница — последний элемент u_list; u > u_max — две ступени (Д-11)."""
        return int(self.u_range[-1]) if self.u_range else int(self.u_list[-1])
    E_mod: float = 210000.0       # модуль упругости тел, венца, колец подшипника, МПа (Д-41)
    nu: float = 0.3               # коэффициент Пуассона
    sigma_H_line: float = 2500.0  # допускаемое σ_H, линейный контакт (ролик), МПа (OQ-08)
    sigma_H_point: float = 3000.0  # допускаемое σ_H, точечный контакт (шарик), МПа (OQ-08)
    s0_brg: float = 1.0           # запас статической грузоподъёмности подшипника, C0/P0
    sep_sigma_m1: float = 509.0   # σ₋₁ материала сепаратора, МПа (40Х, materials.yaml; CP-94)
    sep_K: float = 2.0            # концентрация напряжений в углах окон сепаратора (OQ-44)
    sep_S: float = 2.5            # запас многоцикловой усталости перемычки (OQ-44)
    sep_sigma_Hlim: float = 1056.0  # CP-103: σ_Hlim при sep_grade = "" (запасной путь), МПа
    sep_S_H: float = 1.2          # CP-103 (Д-126): запас контактной выносливости
    sep_Z_N: float = 1.0          # CP-103: коэффициент долговечности
    sep_K_depth: float = 2.0      # CP-103: концентрация на границе слоя (OQ-44)
    sep_case_k: float = 3.0       # CP-103: слой держит контакт при δ >= k·z_t (OQ-49)
    sep_k_edge: float = 1.2       # рост σ_H у кромки стенки окна — кромочный контакт (OQ-44)
    # CP-102 (Д-125): материал сепаратора — марка materials.yaml и её состояние
    # ("38Х2МЮА" + "nitr" -> ссылка "38Х2МЮА:nitr"). Пусто — σ₋₁ и [σ_H] берутся из
    # sep_sigma_m1 / sep_sigma_H, как до CP-102. Вариант u_calc может задать перечень materials.
    sep_grade: str = ""          # марка сепаратора; "" — числа sep_sigma_* из limits
    sep_state: str = ""          # состояние марки (materials.yaml → states)
    sep_band_t: float = 0.0       # радиальная толщина поясов сепаратора, мм; 0 — = стенка (CP-98, OQ-46)
    sep_band_gap: float = 0.2     # зазор утолщённого пояса до dвн шайбы .05, мм (CP-98)
    M_min: float = 0.0            # требуемый выходной момент, Н·м; 0 — не проверяется (Д-41)
    # CP-99, Д-123: таблица расчёта по u — {u: {M_req: {параметры варианта}}}. Пустая внутренняя
    # таблица — прямая постановка; ключ внутренней — целевой момент M_req, Н·м. Состав ключей u
    # задаёт u_list. В ID не входят; в хэш попадают только dR, hb и band_fill (geom.*).
    u_calc: dict = field(default_factory=dict)
    u_def: dict = field(default_factory=dict)   # CP-101: {u: параметры} — слои ALL.ALL + u.ALL
    r_step: float = 1.0           # CP-95: шаг подъёма R_Σ по умолчанию, мм (вариант может задать свой)
    r_up_max: float = 40.0        # CP-95: наибольший подъём R_Σ над R_Σ min по умолчанию, мм
    # CP-95b: добавка к шагу ряда — высота пояса сепаратора, мм; перебор под M_req (в ID — hb)
    band_h_list: tuple = (0.0, 2.0, 4.0, 6.0, 8.0)
    gen_types: tuple = ("bearing", "eccentric")   # генераторы для расчёта (Д-42)
    dgen_step: float = 0.1        # округление вверх D_г эксцентрика и обода, мм (Д-42)
    rim_t_min: float = 2.0        # CP-96: наименьшая радиальная толщина обода .18, мм
    rim_dfl_k: float = 0.05       # CP-96: допускаемая овализация обода / a_ω (OQ-48)
    rim_k_ov: float = 0.0068      # CP-96: δ = k·P·r³/(E·I), 2-я гармоника нагрузки (OQ-48)
    rim_fit_k: float = 0.0004     # CP-96: натяг обода на наружное кольцо, δ/D
    rim_sigma_fit: float = 300.0  # CP-96: допускаемое σθ обода от натяга, МПа (OQ-48)
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
    M_sep: float = 0.0            # предел по сепаратору, Н·м (CP-94, Д-116)
    M_row: float = 0.0            # референс: предел одного ряда окон, Н·м (CP-98, Д-118)
    M: float = 0.0                # допускаемый выходной момент, Н·м
    M_by: str = ""                # что ограничивает M: контакт | подшипник | крепление | сепаратор
    M_req: float = 0.0            # CP-95: требуемый момент для u, Н·м; 0 — прямая постановка
    dR: float = 0.0              # CP-95: подъём R_Σ над R_Σ min, мм (у bearing — больший подшипник)
    hb: float = 0.0               # CP-95b: добавка высоты пояса к шагу ряда, мм
    band_fill: bool = False       # CP-95b: пояс сепаратора утолщён до t_max
    sep_mat: dict = field(default_factory=dict)   # CP-102: материал сепаратора (в хэше ID)
    sep_why: str = ""             # причина M_sep: механизм, напряжения, [σ] (CP-94)
    M_body_gen: float = 0.0       # предел тела по контакту с генератором, Н·м (CP-98)
    M_body_ring: float = 0.0      # то же с венцом, Н·м
    M_body_win: float = 0.0       # то же со стороной окна сепаратора, Н·м
    M_by_body: str = ""           # первый контакт тела: генератор | венец | окно
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
    sep_chk: dict = field(default_factory=dict)   # проверка сепаратора при M (CP-94)
    ecc: dict = field(default_factory=dict)       # эксцентрик .03 (Д-46)
    spacer: dict = field(default_factory=dict)    # шайбы .05 (Д-53)
    rim: dict = field(default_factory=dict)       # обод .18 при gen = rim (CP-96)


def _load(cls, d):
    names = {f.name for f in fields(cls)}
    data = {k: v for k, v in d.items() if not k.startswith("_")}
    unknown = sorted(set(data) - names)
    if unknown:
        raise ValueError(f"{cls.__name__}: неизвестные параметры {unknown}")
    return cls(**{k: tuple(v) if isinstance(v, list) else v for k, v in data.items()})


# CP-101 (Д-124): параметры слоя u_calc → u → ALL → M_req
NUM_KEYS = ("r_step", "r_up_max", "band_h_list")          # перебор
LIST_KEYS = ("mounts", "rollers", "gen_types", "materials")   # перечни (пустой — без ограничения)
VARIANT_KEYS = NUM_KEYS + LIST_KEYS
VARIANT_RESERVED = ()                         # зарезервировано на доработку


def _parse_params(where, prm):
    """CP-101 (Д-124): параметры слоя u_calc — проверка и нормализация.

    Проверяются только заданные ключи: перебор (r_step, r_up_max, band_h_list) и перечни
    (mounts, rollers, gen_types, materials). Пустой список перечня — без ограничения (все).
    Имена материалов проверяются в load_config по materials.yaml (CP-102, CP-103)."""
    if prm is None:
        return {}
    if not isinstance(prm, dict):
        raise ValueError(f"{where}: нужна таблица параметров {{ключ: значение}}, получено "
                         f"{type(prm).__name__}")
    bad = sorted(set(prm) - set(VARIANT_KEYS) - set(VARIANT_RESERVED))
    if bad:
        raise ValueError(f"{where}: неизвестные параметры {bad}; допустимы {list(VARIANT_KEYS)}")
    res = sorted(set(prm) & set(VARIANT_RESERVED))
    if res:
        raise ValueError(f"{where}: {res} зарезервированы на дальнейшие доработки — пока не "
                         f"принимаются (CP-101)")
    out = {}
    if "r_step" in prm:
        v = float(prm["r_step"])
        if not v > 0:
            raise ValueError(f"{where}.r_step: шаг подъёма R_Σ должен быть > 0, мм")
        out["r_step"] = v
    if "r_up_max" in prm:
        v = float(prm["r_up_max"])
        if v < 0:
            raise ValueError(f"{where}.r_up_max: наибольший подъём R_Σ должен быть ≥ 0, мм")
        out["r_up_max"] = v
    if "band_h_list" in prm:
        hb = tuple(float(x) for x in prm["band_h_list"])
        if not hb or list(hb) != sorted(hb) or hb[0] < 0:
            raise ValueError(f"{where}.band_h_list: высоты пояса по возрастанию и ≥ 0, мм")
        out["band_h_list"] = hb
    for k, allowed, note in (("mounts", None, "ring_mounts"),
                             ("rollers", None, "vendor_prices.yaml → rollers"),
                             ("gen_types", GEN_TYPES, "типы генератора (Д-42)"),
                             ("materials", None, "materials.yaml (марка:состояние, CP-102)")):
        if k not in prm or prm[k] is None:
            continue
        v = prm[k]
        if isinstance(v, str) or not isinstance(v, (list, tuple)):
            raise ValueError(f"{where}.{k}: нужен список, получено {type(v).__name__}; "
                             f"пустой список — без ограничения")
        lst = tuple(str(x) for x in v)
        if allowed is not None:
            badl = [x for x in lst if x not in allowed]
            if badl:
                raise ValueError(f"{where}.{k}: {badl} — допустимы {list(allowed)}")
        out[k] = lst
    return out


def _all_layer(where, v):
    """CP-101: слой ALL — {ALL: {параметры}}; возвращает параметры слоя ({} — не задан)."""
    if v is None:
        return {}
    if not isinstance(v, dict):
        raise ValueError(f"{where}: нужна таблица {{ALL: {{параметры}}}} или {{параметры}}, "
                         f"получено {type(v).__name__}")
    if "ALL" in v:                                    # полный вид: {ALL: {параметры}}
        extra = sorted(set(v) - {"ALL"})
        if extra:
            raise ValueError(f"{where}: под ALL допустим только ключ ALL — параметры по умолчанию "
                             f"для всех элементов уровня; найдено {extra}")
        return v["ALL"]
    return v                                          # сокращённый вид: {параметры}


def _merge(*layers):
    """CP-101: слои параметров — следующий перекрывает предыдущий, список заменяется целиком."""
    out = {}
    for l in layers:
        out.update({k: v for k, v in (l or {}).items() if v is not None})
    return out


def _parse_u_calc(raw):
    """CP-99/CP-101 (Д-123, Д-124): таблица расчёта по u -> (u_calc, u_def, u_list).

    {ALL: {ALL: параметры}, u: {ALL: параметры, M_req: параметры}}. Слои: ALL.ALL — для всех u и
    вариантов, u.ALL — для всех вариантов этого u, вариант — для себя (перекрывает, список
    заменяется целиком). Пустая таблица вариантов (или только ALL) — прямая постановка для u.
    Состав ключей u, кроме ALL, задаёт u_list и границы диапазона (Д-119)."""
    if not isinstance(raw, dict) or not raw:
        raise ValueError("limits.u_calc: нужна таблица {u: {M_req: {параметры}}} — состав ключей u "
                         "задаёт таблицу SPEC-10 и u_min…u_max (CP-99, Д-123)")
    base = _parse_params("limits.u_calc.ALL.ALL", _all_layer("limits.u_calc.ALL", raw.get("ALL")))
    out, udef = {}, {}
    for k_u, var in raw.items():
        if k_u == "ALL":
            continue
        try:
            u = int(k_u)
        except (TypeError, ValueError):
            raise ValueError(f"limits.u_calc: ключ {k_u!r} — нужен u (целое) или ALL")
        if u in out:
            raise ValueError(f"limits.u_calc: u = {k_u} задан дважды")
        if u < 2:
            raise ValueError(f"limits.u_calc[{u}]: u < 2 — вне одноступенчатого диапазона (Д-08)")
        if var is None:
            var = {}
        if not isinstance(var, dict):
            raise ValueError(f"limits.u_calc[{u}]: нужно {{M_req: {{параметры}}}}, получено "
                             f"{type(var).__name__}")
        u_all = _parse_params(f"limits.u_calc[{u}].ALL",
                              _all_layer(f"limits.u_calc[{u}]", var.get("ALL")))
        udef[u] = _merge(base, u_all)
        vs = {}
        for k_m, prm in var.items():
            if k_m == "ALL":
                continue
            m = float(k_m)
            if not m > 0:
                raise ValueError(f"limits.u_calc[{u}]: M_req = {k_m} — нужен > 0, Н·м")
            if m in vs:
                raise ValueError(f"limits.u_calc[{u}]: M_req = {m:g} задан дважды")
            vs[m] = _merge(udef[u], _parse_params(f"limits.u_calc[{u}][{m:g}]", prm))
        out[u] = vs
    if not out:
        raise ValueError("limits.u_calc: нет ни одного u — ALL задаёт только параметры по умолчанию; "
                         "нужен хотя бы один u (CP-99, Д-123)")
    return out, udef, tuple(sorted(out))


def u_params(lim):
    """CP-101: все слои параметров u_calc — [(где, параметры)]; проверки и справка."""
    out = [(f"u_calc[{u}].ALL", lim.u_def.get(u, {})) for u in lim.u_list]
    out += [(f"u_calc[{u}][{m:g}]", prm) for u in lim.u_list
            for m, prm in sorted((lim.u_calc.get(u) or {}).items())]
    return out


def _scope(prm, rollers, mounts, lim, where):
    """CP-101: эффективные перечни тел качения, креплений и типов генератора для слоя.

    Пустой или отсутствующий список — без ограничения (все). Неизвестное имя — ошибка: это
    опечатка в конфиге, а не «нет такого варианта». Пустой результат — тоже ошибка, чтобы u не
    выпал из таблицы молча."""
    rl = prm.get("rollers") or ()
    bad = [k for k in rl if k not in rollers]
    if bad:
        have = sorted(k for k in rollers if not k.startswith("_"))
        raise ValueError(f"{where}.rollers: {bad} нет в vendor_prices.yaml → rollers (есть {have})")
    mt = prm.get("mounts") or ()
    bad = [k for k in mt if k not in mounts]
    if bad:
        raise ValueError(f"{where}.mounts: {bad} нет в ring_mounts (есть {list(mounts)})")
    rs = {k: v for k, v in rollers.items() if not k.startswith("_") and (not rl or k in rl)}
    ms = {k: v for k, v in mounts.items() if not mt or k in mt}
    gs = tuple(prm.get("gen_types") or lim.gen_types)
    if not rs or not ms or not gs:
        raise ValueError(f"{where}: после ограничения перечней не осталось вариантов расчёта "
                         f"(тел {len(rs)}, креплений {len(ms)}, генераторов {len(gs)}) — "
                         f"проверьте mounts / rollers / gen_types (CP-101)")
    return rs, ms, gs


def _variant_limits(lim, params):
    """CP-99: пределы перебора варианта — только числовые ключи (r_step, r_up_max, band_h_list)."""
    kw = {k: params[k] for k in NUM_KEYS if k in params}
    return replace(lim, **kw) if kw else lim


# CP-110 (A-6.1): замечания к входу, которые не привязаны к строке таблицы
CFG_WARN = []


def _dup_warnings(raw):
    """CP-110 (A-6.1): дубли в перечнях u_calc — предупреждение, не ошибка.

    Перечень схлопывается в dict молча, поэтому дубль на расчёт не влияет, но почти всегда
    означает опечатку: одно тело выпало из списка, другое попало дважды. Так 32/400 остался
    без R_D7x20 и не решился при 400 Н·м, хотя 32/700 решился при 718.3 на меньшем габарите."""
    out = []

    def chk(where, prm):
        if not isinstance(prm, dict):
            return
        for k in ("rollers", "mounts", "materials"):
            v = prm.get(k)
            if not isinstance(v, (list, tuple)):
                continue
            seen, d = set(), []
            for x in v:
                if str(x) in seen and str(x) not in d:
                    d.append(str(x))
                seen.add(str(x))
            if d:
                out.append(f"{where}.{k}: дубли {d} — перечень схлопывается; проверьте, "
                           f"не потеряно ли тело/крепление (CP-110, A-6.1)")

    top = raw.get("ALL", {}) if isinstance(raw.get("ALL"), dict) else {}
    chk("limits.u_calc.ALL.ALL", top.get("ALL", top))
    for k_u, var in raw.items():
        if k_u == "ALL" or not isinstance(var, dict):
            continue
        chk(f"limits.u_calc[{k_u}].ALL", var.get("ALL"))
        for k_m, prm in var.items():
            if k_m != "ALL":
                chk(f"limits.u_calc[{k_u}][{k_m}]", prm)
    return out


def mreq_warn(rows):
    """CP-110 (A-6.1): на одном u вариант с меньшим M_req не решён, а с большим решён —
    почти всегда потерянное тело в перечне rollers (или опечатка в самом M_req)."""
    by = {}
    for r in rows:
        if r.get("excluded") or not r.get("M_req"):
            continue
        try:
            mm = float(r["M_req"])
        except (TypeError, ValueError):
            continue
        key = (int(r["u"]), mm)
        ok = bool(r.get("ok")) and float(r.get("M") or 0) + 1e-6 >= mm
        by[key] = by.get(key, False) or ok
    out = []
    for u in sorted({k[0] for k in by}):
        vs = sorted((mm, ok) for (uu, mm), ok in by.items() if uu == u)
        for mm, ok in vs:
            if ok:
                continue
            bigger = [x for x, o in vs if o and x > mm]
            if bigger:
                out.append(f"u_calc[{u}]: M_req {mm:g} не решён, а {bigger[0]:g} решён тем же u — "
                           f"проверьте перечень rollers варианта (CP-110, A-6.1)")
    return out


def load_config(cfg):
    """specs/ptk_input.yaml -> (PtkLimits, {ключ: RingHoles}, fasteners, mount_mode) (Д-33)."""
    fast = {k: v for k, v in cfg["fasteners"].items() if not k.startswith("_")}
    raw = cfg.get("ring_mounts") or {"default": cfg["ring_holes"]}
    mounts = {k: _load(RingHoles, v) for k, v in raw.items() if not k.startswith("_")}
    raw_lim = dict(cfg["limits"])
    for key in ("u_list", "M_req"):                     # CP-99: упразднены, см. limits.u_calc
        if key in raw_lim:
            raise ValueError(f"limits.{key}: устарело — расчёт по u задаётся таблицей limits.u_calc "
                             f"(CP-99, Д-123)")
    if "sep_sigma_H" in raw_lim:                        # CP-103 (Д-126)
        raise ValueError("limits.sep_sigma_H: устарело — допускаемое считается из предела: "
                         "sep_sigma_Hlim (только при пустом sep_grade) и sep_S_H, sep_Z_N (CP-103)")
    if raw_lim.get("u_range"):
        raw_lim["u_range"] = tuple(raw_lim["u_range"])
        if len(raw_lim["u_range"]) != 2 or raw_lim["u_range"][0] >= raw_lim["u_range"][1]:
            raise ValueError("limits.u_range: нужно [u_min, u_max] по возрастанию (CP-103, A-5)")
    lim = _load(PtkLimits, raw_lim)
    lim.u_calc, lim.u_def, lim.u_list = _parse_u_calc(raw_lim.get("u_calc"))   # Д-119: края
    CFG_WARN.clear()                                          # CP-110: дубли в перечнях
    CFG_WARN.extend(_dup_warnings(raw_lim.get("u_calc")))
    bad = [g for g in lim.gen_types if g not in GEN_TYPES]
    if bad or not lim.gen_types:
        raise ValueError(f"limits.gen_types: {list(lim.gen_types)} — допустимы {GEN_TYPES} (Д-42)")
    for where, prm in u_params(lim):                    # CP-101: имена креплений — из ring_mounts
        badm = [k for k in (prm.get("mounts") or ()) if k not in mounts]
        if badm:
            raise ValueError(f"limits.{where}.mounts: {badm} нет в ring_mounts (есть {list(mounts)})")
    if lim.groove_f <= 0.5:
        raise ValueError(f"limits.groove_f = {lim.groove_f}: нужно > 0.5 — жёлоб шире шарика (Д-45)")
    if lim.r_step <= 0:
        raise ValueError(f"limits.r_step = {lim.r_step}: шаг подъёма R_Σ должен быть > 0 (CP-95)")
    refs = [lim.sep_grade] if lim.sep_grade else []      # CP-103 (A-1): марки проверяются здесь,
    for _, prm in u_params(lim):                        # а не в середине sweep
        refs += list(prm.get("materials") or ())
    for ref in refs:
        _mat(lim, ref)                                  # ValueError: марки/состояния нет
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
GEOM_REV = 8                       # Д-42: тип генератора bearing | eccentric в хэше
# Д-125/Д-126 (CP-103): в хэш входит только ссылка на материал сепаратора "марка[:состояние]" —
# она попадает на чертёж .02 (графа 3, ТТ). Числа σ — справка в sep_mat: их уточнение меняет M,
# но не ID; влияние на подбор уже в хэше через dR, hb, band_fill. Номер 8 — один разрыв.
# CP-96: rim — новое значение gen, а gen уже входит в хэш, поэтому rev НЕ повышается (Д-80: номер
# меняют при смене формул геометрии). ID bearing/eccentric остаются, у rim свои — Д-120.
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
    "Т5": ("шарик / обод .18",
           "исключено из результатов SPEC-10",
           "жёлоб на ободе не заложен (CP-96, OQ-48); ролик катится по цилиндру обода"),
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


_MATS = {}                              # CP-102: кэш materials.yaml для марки сепаратора


def _mats_catalog(mats=None):
    """CP-102: справочник материалов — переданный или specs/materials.yaml (кэш)."""
    if mats is not None:
        return mats
    if not _MATS:
        p = _Path(__file__).resolve().parents[1] / "specs" / "materials.yaml"
        _MATS.update(yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {})
    return _MATS


def _mat(lim, ref="", mats=None):
    """CP-103 (Д-126): материал сепаратора -> {ref, m1_case, m1_core, Hlim_case, Hlim_core,
    depth, src_m1, src_H}. Пределы — materials.yaml; у заданной марки нет σ₋₁ ядра или
    σ_Hlim ядра — ValueError (метка на чертеже не должна расходиться с расчётом). ref = "" —
    запасной путь limits.sep_sigma_m1 / sep_sigma_Hlim без слоя (src = "limits", устарел)."""
    r = str(ref or "")
    if not r:
        m1, H = float(lim.sep_sigma_m1), float(lim.sep_sigma_Hlim)
        return {"ref": "", "m1_case": None, "m1_core": m1, "Hlim_case": None, "Hlim_core": H,
                "depth": 0.0, "src_m1": "limits", "src_H": "limits"}
    p = materials.sep_props(_mats_catalog(mats), r)
    if p is None:
        raise ValueError(f"u_calc.materials: {r!r} — нет такой марки или состояния в "
                         f"specs/materials.yaml (CP-102)")
    c, cs = p["core"], p["case"] or {}
    miss = [k for k, v in (("sigma_m1", c["sigma_m1"]), ("sigma_Hlim | hb", c["sigma_Hlim"]))
            if v is None]
    if p["case"] is not None:
        miss += [f"case.{k}" for k in ("sigma_m1", "sigma_Hlim", "depth") if cs.get(k) is None]
    if miss:
        raise ValueError(f"материал сепаратора {r}: нет {miss} в specs/materials.yaml (CP-103, Д-126)")
    f = lambda x: None if x is None else round(float(x), 6)
    return {"ref": p["ref"], "m1_case": f(cs.get("sigma_m1")), "m1_core": f(c["sigma_m1"]),
            "Hlim_case": f(cs.get("sigma_Hlim")), "Hlim_core": f(c["sigma_Hlim"]),
            "depth": f(p["depth"]), "src_m1": "materials",
            "src_H": "materials" if p["src_Hcore"] == "sigma_Hlim" else p["src_Hcore"]}


def _mat_scope(prm, lim):
    """CP-102: перечень материалов варианта; пусто — марка по умолчанию limits."""
    refs = tuple(str(x) for x in (prm.get("materials") or ()) if str(x).strip())
    if refs:
        return refs
    d = f"{lim.sep_grade}:{lim.sep_state}" if lim.sep_state else lim.sep_grade
    return (d if lim.sep_grade else "",)


def roller_code(rol):
    t = ROLLER_TYPES.get(rol.get("type"), "X")
    if t == "B":
        return f"B{_num(rol['d'])}"
    return f"{t}{_num(rol['d'])}X{_num(rol.get('l', rol['d']))}"


def holes_code(holes):
    return f"{holes.n}{holes.bolt}" + (f"P{holes.pins}" if holes.pins else "")


def geom_params(u, rol, lim, holes, fast, brg=None, gen="bearing", dR=0.0, hb=0.0, fill=False,
                mat=None):
    """Все параметры, определяющие геометрию исполнения (вход хэша и CAD).

    CP-95: dR — подъём R_Σ у eccentric/rim. Ключ добавляется только при dR > 0, поэтому ID прямой
    постановки не меняются; у bearing R_Σ задаёт подшипник, и он уже в хэше (Д-80, Д-120)."""
    f = fast.get(holes.bolt, {})
    g = {"rev": GEOM_REV, "u": u, "gen": gen,
         "roller": {k: rol.get(k) for k in GEOM_ROLLER},
         "bearing": {k: brg.get(k) for k in GEOM_BEARING} if brg else None,
         "limits": {k: getattr(lim, k) for k in GEOM_LIMITS},
         "ring_holes": {k: getattr(holes, k) for k in GEOM_HOLES},
         "fastener": {k: f.get(k) for k in ("d_clear", "dk")}}
    if dR > 1e-9 and gen != "bearing":                  # CP-95: D_г обода/эксцентрика задан dR
        g["dR"] = dR
    if hb > 1e-9:                                       # CP-95b: шаг ряда, пакет, шайбы — другие
        g["hb"] = hb
    if fill:                                            # CP-95b: пояс до t_max (CAD пояса — OQ-46)
        g["band_fill"] = True
    if mat is not None:                                 # CP-103 (Д-126): только ссылка
        g["material"] = {"ref": mat["ref"]}
    return _n(g)


def config_id(u, rol, lim, holes, fast, brg=None, gen="bearing", dR=0.0, hb=0.0, fill=False,
              mat=None):
    """ID исполнения PTK-<u>-<тело>-<отверстия>-<хэш> (Д-80) и снимок геометрии."""
    g = geom_params(u, rol, lim, holes, fast, brg, gen, dR, hb, fill, mat)
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


def rim_pick(Dg, l, a, MB1, need_d, bears, lim):
    """CP-96: подшипник под обод .18 -> (ключ | None, обод). Кандидаты: d >= need_d,
    D <= Dг - 2·rim_t_min, натяг по Ляме проходит; берётся наибольший min(M_B, M_ov).

    MB1 — M_B пакета на 1 Н C0. Овализация: δ = rim_k_ov·P·r³/(E·I), I = l·t³/12,
    P = 1000·M/(s0·MB1) — сила ряда на 1 Н·м пакета, Н; δ <= rim_dfl_k·a_ω -> M_ov (OQ-48).
    Натяг (кольцо подшипника жёсткое): σθ = E·(δ/D)·k/(k + ν), k = (Dг²+D²)/(Dг²−D²)."""
    best, allow = None, lim.rim_dfl_k * a
    for k, b in bears.items():
        if (k.startswith("_") or b["d"] < need_d - 1e-9
                or b["D"] > Dg - 2 * lim.rim_t_min + 1e-9):
            continue
        t, rm = (Dg - b["D"]) / 2, (Dg + b["D"]) / 4
        P1 = 1000.0 / (lim.s0_brg * MB1) if MB1 > 0 else 0.0      # Н на 1 Н·м
        M_ov = (allow * lim.E_mod * l * t ** 3 / 12 / (lim.rim_k_ov * rm ** 3 * P1)
                if P1 else 0.0)
        kk = (Dg ** 2 + b["D"] ** 2) / (Dg ** 2 - b["D"] ** 2)
        s_fit = lim.E_mod * lim.rim_fit_k * kk / (kk + lim.nu)
        if s_fit > lim.rim_sigma_fit + 1e-9:
            continue
        key = (min(b["C0"] * MB1, M_ov), b["C0"], -b["D"])
        if best is None or key > best[0]:
            m = lim.rho * 1e-6 * math.pi / 4 * (Dg ** 2 - b["D"] ** 2) * l
            best = (key, k, {"D": round(Dg, 3), "d": b["D"], "b": l, "t": round(t, 3),
                             "fit": round(lim.rim_fit_k * b["D"], 4), "s_fit": round(s_fit, 1),
                             "dfl_allow": round(allow, 4), "M_ov": math.floor(10 * M_ov) / 10,
                             "m_g": round(m, 1)})
    return (best[1], best[2]) if best else (None, {})


def calc(u, rid, rol, lim, holes, fast, bears, gen="bearing", dR=0.0, hb=0.0, fill=False,
         m_req=0.0, mat=None):
    """Расчёт одной конфигурации. rol = {'type','d','l'[, 'a_w', 'wall_min']};
    gen — bearing (тела на наружном кольце подшипника, Д-40) | eccentric (на эксцентрике, Д-42).
    dR — подъём R_Σ над R_Σ min, мм (CP-95): у eccentric/rim — D_г больше на 2·dR,
    у bearing — подшипник с D ≥ 2(R_Σ min + dR) − D_ш."""
    D = rol["d"]
    mat = mat or _mat(lim)                           # CP-102/CP-103: материал сепаратора
    wall = rol.get("wall_min", lim.wall_min)
    a = rol.get("a_w") or lim.a_k * D
    r = PtkResult(u, rid, D, gen=gen, M_req=m_req, dR=dR, hb=hb, band_fill=fill, sep_mat=mat)
    if not mat["ref"]:                                   # CP-103: запасной путь
        r.warnings.append("сепаратор: материал не из справочника — σ₋₁/σ_Hlim из limits "
                          "(sep_grade пуст; устарело, CP-103)")
    r.id, r.geom = config_id(u, rol, lim, holes, fast, None, gen, dR, hb, fill, mat)
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
    if rol.get("type") == "ball" and gen in ("bearing", "rim"):  # Д-45; CP-96: жёлоба на ободе нет
        x = "Т1" if gen == "bearing" else "Т5"
        r.n, r.z, r.excluded, r.tech = n, z, x, [x]
        return r
    R, by = r_sum(u, D, a, lim)
    brg = None
    if gen == "bearing":
        bk, need_D, need_d = bearing(D, R + dR, a, bears, lim)     # CP-95: dR -> крупнее подшипник
        brg = bears.get(bk) if bk else None
        if brg is None:
            r.errors.append(f"нет подшипника генератора с D ≥ {need_D:.1f} и d ≥ {need_d:.1f} мм "
                            f"в vendor_prices.yaml → bearings (Д-40)")
        else:
            R = (brg["D"] + D) / 2
            r.bearing = bk
            r.id, r.geom = config_id(u, rol, lim, holes, fast, brg, gen, 0.0, hb, fill, mat)
    else:                                               # Д-42: D_г — наружный Ø эксцентрика
        need_d = lim.shaft_d_min + 2 * (a + lim.ecc_wall_min)
        if need_d > 2 * R - D + 1e-9:
            by = "вал"
        R = (_ceil(max(2 * R - D, need_d) + 2 * dR, lim.dgen_step) + D) / 2   # CP-95: + 2·dR
    if gen == "rim":                                    # CP-96: подшипник на min радиусе эксцентрика
        fit = [b["D"] for k, b in bears.items() if not k.startswith("_")
               and b["d"] >= need_d - 1e-9]
        if fit and min(fit) + 2 * lim.rim_t_min > 2 * R - D + 1e-9:
            R = (_ceil(min(fit) + 2 * lim.rim_t_min, lim.dgen_step) + D) / 2
            by = "обод"
        MB1 = ptk_force.torque(n, z, a, R, D, rol["l"], rol.get("type", "roller"),
                               {"C0": 1000.0, "B": rol["l"]}, lim, lim.rows)["M_B"] / 1000
        bk, r.rim = rim_pick(2 * R - D, rol["l"], a, MB1, need_d, bears, lim)
        brg = bears.get(bk) if bk else None
        if brg is None:
            r.errors.append(f"обод .18: нет подшипника с d >= {need_d:.1f} и D <= "
                            f"{2 * R - D - 2 * lim.rim_t_min:.1f} мм, проходящего натяг (CP-96)")
        else:
            r.bearing = bk
            r.id, r.geom = config_id(u, rol, lim, holes, fast, brg, gen, dR, hb, fill, mat)
            if rol["l"] > brg["B"] + 1e-9:                # CP-96: обод шире подшипника
                r.warnings.append(f"обод .18 шире подшипника {bk}: {rol['l']:g} > {brg['B']:g} мм — "
                                  f"консоль {((rol['l'] - brg['B']) / 2):.2f} мм на сторону (OQ-48)")
    if dR > 1e-9:                                       # CP-95: R_Σ поднят под требуемый момент
        by = "M_req"
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
    pitch = (max(rol["l"], brg["B"]) if brg else rol["l"]) + hb   # Д-40; CP-95b: + высота пояса
    r.width = round(lim.rows * pitch + (lim.rows + 1) * lim.row_gap, 1)
    if not r.errors and (brg is not None or gen == "eccentric"):    # Д-46: детали .02, .03
        r.sep = ptk_parts.separator(n, R, a, D, rol["l"], pitch, r.phasing, lim, SEP_K)
        r.sep["band"] = ptk_parts.sep_band(r.sep, d_root, lim, fill)   # CP-98; CP-95b: fill
        r.warnings += r.sep["band"].pop("warnings")
        if fill:                                        # CP-95b: CAD утолщения пояса нет
            r.warnings.append(f"сепаратор: пояс до t_max {r.sep['band']['t']:g} мм — CAD пояса нет (OQ-46)")
        eb = {**brg, "m_rim": r.rim["m_g"]} if r.rim else brg      # CP-96: масса обода
        r.ecc = ptk_parts.eccentric(n, a, D, rol, eb, r.phasing, lim, gen, R)
        r.warnings += r.ecc.pop("warnings")
        r.parts += ptk_parts.parts(r.id, r.ecc)
        if r.rim:                                        # CP-96: обод .18 — по одному на ряд
            r.parts.append({"id": f"{r.id}.18", "name": "обод генератора", "variant": "",
                            "rows": list(range(1, lim.rows + 1))})
        r.spacer = ptk_parts.spacers(d_root, r.d_out, r.d_bc, r.geom["fastener"]["d_clear"],
                                     rol["l"], pitch, lim.rows, lim)
        r.warnings += r.spacer.pop("warnings")
        r.parts += ptk_parts.spacer_parts(r.id, r.spacer, lim.rows)
    if (brg is not None or gen == "eccentric") and not r.errors:
        bt = {**brg, "B": rol["l"]} if gen == "rim" else brg       # CP-96: дорожка обода = l
        t = ptk_force.torque(n, z, a, R, D, rol["l"], rol.get("type", "roller"), bt, lim,
                             lim.rows)
        r.M_H, r.M_B = t["M_H"], t["M_B"] or 0.0
        r.M_body_gen, r.M_body_ring = t["M_g"], t["M_v"]             # CP-98
        cand = [(r.M_H, "контакт"), (round(r.t_hold / holes.safety, 1), "крепление")]
        if brg is not None:
            cand.append((r.M_B, "подшипник"))
        if r.rim:                                        # CP-96: овализация обода — свой предел
            cand.append((r.rim["M_ov"], "обод"))
        sep_in = (r.sep, t["k_sep"], D, rol["l"], rol.get("type", "roller"), lim.rows, R, a, lim,
                  mat)
        ref = {}
        if r.sep:                                        # Д-116, CP-94: предел сепаратора
            r.M_sep, r.sep_why = ptk_force.sep_limit(*sep_in)
            ref = ptk_force.sep_refs(*sep_in)            # CP-98: M_row, M_win
            r.M_row, r.M_body_win = ref["M_row"], ref["M_win"]
            cand.append((r.M_sep, "сепаратор"))
        r.M, r.M_by = min(cand)
        if r.rim:                                        # CP-96: прогиб обода при принятом M, мм
            r.rim["dfl"] = (round(r.rim["dfl_allow"] * r.M / r.rim["M_ov"], 4)
                            if r.rim["M_ov"] else 0.0)
        body = [(r.M_body_gen, "генератор"), (r.M_body_ring, "венец")]
        r.M_by_body = min(body + ([(r.M_body_win, "окно")] if r.sep else []))[1]
        if r.sep:
            eta = round(r.M_sep / (lim.rows * r.M_row), 3) if r.M_row else 0.0
            r.sep_chk = {**ptk_force.sep_check(r.M, *sep_in), **ref,
                         "M_pack": r.M_sep, "eta_pack": eta}
        if r.M < lim.M_min:
            r.errors.append(f"M {r.M:g} < M_min {lim.M_min:g} Н·м, ограничивает: {r.M_by} (Д-41)")
    if gen == "eccentric":                               # Д-45
        r.tech += (["Т2", "Т3"] if rol.get("type") == "ball" else []) + ["Т4"]
    r.ok = not r.errors
    return r


def solve(u, rid, rol, gen, bears, lim, mounts, fast, m_req, mat=None):
    """CP-95 (Д-116 п. 2, Д-121), CP-95b, CP-99: обратная постановка для (u, тело, генератор)
    при целевом моменте m_req (вариант limits.u_calc → u → M_req).

    Переменные: крепление × dR (шаг r_step до r_up_max или D > d_out_max) × пояс (hb из
    band_h_list, на каждом hb сначала без fill, затем fill — пояс до t_max). dR идёт вверх (D растёт
    монотонно); пояс перебирается, только пока ограничивает сепаратор (иначе hb не поможет).
    Первое dR с M ≥ M_req — кандидат крепления с наименьшим hb; из кандидатов — наименьший
    (D, B, −M): габарит, затем длина пакета (масса на шаге 1 не считается, Д-48).
    Нет кандидата — реализуемая строка с наибольшим M (при равном — меньшие D, B) и ошибкой
    с потолками M_H, M_win, крепления, подшипника: что именно не пускает к M_req."""
    M_req, best, top, first = float(m_req), None, None, None
    n_up = int(round(lim.r_up_max / lim.r_step)) if lim.r_step > 0 else 0
    tiers = [(hb, f) for hb in (lim.band_h_list or (0.0,)) for f in (False, True)]
    for key, h in mounts.items():
        hit = False
        for i in range(n_up + 1):
            for hb, f in tiers:
                r = calc(u, rid, rol, lim, h, fast, bears, gen, round(i * lim.r_step, 6), hb, f,
                         m_req, mat)
                r.mount = key
                if r.excluded:                          # Т1/Т5 не зависят от dR, пояса, крепления
                    return r
                first = first or r
                if r.ok and (top is None or (r.M, -r.d_out, -r.width) > (top.M, -top.d_out, -top.width)):
                    top = r
                if r.ok and r.M >= M_req - 1e-9:
                    if best is None or (r.d_out, r.width, -r.M) < (best.d_out, best.width, -best.M):
                        best = r
                    hit = True
                    break
                if not r.ok or r.M_by != "сепаратор":   # пояс не поможет: ошибка или предел не сепаратор
                    break
            if hit or (lim.d_out_max and r.d_out > lim.d_out_max):
                break                                   # больший dR — больший D: дальше смысла нет
    if best is not None:
        return best
    top = top or first
    sf = mounts[top.mount].safety if top.mount in mounts else 1.0
    top.errors.append(f"M_req {M_req:g} Н·м не достигнут: наибольший M {top.M:g} ({top.M_by or '—'}); "
                      f"потолки — контакт M_H {top.M_H:g}, тело/окно M_win {top.M_body_win:g}, "
                      f"крепление {top.t_hold / sf:.1f}, подшипник {top.M_B:g} Н·м "
                      f"(dR ≤ {lim.r_up_max:g}, hb ≤ {max(lim.band_h_list or (0.0,)):g} мм, "
                      f"крепления {list(mounts)}; CP-95b)")
    top.ok = False
    return top


def sweep(rollers, bears, lim, mounts, fast, mode="first_ok", mats=None):
    """Д-33, Д-42: для (u, тело, генератор) — все крепления (all) или первое прошедшее (first_ok).
    CP-99/CP-101: перечни тел, креплений и генераторов берутся из слоя u_calc (ALL.ALL → u.ALL →
    вариант); для u с вариантами — обратная постановка solve() по каждому варианту (u, M_req)."""
    out = []
    for u in lim.u_list:
        variants = lim.u_calc.get(u) or {}
        if variants:                                    # CP-99: обратная постановка по вариантам
            for m, prm in sorted(variants.items()):
                rl, ms, gs = _scope(prm, rollers, mounts, lim, f"u_calc[{u}][{m:g}]")
                vl = _variant_limits(lim, prm)
                for ref in _mat_scope(prm, vl):        # CP-102: материалы варианта
                    mt = _mat(vl, ref, mats)
                    for rid, rol in rl.items():
                        for gen in gs:
                            out.append(solve(u, rid, rol, gen, bears, vl, ms, fast, m, mt))
            continue
        prm = lim.u_def.get(u, {})
        rl, ms, gs = _scope(prm, rollers, mounts, lim, f"u_calc[{u}].ALL")
        for ref in _mat_scope(prm, lim):                # CP-102: материалы слоя u
            mt = _mat(lim, ref, mats)
            for rid, rol in rl.items():
                for gen in gs:
                    rs = []
                    for key, h in ms.items():
                        r = calc(u, rid, rol, lim, h, fast, bears, gen, mat=mt)
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


def _body(r):
    """M_body_* (CP-98): генератор / венец / окно, в скобках — первый контакт."""
    if not r.get("M_body_gen"):
        return "—"
    w = f"{r['M_body_win']:g}" if r.get("M_body_win") else "—"
    return f"{r['M_body_gen']:g} / {r['M_body_ring']:g} / {w} ({r['M_by_body']})"


def profile_table(rows):
    """Д-38: профиль и нагрузки по исполнениям (раздел SPEC-10)."""
    t = ["### Профиль и нагрузки по исполнениям (Д-38)", "",
         "R_о/R, R_в/R — (8), (9) при φ = 90° (α = α max), на 1 Н реакции генератора.", "",
         "| ID | $a_\\omega$ | $R_\\Sigma$ | $R_\\Sigma$ задан | $D_\\text{г}$ | α max, ° | "
         "$R_\\text{о}/R$ | $R_\\text{в}/R$ | r верш., мм | перемычка сеп., мм | "
         "M тела: генер. / венец / окно, Н·м (первый) | Статус |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if not r["z"]:
            continue
        ro, rv = ptk_profile.contact_ratios(math.pi / 2, r["a_w"], r["R_sum"], r["z"])
        t.append(f"| {r['id']} | {r['a_w']} | {r['R_sum']} | {r['R_by']} | {r['Dgen']} | "
                 f"{r['alpha_max']} | {ro:.2f} | {rv:.2f} | {r['r_tip']} | {r['sep_web']} | "
                 f"{_body(r)} | {'OK' if r['ok'] else 'нет'} |")
    return "\n".join(t)


def phasing_table(lim, holes):
    """Таблица фазировки рядов и сдвигов сверловки для SPEC-10 (Д-19)."""
    order = pattern_order(holes)
    gaps = pin_gaps(holes)
    pins = (f", штифты Ø{holes.pin_d:g} в промежутках {gaps}" if gaps else ", без штифтов")
    head = (f"Сверловка венца: {holes.n}×{holes.bolt} через {360 / max(holes.n, 1):g}°{pins}; "
            f"порядок симметрии сверловки N = {order} (σ = {360 / order:g}°). "
            "Не зависит от тела качения, поэтому дана по u.")
    cols = ["u (z = u + 1)", "p, °", "g, °", "Венцов", "Ряд", "φ, °", "δ/p", "s, °",
            "Сепаратор, °", "Вариант"]
    rows = ["| " + " | ".join(cols) + " |",            # CP-106: разделитель — из шапки (было 11 на 10)
            "|" + "---|" * len(cols)]
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


def mreq_table(rows, lim):
    """CP-95, CP-99: решение под M_req по вариантам (u, M_req) — наименьший (D, B, −M) среди
    реализуемых строк; варианты — limits.u_calc → u → M_req."""
    pairs = sorted({(r["u"], round(float(r["M_req"]), 6)) for r in rows if r.get("M_req")})
    if not pairs:
        return ("не задано (`limits.u_calc` без вариантов `M_req`) — прямая постановка: M есть "
                "следствие габарита, а не вход.")
    t = ["| u | M_req, Н·м | ID | Тело | Генератор | Сепаратор | dR, мм | $R_\\Sigma$ | D | B | "
         "M, Н·м (огр.) |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for u, m in pairs:
        ok = [r for r in rows if r["u"] == u and r["ok"] and not r["excluded"]
              and abs(float(r["M_req"]) - m) < 1e-9]
        if not ok:
            t.append(f"| {u} | {m:g} | нет решения | — | — | — | — | — | — | — | — |")
            continue
        b = min(ok, key=lambda r: (r["d_out"], r["width"], -r["M"]))
        gen = (b["bearing"] + (" + обод" if b["gen"] == "rim" else "")
               if b["gen"] in ("bearing", "rim") else "эксцентрик")
        t.append(f"| {u} | {m:g} | `{b['id']}` | {b['roller']} | {gen} | {(b.get('sep_mat') or {}).get('ref') or '—'} | {b['dR']:g} | "
                 f"{b['R_sum']:g} | {b['d_out']:g} | {b['width']:g} | {b['M']:g} ({b['M_by']}) |")
    return "\n".join(t)


def tech_md():
    """Расшифровка техкодов (Д-45) для SPEC-10."""
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
    assert r.M > 0 and r.M_by in ("контакт", "подшипник", "крепление", "сепаратор"), (r.M, r.M_by)
    assert r.M <= min(r.M_H, r.M_B, r.t_hold / holes.safety, r.M_sep) + 0.1       # Д-41, Д-116
    assert r.M_sep > 0 and r.sep_chk["sig_b"] <= r.sep_chk["sig_allow"], r.sep_chk   # CP-94
    # CP-98: шаг ряда = l (B 7 < l 8) — пояс 0.95 мм лимитирует; усиление пояса поднимает M_sep,
    # ID не меняется (sep_band_t не в GEOM_LIMITS до CAD пояса, OQ-46)
    rr = calc(19, "t", b, PtkLimits(sep_band_t=3.0), holes, fast, bears)
    assert r.sep_chk["lim_elem"] == "пояс" and rr.sep["band"]["t"] == 3.0, (r.sep_chk, rr.sep)
    assert rr.M_sep > 1.2 * r.M_sep and rr.id == r.id, (rr.M_sep, r.M_sep)
    rh = calc(19, "t", b, lim, holes, fast, bears, "bearing", 0.0, 2.0, True)   # CP-95b: пояс
    assert rh.width == r.width + 4 * 2.0, (rh.width, r.width)
    assert rh.sep["band"]["h_mid"] == round(r.sep["band"]["h_mid"] + 2.0, 3), rh.sep["band"]
    assert rh.sep["band"]["t"] == rh.sep["band"]["t_max"] and rh.id != r.id, rh.sep["band"]
    assert rh.M_sep > r.M_sep, (rh.M_sep, r.M_sep)
    assert not calc(19, "t", b, PtkLimits(M_min=1e6), holes, fast, bears).ok
    assert not calc(19, "t", b, lim, holes, fast, {}).ok                         # нет подшипника
    assert c(19, rol={**b, "a_w": 0.5}).alpha_max < r.alpha_max   # меньше a_ω — меньше α
    assert c(19, rol={**b, "wall_min": 8.0}).d_out > r.d_out       # wall_min тела
    e = calc(19, "t", b, lim, holes, fast, {}, "eccentric")      # Д-42: каталог не нужен
    assert e.ok and not e.bearing and e.gen == "eccentric", e.errors
    assert e.Dgen >= lim.shaft_d_min + 2 * (e.a_w + lim.ecc_wall_min) - 1e-9
    assert abs(2 * e.R_sum - e.Dgen - e.Drol) < 1e-3 and e.M_B == 0.0
    assert e.M_by in ("контакт", "крепление", "сепаратор") and e.id != r.id, (e.M_by, e.id)
    assert e.width == 4 * 8.0 + 5 * lim.row_gap
    assert "Т4" in e.tech and not r.tech, (e.tech, r.tech)
    m = calc(19, "t", b, lim, holes, fast, bears, "rim")             # CP-96: обод .18
    assert m.ok and m.bearing and m.gen == "rim" and m.rim, m.errors
    assert bears[m.bearing]["D"] <= m.Dgen - 2 * lim.rim_t_min + 1e-9
    assert m.Dgen >= e.Dgen - 1e-9 and m.id not in (e.id, r.id), (m.Dgen, e.Dgen)
    assert bears[m.bearing]["d"] >= lim.shaft_d_min + 2 * (m.a_w + lim.ecc_wall_min) - 1e-9
    assert m.M_B > 0 and m.rim["M_ov"] > 0 and m.M <= min(m.M_B, m.rim["M_ov"], m.M_H) + 0.1
    assert m.rim["s_fit"] <= lim.rim_sigma_fit and m.rim["b"] == b["l"]
    assert m.ecc["t"] == bears[m.bearing]["B"]            # эксцентрик несёт только подшипник
    assert any(p["id"] == m.id + ".18" for p in m.parts), m.parts
    assert calc(19, "t", {"type": "ball", "d": 3.0, "l": 3.0}, lim, holes, fast, bears,
                "rim").excluded == "Т5"                           # CP-96: жёлоба на ободе нет
    bb = c(10, rol={"type": "ball", "d": 2.0, "l": 2.0})          # Д-45: шарик на подшипнике
    assert not bb.ok and bb.excluded == "Т1" and not bb.errors, bb
    be = calc(10, "t", {"type": "ball", "d": 2.0, "l": 2.0}, lim, holes, fast, {}, "eccentric")
    assert not be.excluded and be.tech == ["Т2", "Т3", "Т4"], be.tech
    assert tech_md().count("| Т") == len(TECH)
    big = calc(100, "t", b, PtkLimits(d_out_max=None, u_list=(10, 100)), holes, fast, {},  # Д-119: u=100 — свой список
              "eccentric")
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
    assert (lim.u_min, lim.u_max) == (lim.u_list[0], lim.u_list[-1])   # Д-119: диапазон из u_list
    assert (PtkLimits(u_list=(12, 30, 45)).u_min, PtkLimits(u_list=(12, 30, 45)).u_max) == (12, 45)
    try:
        load_config({"limits": {"u_min": 10, "u_list": [10, 20]}, "ring_mounts": {"x": {}},
                     "fasteners": {}})
        raise AssertionError("явный u_min в limits принят — диапазон задаётся только u_list (Д-119)")
    except ValueError:
        pass
    try:
        load_config({"limits": {"u_list": [20, 10]}, "ring_mounts": {"x": {}}, "fasteners": {}})
        raise AssertionError("u_list не по возрастанию принят")
    except ValueError:
        pass
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
    # CP-94: K20 = PTK-063-R3X8-22M6P2-C068EC (SPEC-10: 61819, 22×M6+2×Ø6, D ≤ 200) —
    # сепаратор ограничивает M: σ перемычки ≤ [σ], M_sep < M_H, M_by «сепаратор» (Д-116)
    k20 = calc(63, "R_D3x8", {"type": "roller", "d": 3.0, "l": 8.0}, PtkLimits(d_out_max=200.0),
               RingHoles(bolt="M6", n=22, pins=2, pin_d=6.0),
               {"M6": {"d_clear": 6.6, "dk": 10.0, "F_M": 9.3}},
               {"61819": {"d": 95.0, "D": 120.0, "B": 13.0, "C": 19.9, "C0": 18.8}})
    assert k20.ok and k20.id == "PTK-063-R3X8-22M6P2-C068EC", (k20.id, k20.errors)
    assert abs(k20.t_hold - 1740.7) < 0.1 and k20.sep["web"] == 3.015, (k20.t_hold, k20.sep)
    assert k20.M_by == "сепаратор" and k20.M == k20.M_sep < k20.M_H, (k20.M, k20.M_sep, k20.M_H)
    s20 = k20.sep_chk
    assert 120.0 < k20.M_sep < 300.0 and s20["by"] == "изгиб", (k20.M_sep, s20)
    assert s20["sig_b"] <= s20["sig_allow"] and s20["sig_H"] < s20["sigH_allow"], s20
    # CP-98: пояс K20 5.95 мм не лимитирует — M_sep как в CP-94 (188.1), предел — перемычка ряда 1
    assert abs(k20.M_sep - 188.1) < 0.2 and s20["lim_elem"] == "перемычка", (k20.M_sep, s20)
    assert s20["n_row_lim"] == 1 and k20.sep["band"]["h_mid"] == 5.95, (s20, k20.sep["band"])
    # CP-111: M_by = сепаратор — max(u_b, u_H) = 1 по определению (обе загрузки линейны по M);
    # расхождение — только округление M сепаратора до 0.1 в sep_check
    assert abs(max(s20["u_b"], s20["u_H"]) - 1.0) < 1e-3, (s20["u_b"], s20["u_H"])
    assert 0 < k20.M_row < k20.M_sep < 4 * s20["M_row_b"], (k20.M_row, k20.M_sep, s20)
    b20 = (k20.M_body_gen, k20.M_body_ring, k20.M_body_win)
    assert min(b20) > 0 and k20.M_H == min(b20[:2]) and k20.M <= min(b20), (b20, k20.M)
    assert k20.M_by_body in ("генератор", "венец", "окно") and s20["M_pack"] == k20.M_sep
    assert 0 < s20["eta_pack"] < 1, s20
    # CP-95 (Д-121): обратная постановка — dR поднимает R_Σ, ID меняется только при dR > 0
    e2 = calc(19, "t", b, lim, holes, fast, {}, "eccentric", 5.0)
    assert abs(e2.R_sum - e.R_sum - 5.0) < 1e-9 and e2.R_by == "M_req", (e2.R_sum, e.R_sum)
    assert e2.id != e.id and e2.d_out >= e.d_out and e2.geom.get("dR") == 5.0, (e2.geom, e.id)
    assert calc(19, "t", b, lim, holes, fast, {}, "eccentric", 0.0).id == e.id   # dR = 0 — ID прежний
    tgt = round(min(1.3 * e.M, 0.95 * e.M_H), 1)
    lq = PtkLimits(d_out_max=None, u_calc={19: {tgt: {}}, 10: {}, 63: {}},
                   u_list=(10, 19, 63))                                  # CP-99: таблица по u
    mts = {"a": holes, "b": RingHoles(bolt="M4", n=12)}
    s = solve(19, "t", b, "eccentric", {}, lq, mts, fast, tgt)
    assert s.ok and s.M >= tgt - 1e-9 and s.M_req == tgt and s.mount in mts, (s.M, s.dR, s.errors)
    sx = solve(19, "t", b, "eccentric", {}, lq, {"a": holes}, fast, 1e6)
    assert not sx.ok and "M_req" in sx.errors[-1], sx.errors
    assert "нет решения" not in mreq_table([asdict(s)], lq) and "нет решения" in mreq_table(
        [asdict(sx)], lq)                                                   # CP-99: по вариантам
    # CP-101 (Д-124): слои ALL.ALL -> u.ALL -> вариант; перечни mounts/rollers/gen_types
    lb, mb, _, _ = load_config({"limits": {"u_calc": {
        "ALL": {"ALL": {"mounts": ["M6x24P2"], "r_step": 2.0}},
        10: {"ALL": {"rollers": ["R_D8x16"]}, 500: {}, 700: {"mounts": ["M5x12P2"], "r_step": 0.5}},
        20: {}}}, "ring_mounts": {"M6x24P2": {}, "M5x12P2": {}}, "fasteners": {}})
    assert lb.u_list == (10, 20) and lb.u_calc[10][500.0]["r_step"] == 2.0, (lb.u_list, lb.u_calc)
    assert lb.u_calc[10][500.0]["rollers"] == ("R_D8x16",), lb.u_calc[10]
    assert lb.u_calc[10][700.0]["mounts"] == ("M5x12P2",) and lb.u_calc[10][700.0]["r_step"] == 0.5
    assert lb.u_calc[10][700.0]["rollers"] == ("R_D8x16",)      # слой u.ALL унаследован вариантом
    assert lb.u_def[20] == {"mounts": ("M6x24P2",), "r_step": 2.0}, lb.u_def[20]   # только ALL.ALL
    for badc in ({},                                    # пустая таблица
                 {"ALL": {"ALL": {}}},                  # только ALL — нет ни одного u
                 {"ALL": {"10": {}}, 10: {}},           # лишний ключ под ALL
                 {10: {100: {"mounts": ["НЕТ"]}}},      # крепления нет в ring_mounts
                 {10: {100: {"gen_types": ["nosuch"]}}},
                 {10: {100: {"mounts": "M6x24P2"}}},    # не список
                 {10: {100: {"nosuch": 1}}},            # неизвестный параметр
                 {10: {0: {}}}):                        # M_req <= 0
        try:
            load_config({"limits": {"u_calc": badc}, "ring_mounts": {"M6x24P2": {}},
                         "fasteners": {}})
        except ValueError:
            continue
        raise AssertionError(f"u_calc принял {badc}")
    lm, _, _, _ = load_config({"limits": {"u_calc": {10: {100: {"materials": ["38Х2МЮА:nitr"]}}}},
                               "ring_mounts": {"M6x24P2": {}}, "fasteners": {}})
    assert _parse_params("t", {"materials": ["40Х"]})["materials"] == ("40Х",), \
        "materials теряется в _parse_params (A-1)"
    assert _mat_scope({"materials": ["38Х2МЮА:nitr"]}, lm) == ("38Х2МЮА:nitr",), "materials — не перечень"
    assert _mat_scope({}, lm) == ("",), "марки по умолчанию нет — ожидался пустой ref"
    assert _mat(lm, "40Х")["m1_core"] == 509.0 and _mat(lm, "40Х")["src_m1"] == "materials"
    # CP-103 (Д-126): пределы слоя/ядра раздельно; в хэше только ref; смена σ не меняет ID
    m40 = _mat(lm, "40Х")
    assert m40["m1_core"] == 509.0 and m40["m1_case"] is None and m40["Hlim_core"] == 640.0, m40
    mn = _mat(lm, "38Х2МЮА:nitr")
    assert (mn["m1_case"], mn["m1_core"], mn["Hlim_case"], mn["depth"]) == \
        (608.0, 392.0, 1050.0, 0.4), mn
    g1 = geom_params(10, {"d": 3.0}, lm, RingHoles(), {}, mat=mn)
    g2 = geom_params(10, {"d": 3.0}, lm, RingHoles(), {}, mat={**mn, "m1_case": 700.0})
    assert g1 == g2 and g1["material"] == {"ref": "38Х2МЮА:nitr"}, g1
    assert _mat(PtkLimits(), "")["src_m1"] == "limits"
    lr = replace(PtkLimits(u_list=(32,)), u_range=(10, 63))
    assert (lr.u_min, lr.u_max) == (10, 63)
    try:                                        # CP-102: марки/состояния нет — ошибка
        _mat(lm, "НетТакой")
    except ValueError:
        pass
    else:
        raise AssertionError("нет ошибки на неизвестную марку в materials (CP-102)")
    try:                                                # rollers вне каталога — ошибка sweep
        sweep({"R_D3x8": {"type": "roller", "d": 3.0, "l": 8.0}}, {}, lb, mb, fast)
    except ValueError as e:
        assert "rollers" in str(e), e
    else:
        raise AssertionError("rollers вне каталога принят")
    bb3 = calc(19, "t", b, lim, holes, fast, bears, "bearing", 3.0)   # bearing: dR -> больший подшипник
    assert bb3.R_sum >= r.R_sum - 1e-9 and bb3.dR == 3.0 and "dR" not in bb3.geom, bb3.R_sum
    return True


if __name__ == "__main__":
    print(self_test())
