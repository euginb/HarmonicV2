"""Чтение ручных конфигураций specs/*.yaml (Д-60).

Ручные конфиги — только YAML: описание каждого параметра — комментарием прямо
в файле («_comment»-ключи JSON больше не нужны). Code-first данные машина
пишет в JSON (ptk_configs.json, ptk_designs.json, каталоги) — их читает json,
не этот модуль. Зависимость — PyYAML (pip install pyyaml).
"""

from pathlib import Path

try:
    import yaml
except ImportError:                     # внятная ошибка вместо traceback импорта
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs"


def load(name, base=None):
    """YAML-файл -> dict (Д-60). base — папка с файлом (по умолчанию specs/ корня
    репозитория); имя — с .yaml или без. Путь, существующий от текущей папки
    (например specs/cad_set.yaml из --spec), берётся как есть."""
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
    return True
