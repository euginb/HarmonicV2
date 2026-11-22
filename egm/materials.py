"""Материалы и заготовки по материалам (Д-67, CP-57).

specs/materials.yaml — справочник марок: обозначение для графы 3 основной надписи,
плотность, термообработка, применение. Деталь ссылается на марки:
products.yaml → parts.<NN>.material — список по предпочтению.
specs/stock.yaml → materials.<марка> — у каждой марки свой набор форм (tubes, sheets,
bars): сортамент зависит от материала (40ХН2МА — в основном толстостенные
горячедеформированные трубы ГОСТ 8732; лист ГОСТ 19904 — в основном 08пс, TECH-01).
Старый формат stock.yaml (tubes/sheets/bars без марки) читается как марка None.
Ключи марок — строки ("45" в YAML — в кавычках; число приводится к строке).
"""
FORMS = ("tubes", "sheets", "bars")


def grades(mats):
    """materials.yaml -> {марка (str): запись}."""
    return {str(k): (v or {}) for k, v in ((mats or {}).get("materials") or {}).items()}


def stock_by_material(stock):
    """stock.yaml -> {марка | None: {tubes, sheets, bars}}."""
    if not stock:
        return {}
    if "materials" in stock:
        return {str(k): {f: list((v or {}).get(f) or []) for f in FORMS}
                for k, v in (stock.get("materials") or {}).items()}
    return {None: {f: list(stock.get(f) or []) for f in FORMS}}


def title(mats, grade):
    """Графа 3 основной надписи по марке; нет в справочнике — сама марка; нет марки — ""."""
    if grade is None or grade == "":
        return ""
    return grades(mats).get(str(grade), {}).get("title") or str(grade)


def part_materials(prods, code, nn):
    """Марки детали code.nn по предпочтению (products.yaml → material) или []."""
    it = (((prods or {}).get(code) or {}).get("parts") or {}).get(nn) or {}
    return [str(m) for m in (it.get("material") or [])]


SEP = ":"                      # CP-102: разделитель марки и состояния — "38Х2МЮА:nitr"


def split_ref(ref):
    """CP-102: ссылка "марка[:состояние]" -> (марка, состояние | None)."""
    s = str(ref or "").strip()
    if not s:
        return "", None
    g, _, st = s.partition(SEP)
    return g.strip(), (st.strip() or None)


def states(mats, grade):
    """CP-102: именованные состояния марки (materials.yaml → <марка>.states) или {}."""
    g, _ = split_ref(grade)
    return {str(k): (v or {}) for k, v in ((grades(mats).get(g) or {}).get("states") or {}).items()}


def state_props(mats, grade, state):
    """CP-102/CP-103 (Д-126): состояние марки -> {heat, for, core, case, depth} | None.
    core — переопределения свойств ядра ({} — ядро не меняется: азотирование ниже отпуска);
    case — пределы поверхностного слоя {sigma_m1, sigma_Hlim, depth, hv} | None. Слой НЕ
    сливается в плоские поля марки (A-4): слой и ядро считаются раздельно (egm/ptk_force.py).
    Нет состояния — None (марка считается в состоянии поставки)."""
    st = states(mats, grade).get(str(state)) if state else None
    if st is None:
        return None
    case = {k: v for k, v in (st.get("case") or {}).items() if v is not None} or None
    core = {k: v for k, v in (st.get("core") or {}).items() if v is not None}
    return {"heat": st.get("heat"), "for": st.get("for"), "core": core, "case": case,
            "depth": float((case or {}).get("depth") or 0.0)}


# Ключи props(): прежний набор (Д-110) + CP-103. sigma_H — устарело (Д-126), остаётся в наборе
# ради совместимости вызовов (egm/shafts.py его не читает); контакт — sigma_Hlim / hb.
PROPS = ("sigma_v", "sigma_t", "sigma_m1", "sigma_H", "sigma_Hlim", "hb", "rho", "state",
         "d_range")


def props(mats, grade, state=None):
    """Механические свойства марки (Д-110, OQ-36; CP-102: состояние) -> {PROPS} | None — марки
    нет в справочнике. Отсутствующие поля — None (не ошибка). state — ключ materials.yaml →
    <марка>.states: на плоские поля накладываются только переопределения ЯДРА (states.<k>.core);
    свойства слоя (case) — только в sep_props (CP-103, A-4)."""
    if grade is None:
        return None
    g = grades(mats)
    gname, _ = split_ref(grade)
    if gname not in g:
        return None
    it = g[gname]
    out = {k: it.get(k) for k in PROPS}
    if state:
        sp = state_props(mats, gname, state)
        if sp is None:
            return None
        out.update({k: v for k, v in sp["core"].items() if k in out})
        out["state"] = sp.get("heat") or out["state"]
    return out


def hlim_core(p):
    """σ_Hlim ядра, МПа -> (σ | None, источник): поле sigma_Hlim, иначе 2·HB + 70
    (ГОСТ 21354-87, улучшение — сверить, OQ-49)."""
    if p.get("sigma_Hlim") is not None:
        return float(p["sigma_Hlim"]), "sigma_Hlim"
    if p.get("hb") is not None:
        return 2.0 * float(p["hb"]) + 70.0, "2·HB+70"
    return None, None


