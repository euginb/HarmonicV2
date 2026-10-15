"""Экспорт 3D-модели во FreeCAD (.FCStd) — альтернативный формат (Д-64, rev 9.4).

Геометрия та же, что у STEP (egm/cad/step.py, Д-30, Д-32): FreeCAD сам её не
строит. Деталь/сборка экспортируются в STEP (CadQuery), головной FreeCAD
(команда из configs/application.yaml → cad.export.freecad.command) импортирует
его скриптом-конвертером и сохраняет документ .FCStd рядом. Зависимости:
CadQuery — для геометрии; FreeCAD (freecadcmd / FreeCADCmd) — только для
конвертации. Команда не найдена — FileNotFoundError («freecad: пропущен»,
прогон не падает); ошибка конвертации — ValueError с выводом FreeCAD.
"""
import os
import shutil
import subprocess
import time
from pathlib import Path

from egm.cad import step  # noqa: F401  (геометрия — общая с STEP, Д-32)

FORMAT = "FCStd"
DEFAULT_COMMAND = "FreeCADCmd"

# Скрипт-конвертер: выполняется головным FreeCAD (freecadcmd). Вход/выход — через
# переменные окружения EGM_STEP / EGM_FCSTD (argv у FreeCADCmd зависит от версии).
# Структура — Import.insert (дерево изделия); без него — одна Part::Feature.
_SCRIPT = """\
# EGM: STEP -> FreeCAD (.FCStd), головной режим (Д-64). Запускается FreeCADCmd:
# вход и выход — переменные окружения EGM_STEP / EGM_FCSTD (argv зависит от версии).
import os
import sys
import traceback

import FreeCAD as App


def main():
    step_path = os.environ.get("EGM_STEP") or (sys.argv[1] if len(sys.argv) > 1 else "")
    fcstd_path = os.environ.get("EGM_FCSTD") or (sys.argv[2] if len(sys.argv) > 2 else "")
    if not step_path or not fcstd_path:
        print("EGM: переменные окружения EGM_STEP / EGM_FCSTD не заданы", file=sys.stderr)
        return 2
    name = os.path.splitext(os.path.basename(fcstd_path))[0]
    doc = App.newDocument(name)
    try:
        try:
            import Import
            Import.insert(step_path, doc)
        except Exception:
            import Part
            doc.addObject("Part::Feature", name).Shape = Part.read(step_path)
        doc.recompute()
        doc.saveAs(fcstd_path)
        App.Console.PrintMessage("EGM: %s -> %s\\n" % (step_path, fcstd_path))
        return 0
    except Exception:
        traceback.print_exc()
        return 1


sys.exit(main())
"""


def _write_script(out_dir):
    """Скрипт-конвертер рядом с выводом (out/ в git не хранится); возвращает путь."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / "freecad_convert.py"
    p.write_text(_SCRIPT, encoding="utf-8", newline="\n")
    return p


def _resolve(command=None):
    """Исполняемый файл FreeCAD: command из application.yaml (по умолчанию
    FreeCADCmd) -> путь через PATH; не найден — FileNotFoundError (Д-64)."""
    cmd = (command or DEFAULT_COMMAND).strip().strip('"')
    found = shutil.which(cmd)
    if found is None:
        raise FileNotFoundError(f"FreeCAD не найден: {cmd!r} — установите FreeCAD или "
                                "укажите команду в configs/application.yaml → "
                                "cad.export.freecad.command (Д-64)")
    return found


def export(step_file, fcstd_path, command=None):
    """STEP -> .FCStd: головной FreeCAD (command, Д-64) импортирует STEP скриптом-
    конвертером и сохраняет документ. Возвращает время конвертации, с.
    Команда не найдена — FileNotFoundError; ошибка конвертации — ValueError."""
    cmd = _resolve(command)
    script = _write_script(Path(fcstd_path).parent)
    env = {**os.environ, "EGM_STEP": str(Path(step_file).resolve()),
           "EGM_FCSTD": str(Path(fcstd_path).resolve())}
    t0 = time.perf_counter()
    try:
        p = subprocess.run([cmd, str(script.resolve())], env=env, capture_output=True,
                           text=True, timeout=600)
    except subprocess.TimeoutExpired as e:
        raise ValueError(f"FreeCAD не ответил за {e.timeout} с") from e
    dt = time.perf_counter() - t0
    if p.returncode != 0 or not Path(fcstd_path).exists():
        tail = (p.stderr or p.stdout or "").strip()[-400:]
        raise ValueError(f"FreeCAD (код {p.returncode}): {tail or 'нет вывода'}")
    return dt


def self_test():
    """FreeCAD в прогоне не нужен: скрипт-конвертер компилируется, формат и команда
    по умолчанию заданы. Сам конвертация проверяется на машине с FreeCAD."""
    compile(_SCRIPT, "freecad_convert.py", "exec")
    assert FORMAT == "FCStd" and DEFAULT_COMMAND == "FreeCADCmd"
    return True
