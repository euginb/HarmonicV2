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
    return True
