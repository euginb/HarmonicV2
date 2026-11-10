"""egm/doc_yaml.py — переиспользуемый вывод машиночитаемых результатов в КОММЕНТИРОВАННЫЙ YAML.

Зачем. Выходы расчётных шагов (ptk_configs, ptk_designs, каталог) — сотни листьев с
сокращёнными именами. JSON их хранит, но не объясняет: смысл ключа восстанавливался
только чтением кода. Здесь тот же результат пишется YAML, где над каждым ключом стоит
комментарий, а в шапке файла — глоссарий сокращений.

Как это устроено. Комментарии не выводятся из данных (сериализатор видит только
значения), поэтому описания живут в таблице конкретного документа — наследника Doc:
  GLOSSARY  точные пути ключей;
  PATTERNS  шаблоны для повторяющихся узлов: '*' — любой сегмент, '#' — номер,
            'x[]' — элемент списка, '(a|b)' — альтернатива; значение None означает
            «взять из EXTRA по последнему сегменту» (общий словарь штифтов и т.п.);
  GENERIC   словарь по последнему сегменту — последний рубеж, чтобы без комментария
            не осталось ни одного ключа;
  HEADER    шапка файла: назначение, кто пишет, глоссарий сокращений.

Формат. Эмиттер свой (не yaml.dump): нужны комментарии и предсказуемый порядок ключей.
Ключи-номера позиций и прочие «числовые» строки выводятся в кавычках: YAML 1.1 читает
010 как 8, а 09 как строку — без кавычек тип ключа зависел бы от номера позиции.
Списки скаляров — потоковым видом [a, b, c]; float печатается repr(), чтобы 45.0 не
превратилось в 45 и не прочиталось как int.

Пример наследника — egm/design_doc.py (проработки шага 2), egm/ptk_doc.py (шаг 1),
egm/catalog_doc.py (каталог линейных подшипников).
"""

import json
import re

try:
    import yaml
except ImportError:                     # внятная ошибка вместо traceback импорта
    yaml = None

_NUM = re.compile(r"^[-+]?(?:\d[\d_]*)(?:\.\d*)?(?:[eE][-+]?\d+)?$|^[-+]?\.\d+$")
_YAML_KW = {"null", "true", "false", "yes", "no", "on", "off", "~"}
_NEEDS_Q = re.compile(r"[:#\[\]{}&*!|>'\"%@`,\t]|^ | $")
_PLAIN_KEY = re.compile(r"^[A-Za-zА-Яа-яЁё_][\wА-Яа-яЁё.\-]*$")


def scalar(v):
    """Скаляр YAML: строка в кавычках, если YAML прочитал бы её иначе."""
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v != v or v in (float("inf"), float("-inf")):
            return repr(v)
        return repr(v)                           # точный round-trip (7.0 → «7.0», не «7»)
    s = str(v)
    if s == "" or _NUM.match(s) or s.lower() in _YAML_KW or _NEEDS_Q.search(s):
        return json.dumps(s, ensure_ascii=False)
    return s


def key(k):
    """Ключ YAML: номер позиции и материал в кавычках, обычные имена — без."""
    k = str(k)
    if _NUM.match(k) or not _PLAIN_KEY.match(k) or k.lower() in _YAML_KW:
        return json.dumps(k, ensure_ascii=False)
    return k


def _seg_re(seg):
    """Сегмент шаблона -> регулярное выражение."""
    if seg == "*":
        return "[^.]+"
    if seg == "#":
        return r"\d+"
    if seg.startswith("(") and seg.endswith(")"):
        return seg                                  # альтернатива, напр. (ext|int)
    if seg.endswith("[]"):
        return re.escape(seg[:-2]) + r"\[\]"
    return re.escape(seg)


def _compile(pattern):
    return re.compile("^" + r"\.".join(_seg_re(s) for s in pattern.split(".")) + "$")


