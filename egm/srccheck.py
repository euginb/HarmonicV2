"""Проверка исходников (Д-79, CP-59): каждый *.py проекта компилируется (compile, без
выполнения). Макросы FreeCAD (tools/freecad_*.py) вне FreeCAD не импортируются, и их
синтаксис self-тесты модулей не видят. При ошибке — подсказка: строки-маркеры Markdown
(тройные обратные кавычки, «### FILE:») — след копирования кода из чата или бандла.
"""
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRS = ("egm", "tools")
FENCE = "`" * 3                    # не литералом: в этом файле маркера быть не должно
MARKS = (FENCE, "### FILE:")


def files(root=ROOT):
    """main.py и все *.py в egm/, tools/."""
    out = [root / "main.py"] if (root / "main.py").exists() else []
    for d in DIRS:
        out += sorted(p for p in (root / d).rglob("*.py") if "__pycache__" not in p.parts)
    return out


def check(path):
    """[«строка: ошибка»]: синтаксис; при ошибке — строки-маркеры Markdown как подсказка."""
    text = path.read_text(encoding="utf-8")
    try:
        compile(text, str(path), "exec")
        return []
    except SyntaxError as e:
        errs = [f"{e.lineno}: SyntaxError: {e.msg}"]
    errs += [f"{i}: разметка Markdown «{s.strip()[:20]}»"
             for i, s in enumerate(text.splitlines(), 1) if s.lstrip().startswith(MARKS)]
    return errs


def self_test():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "bad.py"
        p.write_text(f"def f(ws):\n    for w in enumerate(ws\n\n{FENCE}text\n):\n        pass\n",
                     encoding="utf-8")
        e = check(p)
        assert any("Markdown" in x for x in e) and any("SyntaxError" in x for x in e), e
        p.write_text(f"x = '{FENCE}'\n", encoding="utf-8")
        assert check(p) == [], check(p)
    bad = {}
    for f in files():
        e = check(f)
        if e:
            bad[f.relative_to(ROOT).as_posix()] = e
    assert not bad, "; ".join(f"{k}: {', '.join(v)}" for k, v in bad.items())
    return True