def sep_props(mats, ref):
    """CP-103 (Д-126): материал сепаратора по ссылке "марка[:состояние]" -> {ref, grade, state,
    core: {sigma_m1, sigma_Hlim}, case: {sigma_m1, sigma_Hlim, depth, hv} | None, depth,
    src_Hcore} | None — марки или состояния нет (вход неверный). Только ПРЕДЕЛЫ: запасы —
    limits (egm/ptk.py). Нет числа — None в поле; ошибку «нет данных» пишет ptk._mat."""
    gname, st = split_ref(ref)
    if not gname:
        return None
    p = props(mats, gname, st)
    if p is None:
        return None
    H, src = hlim_core(p)
    c = state_props(mats, gname, st)["case"] if st else None
    case = {k: c.get(k) for k in ("sigma_m1", "sigma_Hlim", "depth", "hv")} if c else None
    return {"ref": f"{gname}{SEP}{st}" if st else gname, "grade": gname, "state": st,
            "core": {"sigma_m1": p.get("sigma_m1"), "sigma_Hlim": H}, "case": case,
            "depth": float((case or {}).get("depth") or 0.0), "src_Hcore": src}


def check(mats, prods, stock):
    """Ошибки: марки products.yaml и stock.yaml, которых нет в materials.yaml; трубы без D, s."""
    fails, known = [], set(grades(mats))
    for code, prod in (prods or {}).items():
        if not isinstance(prod, dict):
            continue
        for nn, it in (prod.get("parts") or {}).items():
            ms = (it or {}).get("material")
            if ms is None:
                continue
            if not isinstance(ms, list):
                fails.append(f"products.yaml: {code}.{nn}.material — нужен список марок (Д-67)")
                continue
            fails += [f"products.yaml: {code}.{nn}: марки {m} нет в materials.yaml (Д-67)"
                      for m in ms if str(m) not in known]
    for m, forms in stock_by_material(stock).items():
        if m is not None and m not in known:
            fails.append(f"stock.yaml: марки {m} нет в materials.yaml (Д-67)")
        for t in forms["tubes"]:
            if not isinstance(t, dict) or "D" not in t or "s" not in t:
                fails.append(f"stock.yaml: {m}: труба {t} — нужны D и s")
    return fails


def _load(app, key):
    from egm import config
    try:
        p = config.cfg_file(app, key)
    except Exception:
        return {}
    return config.load(p) if p.exists() else {}


def check_repo():
    """Сверка реальных конфигов (configs/application.yaml → configs.*): ошибки — в checks.md."""
    from egm import config
    app = config.load_app()
    fails = check(_load(app, "configs.materials"), _load(app, "configs.products"),
                  _load(app, "configs.stock"))
    assert not fails, fails
    return True


def self_test():
    mats = {"materials": {"40Х": {"title": "Сталь 40Х ГОСТ 4543-2016"}, 45: {}}}
    prods = {"PTK": {"parts": {"02": {"material": ["40Х", "38Х2МЮА"]}, "04": {}},
                     "layouts": {}}, "version": 7}
    stock = {"materials": {"40Х": {"bars": [70.0]}, "45": {"tubes": [{"D": 70.0}]}}}
    f = check(mats, prods, stock)
    assert len(f) == 2 and "38Х2МЮА" in f[0] and "D и s" in f[1], f
    assert title(mats, "40Х").startswith("Сталь 40Х") and title(mats, 45) == "45", title(mats, 45)
    assert title(mats, None) == "" and title(mats, "Х") == "Х"
    assert stock_by_material({"tubes": [1]})[None]["tubes"] == [1]
    assert stock_by_material(stock)["40Х"] == {"tubes": [], "sheets": [], "bars": [70.0]}
    assert part_materials(prods, "PTK", "02") == ["40Х", "38Х2МЮА"]
    assert part_materials(prods, "PTK", "09") == [] and part_materials(prods, "HD", "01") == []
    assert props(mats, "40Х")["sigma_v"] is None and props(mats, 45)["state"] is None
    assert props(mats, "Х") is None and props(mats, None) is None
    # CP-103 (Д-126; A-4, A6): слой не сливается в props; набор ключей не сужается
    m2 = {"materials": {"38Х2МЮА": {
        "sigma_v": 980, "sigma_t": 835, "sigma_m1": 392, "hb": 285,
        "states": {"nitr": {"heat": "азот.", "core": {},
                            "case": {"sigma_m1": 608, "sigma_Hlim": 1050, "depth": 0.4,
                                     "hv": 650}}}}}}
    old = {"sigma_v", "sigma_t", "sigma_m1", "sigma_H", "rho", "state", "d_range"}
    p0, p1 = props(m2, "38Х2МЮА"), props(m2, "38Х2МЮА", "nitr")
    assert set(p0) >= old and set(p1) >= old, (set(p0), set(p1))
    assert p1["sigma_m1"] == 392 and p1["state"] == "азот.", p1
    s1 = sep_props(m2, "38Х2МЮА:nitr")
    assert s1["core"] == {"sigma_m1": 392, "sigma_Hlim": 640.0}, s1
    assert s1["src_Hcore"] == "2·HB+70", s1
    assert s1["case"]["sigma_m1"] == 608 and s1["depth"] == 0.4, s1
    assert s1["ref"] == "38Х2МЮА:nitr", s1
    s0 = sep_props(m2, "38Х2МЮА")
    assert s0["case"] is None and s0["depth"] == 0.0, s0
    assert sep_props(m2, "38Х2МЮА:нет") is None and sep_props(m2, "") is None
    return True
