"""Номенклатура входных валов — продукт SH (Д-107, Д-109, Д-110; CP-91 этапы 1–2).

specs/shafts.yaml → shafts.<ID>: вход — name, d, bore, link, applies_to, note.
Проработка ссылается на запись: designs[].shaft = {id: SH-08-KEY} или {id: [SH-08-KEY,
SH-10-KEY]} — список: наименьшая проходящая конфигурация (как layout, Д-100); прочие поля
блока — переопределения OVERRIDE (обоснование — в note записи). Приоритет: переопределение
> запись номенклатуры > DEFAULTS (Д-107). Полный блок без id — переходный формат:
работает, предупреждение «устарел (Д-107)»; его tau_allow/sigma_crush — ручные значения.

Допуски — расчёт из материала (Д-110, OQ-36):
  [τ] = min(τ₋₁/(K_τ·S), 0.58·σт/S_т), τ₋₁ = 0.58·σ₋₁, σ₋₁ ≈ 0.43·σв (нет sigma_m1);
  [σсм] = min(σт вала, σт .03, σт шпонки)/S_см.
Материал .15 — марки products.yaml → PTK.parts.15.material по порядку: марка в
materials.yaml со σв/σт → пруток Ø ≥ d + 2·bar_allow в stock.yaml (в пределах d_range)
→ τ, σсм; берётся первая проходящая, отказы остальных — rejected. Коэффициенты DEFAULTS —
предварительные, сверить (OQ-36).
"""
import math
import re

from egm import config, materials

ID_RE = re.compile(r"^SH-(?P<d>\d{2,3})-(?P<link>[A-Z]+)(?:-(?P<sfx>[A-Z0-9]+))?$")
LINKS = ("key", "flat", "integral", "spline", "press")
FIELDS = ("name", "d", "bore", "link", "applies_to", "note")      # вход записи (Д-110)
TRANSIT = ("tau_allow", "sigma_crush", "wall_min", "length")      # переходные поля записи (Д-110)
OVERRIDE = ("bore", "tau_allow", "sigma_crush", "wall_min")       # переопределяемые в проработке

# Умолчания — единственный источник (они же документация умолчаний, SPEC-12 §5).
DEFAULTS = {
    "bore": 0.0,              # Ø отверстия, мм; 0 — сплошной
    "link": "key",            # соединение эксцентрик–вал
    "wall_min": 1.5,          # технологический минимум стенки полого вала у паза, мм (Д-110)
    # K_τ — эффективный коэффициент концентрации при кручении по типу соединения
    # (Д-112, проверено по справочным таблицам: шпоночный паз 1.4…1.7 при кручении —
    # берётся верх диапазона, т.к. материал вала — улучшенная сталь σв ≈ 980).
    "K_tau": {"key": 1.6, "flat": 1.3, "spline": 1.5, "integral": 1.2, "press": 2.5},
    "S": 3.5,                 # запас по усталости при кручении: покрывает НЕучтённый изгиб
                              # (роль прежнего заниженного [τ] = 15…30, Д-110). Калибровка
                              # (Д-112): 45 нормализованная — τ₋₁ = 0.58·290 = 168 МПа,
                              # [τ] = 168/(1.6·3.5) = 30 МПа, т.е. верх прежнего диапазона;
                              # 40Х улучшенная — 0.58·509/(1.6·3.5) = 53 МПа (пропорционально
                              # σ₋₁, а не подгонкой).
    "S_t": 2.0,               # запас по текучести (статика): для валов 1.5…2.5
    "S_crush": 3.5,           # запас по смятию: [σсм] = min(σт вала, .03, шпонки)/3.5;
                              # для шпонки 45 — 355/3.5 = 101 МПа, что совпадает с практикой
                              # 100…150 МПа для неподвижного соединения сталь–сталь
    "m1_k": 0.43,             # σ₋₁ ≈ m1_k·σв, если в materials.yaml нет sigma_m1
    "tau_k": 0.58,            # τ₋₁ = tau_k·σ₋₁ (энергетическая теория); консервативно:
                              # марочник 40Х даёт τ₋₁ = 240 МПа при σ₋₁ = 333 (0.72·σ₋₁)
    "bar_allow": 1.0,         # припуск на сторону, пруток → вал, мм
    "key_grade": "45",        # марка шпонки (ГОСТ 23360)
    "tau_allow": 25.0,        # [τ] без материала (нет materials/products — self_test, черновик)
    "sigma_crush": 100.0,     # [σсм] без материала
}


