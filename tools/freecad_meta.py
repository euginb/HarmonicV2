"""Макрос FreeCAD (Д-50): метаданные из <ID>.assy.json -> свойства объектов, группа «EGM».

FreeCAD атрибуты STEP (PROPERTY_DEFINITION) в панели свойств не показывает; макрос
находит объекты по меткам-алиасам (labels в .assy.json) и добавляет свойства egm_*.
Запуск: открыть <ID>.step; Макрос → Макросы… → этот файл → Выполнить → выбрать <ID>.assy.json.
Дубли FreeCAD получают суффикс 001, 002… — он отбрасывается при поиске.
"""
import json
import re

import FreeCAD as App


def apply(path, doc=None):
    doc = doc or App.ActiveDocument
    with open(path, encoding="utf-8") as f:
        labels = json.load(f)["labels"]
    n = 0
    for o in doc.Objects:
        meta = labels.get(o.Label) or labels.get(re.sub(r"\d{3}$", "", o.Label))
        if not meta:
            continue
        for k, v in meta.items():
            prop = "egm_" + re.sub(r"\W", "_", k, flags=re.ASCII)
            if prop not in o.PropertiesList:
                o.addProperty("App::PropertyString", prop, "EGM", k)
            setattr(o, prop, "" if v is None else str(v))
        n += 1
    App.Console.PrintMessage(f"EGM: свойства записаны в {n} объектов из {path}\n")
    return n


def run():
    from PySide import QtGui
    path = QtGui.QFileDialog.getOpenFileName(None, "EGM: <ID>.assy.json", "",
                                             "assy (*.assy.json)")[0]
    if path:
        apply(path)


if __name__ == "__main__":
    run()
