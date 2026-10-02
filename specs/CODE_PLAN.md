# CODE_PLAN — план доработки кода (rev 0)

Тип: **план**. Решение о порядке работ — Д-01. Каждый пункт `CP-##` продублирован
в коде комментарием `TODO(CP-##)` в месте, которое он затрагивает. Пункт
закрывается только после прогона `main.py` заказчиком (код выхода 0, отчёт
проверок, перегенерированные `specs/`) — до этого изменение считается
непроверенным.

## 1. Порядок работы (Д-01)

Исполнитель готовит патч (`tools/fix_diff.py` → `git apply`, Д-13) на один или
несколько пунктов CP. Заказчик накладывает патч, запускает `python main.py`,
докладывает: код выхода, список непрошедших проверок, массы машин, замечания
по моделям. Следующий патч строится от доложенного состояния. Спецификации
code-first перегенерируются только прогоном.

## 2. Пункты плана

| CP | Содержание | Файлы | Основание | Зависит от | Статус           |
|---|---|---|---|---|------------------|
| CP-01 | Каркас `main.py`, пакет `egm`, калькулятор ПТК ур.1, шаблон SPEC-10 | main.py, egm/, templates/ | Д-08 | — | закрыт (прогон OK, 4eb0bbe) |
| CP-02 | Парсер `docs/HG-Series-Catalog_opt.md` → `catalog_hiwin_hg.json`, пары с каталожными номерами, проверка совместимости, раскладка отверстий рельса, сверка `vendor_prices.json` | egm/catalog.py, main.py | Д-07, Д-10 | CP-01 | закрыт (прогон OK, 0291bd6) |
| CP-03 | Расчёт стоимости по `vendor_prices.json`, отчёт о несовместимостях | egm/cost.py | Д-07 | CP-02 | открыт           |
| CP-04 | БД узлов (дерево машин JSON), спецификации по `naming.MACHINES`: SM-1-HMC, SE-1-HMC (основные), SM-1-VMC, SE-1-VMC (сравнение); 10 разделов; сравнительная таблица HMC/VMC | egm/machine.py, specs/machines/<код>.md/.json | Д-02, Д-09 | CP-02, CP-12 | открыт           |
| CP-05 | Компоновка правилами (attach/center/offset), примитивы CadQuery → STEP, каталог примитивов | egm/cad/ | Д-07 | CP-04 | открыт           |
| CP-06 | 2D SVG-проекции с размерами | egm/cad/svg.py | — | CP-05 | открыт           |
| CP-07 | Закладные: раскрой по листам, унификация, сегменты 10 мм | egm/embeds.py | Д-04 | CP-04 | открыт           |
| CP-08 | ПТК ур.2: момент по контакту Герца, 4-рядная фазировка, JSON конфигураций | egm/ptk.py | Д-08 | CP-01 | частично: профиль и e max — CP-25; контакт Герца и момент — открыт |
| CP-09 | Калькулятор ГК, материалы редукторов, перечень материалов моделей | egm/hd.py, specs/ | — | CP-08 | открыт           |
| CP-10 | Spec-first: технология ЭЭС+ЭХП, литьё, метрология, маршруты, спецификация ПО | specs/ | Д-05, Д-06 | — | открыт           |
| CP-11 | ПТК: u > 100 не считается, рекомендация двухступенчатой схемы; для нереализуемых по Ø — максимальный Ø тела | egm/ptk.py, main.py, templates/ | Д-11 | CP-01 | закрыт (прогон OK, 0291bd6) |
| CP-12 | `egm/naming.py`: разбор кода станка с компоновкой, варианты HMC/VMC, имена файлов, ID узлов | egm/naming.py | Д-02, Д-09 | — | закрыт (прогон OK, 0291bd6) |
| CP-13 | Выход прогона `out/specs/` и `out/reports/`, ключ `--publish` | main.py | Д-14 | — | закрыт (прогон OK, dbcf67c) |
| CP-14 | ПТК: отверстия венца (крепёжные = технологические), момент удержания, параметры в `specs/ptk_input.json`, входные параметры и расшифровка колонок в SPEC-10 | egm/ptk.py, main.py, templates/, specs/ptk_input.json | Д-16, Д-18 | CP-11 | закрыт (прогон OK, dbcf67c) |
| CP-15 | Инструкции INS-00, INS-10, INS-20 | instructions/ | Д-17 | — | закрыт (прогон OK, dbcf67c) |
| CP-16 | ПТК: фазировка рядов через сдвиг сверловки венцов, число вариантов венца, смещение гнёзд сепаратора; снята кратность 4 | egm/ptk.py, main.py, templates/, specs/ptk_input.json, instructions/INS-10 | Д-19 | CP-14 | закрыт (прогон OK) |
| CP-17 | Детерминированный сбор контекста (bundle) по ключам, фиксированный пол чтения, pinned base, зеркало в AI Drive и порядок синхронизации, выдача патчей файлами; область действия — инфраструктура Genspark (AI Drive) | tools/context_bundle.py, README.md, specs/DECISIONS.md | Д-20 | — | закрыт (прогон OK, 369a808) |
| CP-18 | AUDIT_BUNDLE: регистрация скрипта формирования, инструкции INS-90 (применение — только при одновременной недоступности GitHub и AI Drive) и места результатов review | tools/make_audit_bundle.py, instructions/INS-90_AUDIT_BUNDLE.md, specs/DECISIONS.md, review_reports/ | Д-21 | — | закрыт (прогон OK, c563a6a) |
| CP-19 | ПТК: ID исполнения конфигураций, снимок `geom`, детали-венцы `.01<вар>`, `ptk.find()`, проверка дубликатов; колонка ID в SPEC-10 | egm/ptk.py, main.py, templates/, instructions/INS-10, specs/SPEC-01 | Д-22 | CP-16 | закрыт (прогон OK, 39b6569, REV6) |
| CP-20 | Реестр изделий и номенклатура (products.json, SPEC-03), генератор 3D/2D по ID: венец .01 (STEP, SVG с размерами); далее .02/.03/.05 | egm/products.py, egm/cad/, main.py, specs/products.json | Д-24 | CP-19 | закрыт (прогон OK, 4dc721fb, REV6) |
| CP-21 | Документация процесса: реестр инструкций и режимы работы с ИИ в `instructions/README.md`, INS-90 — ручная подготовка контекста (`context_bundle.py` с правилами ключей, `make_audit_bundle.py`), главный README — только проект, структура, GitHub/коммиты/патчи; `CONTEXT_BUNDLE.md` в `.gitignore` | instructions/README.md, instructions/INS-90_AUDIT_BUNDLE.md, README.md, .gitignore, specs/DECISIONS.md, specs/CANCELLED.md | Д-25, Д-26 | CP-18 | закрыт (прогон OK, d80b2d9c, REV7) |
| CP-22 | `make_audit_bundle.py`: исключения правилами `.gitignore` (`SKIP_FILES` — база), профили `--reports/--ins/--data/--tools/--workflow/--min`, `--exclude`, `--out`, `--list`; без ключей — прежний полный снимок; INS-90 §3 | tools/make_audit_bundle.py, instructions/INS-90_AUDIT_BUNDLE.md, instructions/README.md, specs/DECISIONS.md | Д-27 | CP-18, CP-21 | закрыт (прогон OK, f942e76b) |
| CP-23 | Документация: таблица признаков перехода в `instructions/README.md` в главном README; `review_reports/` — локальная папка результатов review, в git не хранится | README.md, instructions/README.md, instructions/INS-90_AUDIT_BUNDLE.md, specs/DECISIONS.md | Д-28, Д-29 | CP-21 | закрыт (прогон OK, f942e76b) |
| CP-24 | Генератор чертежей: контур венца `profile` из дуг, общий для STEP и SVG (`<path>`); self_test CAD в прогоне; макс. Ø тела в ошибке Øнар; INS-30 | egm/cad/, egm/ptk.py, main.py, instructions/, README.md, specs/SPEC-03, specs/DECISIONS.md | Д-24, Д-30 | CP-20 | закрыт (прогон OK, 35cfc881) |
| CP-25 | rev 7.1: z = u + 1, точный профиль венца и e max (`egm/ptk_profile.py`), раздел профиля в SPEC-10; набор креплений `ring_mounts`; CAD — `PartModel` + рендеры SVG/STEP, легенда SPEC-10, `--phase/--row` | egm/ptk.py, egm/ptk_profile.py, egm/cad/, main.py, templates/, specs/ptk_input.json, specs/DECISIONS.md, specs/CANCELLED.md, instructions/INS-30_CAD.md | Д-31, Д-32, Д-33 | CP-24 | открыт |