def parse_id(sid, where="shaft.id"):
    """ID SH-<d>-<link>[-<суффикс>] -> (d, link, суффикс | None); формат — ValueError."""
    m = ID_RE.match(str(sid))
    if not m:
        raise ValueError(f"{where}: ID «{sid}» — формат SH-<d>-<link>, пример SH-08-KEY (Д-107)")
    link = m["link"].lower()
    if link not in LINKS:
        raise ValueError(f"{where}: ID «{sid}» — тип соединения {link} не из {LINKS}")
    return int(m["d"]), link, m["sfx"]


def load(app=None):
    """specs/shafts.yaml через products.SH.configs.shafts (Д-79) -> dict."""
    app = config.load_app() if app is None else app
    return config.load(config.cfg_file(app, "products.SH.configs.shafts")) or {}


def check(nomen):
    """Формат номенклатуры -> [ошибка]: ID, неизвестные поля, d и link против ID."""
    fails = []
    for sid, rec in ((nomen or {}).get("shafts") or {}).items():
        w = f"specs/shafts.yaml: shafts.{sid}"
        try:
            d, link, _ = parse_id(sid, w)
        except ValueError as e:
            fails.append(str(e))
            continue
        rec = rec or {}
        bad = sorted(set(rec) - set(FIELDS) - set(TRANSIT))
        if bad:
            fails.append(f"{w}: неизвестные поля {bad} — допустимы {FIELDS}")
        if "d" not in rec:
            fails.append(f"{w}: нет d")
        elif round(float(rec["d"])) != d:
            fails.append(f"{w}: d = {rec['d']} не совпадает с номиналом ID (Ø{d})")
        if str(rec.get("link", link)) != link:
            fails.append(f"{w}: link = {rec.get('link')} не совпадает с ID ({link})")
    return fails


def resolve(spec, nomen, where):
    """designs[].shaft -> ([(ID | None, shaft)], предупреждения); кандидаты — по возрастанию d.

    shaft — словарь для ptk_design.design(): d, bore, link, wall_min, [tau_allow,
    sigma_crush]; _over — ключи ручных допусков. Неизвестный ID — ValueError (checks.md)."""
    spec, warn = dict(spec or {}), []
    base = {k: DEFAULTS[k] for k in ("bore", "link", "wall_min")}
    if "id" not in spec:
        warn.append(f"{where}.shaft: полный блок устарел (Д-107) — заменить на {{id: SH-…}}")
        sh = {**base, **spec}
        sh["_over"] = sorted(k for k in ("tau_allow", "sigma_crush") if k in spec)
        return [(None, sh)], warn
    ids = spec.pop("id")
    ids = ids if isinstance(ids, list) else [ids]
    if not ids:
        raise ValueError(f"{where}.shaft.id: пустой список (Д-110)")
    bad = sorted(set(spec) - set(OVERRIDE))
    if bad:
        raise ValueError(f"{where}.shaft: поля {bad} не переопределяются — допустимы {OVERRIDE} "
                         f"(d и link задаёт ID, Д-107)")
    reg = (nomen or {}).get("shafts") or {}
    out = []
    for sid in ids:
        parse_id(sid, f"{where}.shaft.id")
        if sid not in reg:
            raise ValueError(f"{where}.shaft.id: {sid} нет в specs/shafts.yaml → shafts (Д-107)")
        rec = reg[sid] or {}
        tr = [k for k in ("tau_allow", "sigma_crush", "wall_min") if k in rec]
        if tr:
            warn.append(f"specs/shafts.yaml: {sid}: переходные поля {tr} (Д-110) — допуск "
                        f"считается из материала; ручное значение — переопределением в проработке")
        sh = {**base, **{k: rec[k] for k in ("d", "bore", "link", "wall_min",
                                             "tau_allow", "sigma_crush") if k in rec}, **spec}
        sh["_over"] = sorted(k for k in ("tau_allow", "sigma_crush") if k in spec or k in rec)
        out.append((sid, sh))
    out.sort(key=lambda x: float(x[1]["d"]))
    return out, warn