class Doc:
    """Документ: шапка + таблица комментариев + эмиттер.

    Наследник задаёт HEADER, GLOSSARY, PATTERNS, GENERIC (и при необходимости EXTRA —
    словарь последнего сегмента для шаблонов со значением None). Файл и чтение —
    в наследнике: dump()/load_specs().
    """

    HEADER = ""
    GLOSSARY = {}
    PATTERNS = []
    GENERIC = {}
    EXTRA = {}

    def __init__(self):
        self._rules = [(_compile(p), t) for p, t in self.PATTERNS]
        self._rules.sort(key=lambda r: -r[0].pattern.count(r"\."))
        self._cache = {}

    def comment(self, path):
        """Комментарий к пути ключа: точное совпадение, шаблоны, EXTRA, GENERIC."""
        if path in self._cache:
            return self._cache[path]
        txt = self.GLOSSARY.get(path)
        if txt is None:
            for rx, t in self._rules:
                if rx.match(path):
                    txt = self.EXTRA.get(path.rsplit(".", 1)[-1]) if t is None else t
                    break
        if txt is None:
            txt = self.GENERIC.get(path.rsplit(".", 1)[-1].replace("[]", ""))
        self._cache[path] = txt or ""
        return self._cache[path]

    # -- эмиттер ---------------------------------------------------------
    def _emit(self, node, indent, lines, path, inline=None):
        """Узел -> строки YAML с комментариями. inline — префикс первой строки («- »)."""
        pad = " " * indent
        # элемент списка: первая строка начинается с «- » (2 знака), остальные ключи
        # того же словаря выравниваются по нему -> отступ +2
        pad2 = " " * (indent + 2) if inline else pad
        step = 4 if inline else 2
        if isinstance(node, dict):
            if not node:
                lines.append(pad + "{}")
                return
            first = True
            for k, v in node.items():
                p = f"{path}.{k}" if path else str(k)
                pre = pad + (inline if (first and inline) else "")
                if not (first and inline):
                    pre = pad2
                c = self.comment(p)
                if c:
                    lines.append((pad + "  " if (first and inline) else pad2) + "# " + c)
                kt = key(k)
                if isinstance(v, dict) and v:
                    lines.append(f"{pre}{kt}:")
                    self._emit(v, indent + step, lines, p)
                elif isinstance(v, list) and v:
                    if all(not isinstance(x, (dict, list, tuple)) for x in v):
                        lines.append(f"{pre}{kt}: [{', '.join(scalar(x) for x in v)}]")
                    else:
                        lines.append(f"{pre}{kt}:")
                        if all(isinstance(x, (list, tuple))
                               and all(not isinstance(y, (dict, list, tuple)) for y in x)
                               for x in v):         # список подсписков скаляров: [[a, b], …]
                            for x in v:
                                lines.append(" " * (indent + step) + "- [" +
                                             ", ".join(scalar(y) for y in x) + "]")
                            first = False
                            continue
                        for item in v:
                            if isinstance(item, (dict, list, tuple)):
                                self._emit(list(item) if isinstance(item, tuple) else item,
                                           indent + step, lines, p + "[]", inline="- ")
                            else:               # скаляр в списке (в т.ч. null)
                                lines.append(" " * (indent + step) + "- " + scalar(item))
                else:
                    if isinstance(v, list):
                        lines.append(f"{pre}{kt}: []")
                    elif isinstance(v, dict):
                        lines.append(f"{pre}{kt}: {{}}")
                    else:
                        lines.append(f"{pre}{kt}: {scalar(v)}")
                first = False
        elif isinstance(node, list):
            for item in node:
                if isinstance(item, (dict, list, tuple)):
                    self._emit(list(item) if isinstance(item, tuple) else item,
                               indent, lines, path, inline="- ")
                else:
                    lines.append(pad + "- " + scalar(item))
        else:
            lines.append(pad + scalar(node))

    def dump(self, data):
        """Данные -> текст файла: шапка, затем записи (список — через пустую строку)."""
        self._cache.clear()
        head = self.HEADER.rstrip("\n")
        lines = [head, ""] if head else []
        if isinstance(data, list):
            for i, rec in enumerate(data):
                if i:
                    lines.append("")
                self._emit(rec, 0, lines, "", inline="- ")
        else:
            self._emit(data, 0, lines, "")
        return "\n".join(lines) + "\n"


def load(path):
    """YAML -> данные (PyYAML обязателен; без него — внятная ошибка)."""
    if yaml is None:
        raise ValueError(f"PyYAML не установлен: pip install pyyaml (чтение {path})")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def self_test():
    """Эмиттер: типы и значения сохраняются, номера позиций — строки в кавычках."""
    class _T(Doc):
        HEADER = "# test"
        GLOSSARY = {"a.b": "комментарий a.b", "a.parts.09": "позиция 09"}
        PATTERNS = [(r"a.items[].x", "x элемента")]
        GENERIC = {"y": "игрек"}

    d = _T()
    data = [{"a": {"b": 1.0, "parts": {"09": "61810", "010": "c"},
                   "items": [{"x": 2, "y": [1.5, None]}, {"x": 3, "y": []}]},
             "s": "010", "n": None, "lst": [[1, 2], [3, 4]]}]
    txt = d.dump(data)
    assert yaml.safe_load(txt) == data, txt
    assert '"09":' in txt and '"010":' in txt and '"010"' in txt
    assert "# комментарий a.b" in txt and "# позиция 09" in txt
    assert "# x элемента" in txt and "# игрек" in txt
    assert "s: \"010\"" in txt and "n: null" in txt
    assert d.comment("нет.такого.пути") == ""
    return True
