# HarmonicV2

Проект **EG-MACHINES** — станки собственного изготовления на эпоксигранитных
станинах (SM-1 — фрезерный, SE-1 — электроэрозионная система ЭЭС; основная
компоновка HMC, вариант VMC считается параллельно для сравнения — Д-09),
оснастка и метрология к ним. Прикладная цель — ячейка мелкосерийного
производства волновых редукторов Ø≤110 мм: основная — ПТК (промежуточные тела
вращения), вспомогательная — с гибким колесом (ГК). Назначение — промышленное
станкостроение и робототехника. Приоритет: точность → дешевизна → скорость.

## Структура репозитория

| Папка | Содержимое | Кто пишет |
|---|---|---|
| `specs/` | спецификации (spec-first и code-first), БД JSON, входные параметры `*_input.json` | заказчик; code-first — перенос из `out/specs/` |
| `reports/` | отчёты прогона: сводка проверок, разбор каталогов | перенос из `out/reports/` (Д-14) |
| `instructions/` | инструкции к code-first спецификациям: входные файлы, параметры, обозначения (Д-17) | правятся напрямую |
| `templates/` | шаблоны code-first спецификаций | код |
| `egm/` | пакет расчётов на Python | код |
| `docs/` | каталоги производителей, справочные материалы | заказчик |
| `archive/` | архив решений | журнал |
| `tools/` | служебные утилиты (`fix_diff.py`) | — |
| `out/` | выход прогона, в git не хранится | `main.py` |

## Правила работы с репозиторием

1. **Code-first**: числа живут в коде и `specs/*.json`; `python main.py` пишет
   спецификации в `out/specs/`, отчёты в `out/reports/`; они переносятся в
   `specs/` и `reports/` вручную или ключом `--publish` (Д-14). Руками не правятся.
2. **Spec-first**: технология, методики, договорённости — правятся напрямую.
   Если число из spec-first попадает в расчёт, оно переносится в код/JSON,
   а документ ссылается на источник, не дублируя значение.
3. Данные производителей — только из `specs/*.json`, без хардкода в коде.
4. Входные параметры расчётов — `specs/*_input.json` (Д-18), их смысл — в `instructions/`.
5. Решения — `Д-##` в DECISIONS.md, план кода — `CP-##` + `TODO(CP-##)` в коде.

## Правила взаимодействия с ИИ

1. ИИ не запускает код и не пишет в репозиторий: изменения — unified diff.
2. Каждый файл: `diff --git a/<путь> b/<путь>`; новый — `new file mode 100644`,
   `--- /dev/null`, один hunk `@@ -0,0 +1,N @@`, все строки с `+`.
3. Правки существующих файлов — только от текущего коммита; первая строка
   патча `# base: <sha>, CP-##`; контекст дословный, минимум не нормируется —
   `tools/fix_diff.py` добирает его до 3 строк по рабочему дереву (Д-13).
4. UTF-8 без BOM, LF, перевод строки в конце; `--recount` не используется.
5. Перед наложением: `python tools/fix_diff.py p.diff` → `git apply --check`.
6. В начале сессии ИИ читает README, DECISIONS, CODE_PLAN, `reports/` и нужные
   spec от последнего коммита способами Д-12, Д-15.
7. Контекст задачи собирается детерминированно (Д-20): зеркало в AI Drive,
   `python tools/context_bundle.py --sha <base> <ключи и пути>`; задача
   открывается указанием базового sha; патч — файлом в AI Drive
   (`/HarmonicV2-patches/`). Механизм действует в инфраструктуре Genspark
   при подключённом AI Drive; вне её — способы Д-12, Д-15 (резервный
   путь): зеркало, синхронизация и канал патчей — функции AI Drive.

## Реестр спецификаций