def allow(p, link, others):
    """Допуски по свойствам марки p и σт сопряжённых деталей others {ecc, key} -> dict."""
    D = DEFAULTS
    sv, st, m1 = float(p["sigma_v"]), float(p["sigma_t"]), p.get("sigma_m1")
    est = m1 is None
    m1 = D["m1_k"] * sv if est else float(m1)
    t_f = D["tau_k"] * m1 / (D["K_tau"].get(link, D["K_tau"]["key"]) * D["S"])
    t_s = D["tau_k"] * st / D["S_t"]
    lim = {"shaft": st, **{k: float(v) for k, v in others.items() if v}}
    who = min(lim, key=lim.get)
    return {"tau_allow": round(min(t_f, t_s), 1), "tau_basis": "fatigue" if t_f <= t_s else "static",
            "sigma_crush": round(lim[who] / D["S_crush"], 1), "crush_basis": who,
            "props": "materials.yaml" + (" (σ₋₁ — оценка 0.43·σв)" if est else "")}


def _over(c, over):
    """Ручные допуски проработки поверх расчётных (Д-110: только с обоснованием в note)."""
    for k, basis in (("tau_allow", "tau_basis"), ("sigma_crush", "crush_basis")):
        if k in over:
            c[k], c[basis] = over[k], "override"
    return c


def pick(sh, tau, sig, mats, prods, stock):
    """Марка .15 и допуски (Д-110) -> dict: grade, state, props, tau_allow, tau_basis,
    sigma_crush, crush_basis, blank, rejected, errors, warnings.

    Первая марка, у которой есть свойства, пруток и проходят τ, σсм. Не прошла ни одна —
    показывается первая со свойствами и прутком (ошибки τ/σсм пишет ptk_design)."""
    D, d, link = DEFAULTS, float(sh["d"]), sh.get("link", "key")
    over = {k: float(sh[k]) for k in sh.get("_over", ()) if k in sh}
    base = {"grade": None, "state": None, "props": "по умолчанию", "blank": None,
            "tau_allow": D["tau_allow"], "tau_basis": "default",
            "sigma_crush": D["sigma_crush"], "crush_basis": "default",
            "rejected": [], "errors": [], "warnings": []}
    order = materials.part_materials(prods, "PTK", "15")
    if mats is None or not order:
        base["warnings"].append("материал .15 не подбирался (нет materials.yaml или "
                                "products.15.material) — допуски DEFAULTS egm/shafts.py")
        return _over(base, over)
    by = materials.stock_by_material(stock)
    pe = materials.props(mats, (materials.part_materials(prods, "PTK", "03") or [None])[0]) or {}
    pk = materials.props(mats, D["key_grade"]) or {}
    others = {"ecc": pe.get("sigma_t"), "key": pk.get("sigma_t")}
    need, first = d + 2 * D["bar_allow"], None
    for g in order:
        p, why, bar = materials.props(mats, g), "", None
        if p is None:
            why = "марки нет в materials.yaml"
        elif not (p.get("sigma_v") and p.get("sigma_t")):
            why = "нет sigma_v / sigma_t в materials.yaml (OQ-36)"
        else:
            bars = sorted(float(x) for x in (by.get(g) or {}).get("bars", []))
            bar = next((b for b in bars if b >= need - 1e-9), None)
            rng = p.get("d_range")
            if bar is None:
                why = f"нет прутка Ø ≥ {need:g} мм в stock.yaml"
            elif rng and not float(rng[0]) - 1e-9 <= bar <= float(rng[1]) + 1e-9:
                why = f"пруток Ø{bar:g} вне d_range {rng} — свойства не справедливы"
        if why:
            base["rejected"].append({"grade": g, "why": why})
            continue
        c = _over({**base, **allow(p, link, others), "grade": g, "state": p.get("state"),
                   "blank": f"пруток Ø{bar:g} (припуск {D['bar_allow']:g} на сторону)"}, over)
        fails = []
        if tau > c["tau_allow"] + 1e-9:
            fails.append(f"τ {tau:.1f} > [τ] {c['tau_allow']:g} МПа")
        if sig is not None and sig > c["sigma_crush"] + 1e-9:
            fails.append(f"σсм {sig:.0f} > [σсм] {c['sigma_crush']:g} МПа")
        if not fails:
            return c
        base["rejected"].append({"grade": g, "why": "; ".join(fails)})
        first = first or c
    if first:
        return first
    base["errors"].append("материал .15: ни одна марка products.15.material не прошла по "
                          "справочнику/заготовке — см. shaft.rejected (Д-110)")
    return _over(base, over)


