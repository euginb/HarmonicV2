"""Макрос FreeCAD (Д-66, CP-56): один запуск — метаданные (Д-50) и чертежи TechDraw (Д-65).

Запуск: Макрос → Макросы… → tools/freecad_egm.py → Выполнить → выбрать <ID>.assy.json.
Нет активного документа или в нём нет узлов этой сборки — открывается <ID>.step рядом
с .assy.json (ImportGui: дерево и цвета как при ручном открытии).
Порядок: 1) tools/freecad_meta.py — свойства egm_*; 2) tools/freecad_techdraw.py — листы,
отчёт <ID>.techdraw.md, PDF. Модули перечитываются (reload): правки без перезапуска FreeCAD.
"""
import importlib
import json
import os
import re
import sys

import FreeCAD as App


def _tools(path):
    starts = []
    if "__file__" in globals():
        starts.append(os.path.dirname(os.path.abspath(__file__)))
    d = os.path.dirname(os.path.abspath(path))
    while True:
        starts.append(os.path.join(d, "tools"))
        up = os.path.dirname(d)
        if up == d:
            break
        d = up
    for t in starts:
        if all(os.path.exists(os.path.join(t, f)) for f in ("freecad_meta.py", "freecad_techdraw.py")):
            if t not in sys.path:
                sys.path.insert(0, t)
            return t
    raise ImportError("не найдены tools/freecad_meta.py, tools/freecad_techdraw.py выше " + path)


def _strip(label):
    return re.sub(r"(?<=\))\d+$", "", label)


def _doc(path):
    with open(path, encoding="utf-8") as f:
        labels = set(json.load(f).get("labels") or {})
    doc = App.ActiveDocument
    if doc is not None and any(_strip(o.Label) in labels for o in doc.Objects):
        return doc
    step = re.sub(r"\.assy\.json$", ".step", path)
    if not os.path.exists(step):
        raise FileNotFoundError(f"нет {step}: открыть STEP вручную или пересоздать "
                                "python -m egm.cad <ID> --assy")
    App.Console.PrintMessage(f"EGM: открывается {step}\n")
    if App.GuiUp:
        import ImportGui
        ImportGui.open(step)
    else:
        import Import
        Import.open(step)
    return App.ActiveDocument


def apply(path, pdf=True):
    _tools(path)
    import freecad_meta
    import freecad_techdraw
    meta = importlib.reload(freecad_meta)
    td = importlib.reload(freecad_techdraw)
    doc = _doc(path)
    n = meta.apply(path, doc)
    rep = td.apply(path, doc, pdf)
    ok = sum(1 for r in rep if not r[2].startswith(("пропущен", "ошибка")))
    App.Console.PrintMessage(f"EGM: метаданные — {n} объектов; чертежей — {ok} из {len(rep)}\n")
    return n, rep


def run():
    from PySide import QtGui
    App.Console.PrintMessage(f"EGM: старт (__name__ = {__name__}, FreeCAD "
                             f"{'.'.join(App.Version()[:3])}, Python {sys.version.split()[0]})\n")
    path = QtGui.QFileDialog.getOpenFileName(None, "EGM: <ID>.assy.json", "",
                                             "assy (*.assy.json)")[0]
    if not path:
        App.Console.PrintMessage("EGM: файл не выбран\n")
        return
    try:
        n, rep = apply(path)
    except Exception:
        import traceback
        msg = traceback.format_exc()
        App.Console.PrintError(msg + "\n")
        QtGui.QMessageBox.critical(None, "EGM — ошибка", msg)
        return
    import freecad_techdraw
    freecad_techdraw.box("EGM", f"Метаданные: {n} объектов.\n" + freecad_techdraw.summary(path, rep))


if __name__ != "freecad_egm":              # макрос FreeCAD (Д-66)
    args = [a for a in sys.argv[1:] if a.endswith(".assy.json")]
    if args:
        apply(args[0], pdf=App.GuiUp)
    elif App.GuiUp:
        run()