| Файл | Тип | Источник | Состояние |
|---|---|---|---|
| [specs/DECISIONS.md](specs/DECISIONS.md) | журнал | — | ведётся |
| [archive/DECISIONS_ARCHIVE.md](archive/DECISIONS_ARCHIVE.md) | журнал | — | ведётся |
| [specs/CODE_PLAN.md](specs/CODE_PLAN.md) | план | доработка кода, `TODO(CP-##)` | ведётся |
| [specs/CANCELLED.md](specs/CANCELLED.md) | журнал | — | ведётся |
| [specs/SPEC-01_NAMING.md](specs/SPEC-01_NAMING.md) | spec-first | Д-02 | черновик |
| [specs/SPEC-02_PRECISION_EMBEDS.md](specs/SPEC-02_PRECISION_EMBEDS.md) | spec-first | Д-03, Д-04 | черновик |
| [specs/CATALOGS.md](specs/CATALOGS.md) | реестр | `docs/` | черновик |
| [specs/vendor_prices.json](specs/vendor_prices.json) | данные (заказчик) | поставщики | заполняется |
| [specs/ptk_input.json](specs/ptk_input.json) | данные (параметры) | заказчик, INS-10 | rev 1 |
| [specs/SPEC-10_PTK_CALC.md](specs/SPEC-10_PTK_CALC.md) | code-first | `egm/ptk.py`, `templates/SPEC-10_PTK_CALC.md.tmpl`, INS-10 | rev 1 |
| [specs/ptk_configs.json](specs/ptk_configs.json) | code-first (данные) | `egm/ptk.py` | rev 1 |
| [specs/catalog_hiwin_hg.json](specs/catalog_hiwin_hg.json) | code-first (БД) | `egm/catalog.py` ← CAT-01, INS-20 | rev 1 |
| [specs/catalog_hiwin_hg_pairs.json](specs/catalog_hiwin_hg_pairs.json) | code-first (БД) | `egm/catalog.py`, Д-10, INS-20 | rev 1 |
| [reports/checks.md](reports/checks.md) | отчёт | `main.py` | каждый прогон |
| [reports/catalog_report.md](reports/catalog_report.md) | отчёт | `egm/catalog.py` | каждый прогон |
| [instructions/README.md](instructions/README.md) | инструкция | INS-00 | rev 1 |
| [instructions/INS-10_PTK_CALC.md](instructions/INS-10_PTK_CALC.md) | инструкция | к SPEC-10 | rev 1 |
| [instructions/INS-20_CATALOG.md](instructions/INS-20_CATALOG.md) | инструкция | к catalog_* | rev 1 |

## Описание спецификаций

| Файл | Что содержит | Как пользоваться |
|---|---|---|
| DECISIONS | принятые решения `Д-##` и открытые вопросы `OQ-##` | первоисточник договорённостей; решения не переписываются, а дополняются или отменяются |
| DECISIONS_ARCHIVE | решения, утратившие актуальность | справочно |
| CODE_PLAN | пункты доработки кода `CP-##`, их статус и основание | пункт закрывается только после прогона `main.py` |
| CANCELLED | отменённые положения `X-##` и чем они заменены | чтобы отменённое не вернулось молча |
| SPEC-01_NAMING | маркировка станков `S<тип>-<№>-<компоновка>` и ID узлов | при именовании станков, узлов, файлов |
| SPEC-02_PRECISION_EMBEDS | классы точности K1–K3, способы монтажа закладных M1–M4, правила раскроя | при проектировании закладных и литья |
| CATALOGS | реестр каталогов производителей CAT-## | при добавлении нового каталога |
| vendor_prices.json | наличие, цена, сроки покупных позиций; тела качения ПТК (`bodies`) | заполняет заказчик (INS-20) |
| ptk_input.json | входные параметры калькулятора ПТК: ограничения, отверстия венца, крепёж | правит заказчик (INS-10) |
| SPEC-10_PTK_CALC | расчёт редуктора ПТК по диапазону u и телам качения, с расшифровкой колонок | результат прогона; параметры — в ptk_input.json |
| ptk_configs.json | те же результаты SPEC-10 в машиночитаемом виде | вход для следующих расчётов |
| catalog_hiwin_hg.json | БД кареток, рельсов, типоразмеров HIWIN HG из CAT-01 | вход для расчётов станков |
| catalog_hiwin_hg_pairs.json | совместимые пары рельс+каретка с нашими каталожными номерами EGC | номер пары используется в спецификациях станков (INS-20) |
| reports/checks.md | сводка проверок прогона | «все пройдены» = код выхода 0 |
| reports/catalog_report.md | итог разбора каталога, ошибки, нераспознанные таблицы | после изменения каталога или парсера |

## Запуск

`python main.py` → `out/specs/`, `out/reports/`; код выхода 0 = все проверки пройдены.
`python main.py --publish` — то же и копирование: `out/reports/` → `reports/`
всегда, `out/specs/` → `specs/` только при коде выхода 0.