def bore_max(d, t1, T_in, ta, wmin):
    """Наибольшее отверстие полого вала, мм: τ ≤ [τ] и стенка у паза ≥ wall_min.
    None — не проходит и сплошной вал."""
    d_t = d - t1
    if d_t <= 0 or ta <= 0:
        return None
    tau0 = 16 * T_in * 1e3 / (math.pi * d_t ** 3)
    if tau0 > ta:
        return None
    b = min(d_t * (1 - tau0 / ta) ** 0.25, d - 2 * (t1 + wmin))
    return math.floor(b * 10 + 1e-9) / 10 if b > 0 else 0.0


def check_repo():
    """Сверка specs/shafts.yaml и ссылок проработок на ID (ошибки — в checks.md)."""
    app = config.load_app()
    nomen = load(app)
    fails = check(nomen)
    inp = config.load(config.cfg_file(app, "products.PTK.configs.design_input")) or {}
    for d in inp.get("designs", []):
        try:
            resolve(d.get("shaft") or {}, nomen, f"designs.{d.get('name')}")
        except ValueError as e:
            fails.append(str(e))
    assert not fails, fails
    return True


def self_test():
    assert parse_id("SH-08-KEY") == (8, "key", None)
    assert parse_id("SH-20-KEY-B6") == (20, "key", "B6")
    for bad in ("SH-8-KEY", "SH-08-XXX", "sh-08-key"):
        try:
            parse_id(bad)
            raise AssertionError(bad)
        except ValueError:
            pass
    nomen = {"shafts": {"SH-08-KEY": {"name": "Ø8", "d": 8.0, "link": "key"},
                        "SH-10-KEY": {"name": "Ø10", "d": 10.0, "link": "key"}}}
    assert check(nomen) == [], check(nomen)
    assert len(check({"shafts": {"SH-08-KEY": {"d": 10.0, "x": 1}}})) == 2
    c, w = resolve({"id": ["SH-10-KEY", "SH-08-KEY"], "tau_allow": 25.0}, nomen, "designs.K")
    assert [s for s, _ in c] == ["SH-08-KEY", "SH-10-KEY"] and c[0][1]["tau_allow"] == 25.0, c
    assert c[0][1]["_over"] == ["tau_allow"] and c[0][1]["wall_min"] == DEFAULTS["wall_min"] and not w
    c, w = resolve({"d": 8.0, "link": "key"}, None, "designs.K")
    assert c[0][0] is None and "устарел" in w[0], w
    for bad in ({"id": "SH-12-KEY"}, {"id": "SH-08-KEY", "d": 9.0}):
        try:
            resolve(bad, nomen, "designs.K")
            raise AssertionError(bad)
        except ValueError:
            pass
    # Допуски — из DEFAULTS, без магических чисел: смена коэффициентов не ломает self_test,
    # но проверяется сама формула [τ] = τ₋₁/(K_τ·S), τ₋₁ = tau_k·m1_k·σв (нет sigma_m1).
    k, s_ = DEFAULTS["K_tau"]["key"], DEFAULTS["S"]
    # 45 нормализация: sigma_m1 нет — σ₋₁ оценивается как m1_k·σв (консервативнее справочника)
    a = allow({"sigma_v": 600, "sigma_t": 355}, "key", {"shaft": 355, "ecc": 785, "key": 355})
    assert a["tau_allow"] == round(DEFAULTS["tau_k"] * DEFAULTS["m1_k"] * 600 / (k * s_), 1), a
    assert a["tau_basis"] == "fatigue" and "оценка" in a["props"], a
    assert a["sigma_crush"] == round(355 / DEFAULTS["S_crush"], 1), a
    # 40Х улучшенная: sigma_m1 из марочника точнее оценки 0.43·σв; смятие лимитирует шпонка 45
    a = allow({"sigma_v": 980, "sigma_t": 785, "sigma_m1": 509}, "key",
              {"shaft": 785, "ecc": 785, "key": 355})
    assert a["tau_allow"] == round(DEFAULTS["tau_k"] * 509 / (k * s_), 1), a
    assert a["crush_basis"] == "key" and a["sigma_crush"] == round(355 / DEFAULTS["S_crush"], 1), a
    p = pick({"d": 8.0, "link": "key", "tau_allow": 25.0, "_over": ["tau_allow"]},
             10.0, None, None, None, None)
    assert p["tau_allow"] == 25.0 and p["tau_basis"] == "override" and p["warnings"], p
    assert abs(bore_max(10.0, 1.8, 0.0, 30.0, 1.5) - 3.4) < 1e-9
    assert bore_max(8.0, 1.2, 100.0, 25.0, 1.5) is None
    return True
