"""Чтение конфигураций: configs/application.yaml (общий, Д-64) и specs/*.yaml (Д-60).

Общий конфиг configs/application.yaml — пути, ссылки на пучок текущих конфигов,
разделы продуктов, механизм чертежей; читается load_app(), ссылки на файлы
резолвит cfg_file(). Ручные конфиги specs/*.yaml — только YAML: описание каждого
параметра — комментарием прямо в файле («_comment»-ключи JSON больше не нужны).
Code-first данные машина пишет в JSON (ptk_configs.json, ptk_designs.json,
каталоги) — их читает json, не этот модуль. Зависимость — PyYAML (pip install pyyaml).
"""

from pathlib import Path

try:
    import yaml
except ImportError:                     # внятная ошибка вместо traceback импорта
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs"
APP_FILE = ROOT / "configs" / "application.yaml"   # общий конфиг приложения (Д-64)


def load_app():
    """configs/application.yaml -> dict (Д-64). Файла нет — {} (работают значения
    по умолчанию в коде). Сами конфиги в него НЕ вкладываются — ссылки (configs:),
    пути резолвит cfg_file."""
    if yaml is None:
        raise ValueError("PyYAML не установлен: pip install pyyaml "
                         "(конфиги configs/application.yaml и specs/*.yaml, Д-60/Д-64)")
    if not APP_FILE.exists():
        return {}
    return yaml.safe_load(APP_FILE.read_text(encoding="utf-8"))


def app_section(app, key):
    """Раздел application.yaml по точечному пути: 'products.PTK' -> dict.
    Узла нет — KeyError с внятным текстом (Д-64)."""
    node = app
    walked = []
    for part in key.split("."):
        walked.append(part)
        if not isinstance(node, dict) or part not in node:
            raise KeyError(f"configs/application.yaml: нет узла {'.'.join(walked)} (Д-64)")
        node = node[part]
    return node


def cfg_file(app, key):
    """Ссылка на конфиг из application.yaml (точечный путь, Д-64) -> Path от корня
    репозитория: 'configs.products' -> <корень>/specs/products.yaml."""
    rel = app_section(app, key)
    if not isinstance(rel, str) or not rel:
        raise ValueError(f"configs/application.yaml: {key}: путь не строка: {rel!r} (Д-64)")
    return ROOT / rel


def load(name, base=None):
    """YAML-файл -> dict (Д-60). base — папка с файлом (по умолчанию specs/ корня
    репозитория); имя — с .yaml или без. Путь, существующий от текущей папки
    (например specs/cad_set.yaml из --spec), берётся как есть; абсолютный путь —
    тоже (ссылки application.yaml резолвит cfg_file, Д-64)."""
    if yaml is None:
        raise ValueError("PyYAML не установлен: pip install pyyaml "
                         "(ручные конфиги specs/*.yaml, Д-60)")
    p = Path(name)
    if p.suffix != ".yaml":
        p = p.with_suffix(".yaml")
    if base is None and not p.exists():
        p = SPECS / p.name
    return yaml.safe_load((base / p.name if base else p).read_text(encoding="utf-8"))


def self_test():
    assert yaml is not None, "нужен PyYAML: pip install pyyaml (Д-60)"
    # комментарии не ломают разбор; типы — как в JSON: 1.0 -> float, null -> None
    data = yaml.safe_load("# пояснение\nключ: 1.0\nсписок: [1, 2]\nвложение:\n  параметр: null\n")
    assert data == {"ключ": 1.0, "список": [1, 2], "вложение": {"параметр": None}}, data
    # Д-64: точечный путь и ссылка на конфиг (без файлов на диске)
    app = {"configs": {"products": "specs/products.yaml"},
           "products": {"PTK": {"enabled": True,
                                "configs": {"input": "specs/ptk_input.yaml"}}}}
    assert app_section(app, "products.PTK")["enabled"] is True
    assert cfg_file(app, "configs.products") == ROOT / "specs" / "products.yaml"
    assert cfg_file(app, "products.PTK.configs.input") == ROOT / "specs" / "ptk_input.yaml"
    for bad in ("products.HD.configs.input", "configs.stock"):
        try:
            cfg_file(app, bad)
            raise AssertionError(bad)
        except KeyError:
            pass
    return True
