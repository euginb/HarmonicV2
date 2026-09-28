# HarmonicV2

Проект **EG-MACHINES** — станки собственного изготовления на эпоксигранитных
станинах (SM-1 — фрезерный, SE-1 — электроэрозионная система ЭЭС; основная
компоновка HMC, вариант VMC считается параллельно для сравнения — Д-09),
оснастка и метрология к ним. Прикладная цель — ячейка мелкосерийного
производства волновых редукторов Ø≤110 мм: основная — ПТК (промежуточные тела
вращения), вспомогательная — с гибким колесом (ГК). Назначение — промышленное
станкостроение и робототехника. Приоритет: точность → дешевизна → скорость.

## Правила работы с репозиторием

1. **Code-first**: числа живут в коде и `specs/*.json`; `python main.py` пишет
   результат в `out/`, заказчик переносит файлы в `specs/`. Руками не правятся.
2. **Spec-first**: технология, методики, договорённости — правятся напрямую.
   Если число из spec-first попадает в расчёт, оно переносится в код/JSON,
   а документ ссылается на источник, не дублируя значение.
3. Данные производителей — только из `specs/*.json`, без хардкода в коде.
4. Решения — `Д-##` в DECISIONS.md, план кода — `CP-##` + `TODO(CP-##)` в коде.

## Правила взаимодействия с ИИ

1. ИИ не запускает код и не пишет в репозиторий: изменения — unified diff.
2. Каждый файл: `diff --git a/<путь> b/<путь>`; новый — `new file mode 100644`,
   `--- /dev/null`, один hunk `@@ -0,0 +1,N @@`, все строки с `+`.
3. Правки существующих файлов — только от текущего коммита; первая строка
   патча `# base: <sha>, CP-##`; контекст дословный, минимум не нормируется —
   `tools/fix_diff.py` добирает его до 3 строк по рабочему дереву (Д-13).
4. UTF-8 без BOM, LF, перевод строки в конце; `--recount` не используется.
5. Перед наложением: `python tools/fix_diff.py p.diff` → `git apply --check`.
6. В начале сессии ИИ читает README, DECISIONS, CODE_PLAN и нужные spec
   через GitHub REST API от последнего коммита (Д-12).

## Реестр спецификаций

| Файл | Тип | Источник | Состояние |
|---|---|---|---|
| [specs/DECISIONS.md](specs/DECISIONS.md) | журнал | — | ведётся |
| [archive/DECISIONS_ARCHIVE.md](archive/DECISIONS_ARCHIVE.md) | журнал | — | ведётся |
| [specs/CODE_PLAN.md](specs/CODE_PLAN.md) | план | доработка кода, `TODO(CP-##)` | итерация 0 |
| [specs/CANCELLED.md](specs/CANCELLED.md) | журнал | — | ведётся |
| [specs/SPEC-01_NAMING.md](specs/SPEC-01_NAMING.md) | spec-first | Д-02 | черновик |
| [specs/SPEC-02_PRECISION_EMBEDS.md](specs/SPEC-02_PRECISION_EMBEDS.md) | spec-first | Д-03, Д-04 | черновик |
| [specs/CATALOGS.md](specs/CATALOGS.md) | реестр | `docs/` | черновик |
| [specs/vendor_prices.json](specs/vendor_prices.json) | данные (заказчик) | поставщики | заполняется |
| [specs/SPEC-10_PTK_CALC.md](specs/SPEC-10_PTK_CALC.md) | code-first | `egm/ptk.py`, `templates/SPEC-10_PTK_CALC.md.tmpl` | rev 0 |
| [specs/ptk_configs.json](specs/ptk_configs.json) | code-first (данные) | `egm/ptk.py` | rev 0 |
| [specs/checks.md](specs/checks.md) | code-first (отчёт) | `main.py` | каждый прогон |
| specs/catalog_hiwin_hg.json | code-first (БД) | `egm/catalog.py` ← CAT-01 | после прогона CP-02 |
| specs/catalog_hiwin_hg_pairs.json | code-first (БД) | `egm/catalog.py`, Д-10 | после прогона CP-02 |
| specs/catalog_report.md | code-first (отчёт) | `egm/catalog.py` | после прогона CP-02 |

Описание: SPEC-01 — маркировка станков (варианты HMC/VMC) и ID узлов; SPEC-02 —
классы точности K1–K3, способы монтажа закладных M1–M4, правила раскроя;
CATALOGS — реестр каталогов производителей; vendor_prices — наличие и цена
(заполняет заказчик); SPEC-10 и ptk_configs — расчёт редуктора ПТК;
catalog_hiwin_hg — БД рельсов и кареток HIWIN HG; catalog_hiwin_hg_pairs —
совместимые пары с каталожными номерами (Д-10); catalog_report — итог разбора
каталога и проверок; checks — сводка проверок прогона.

## Запуск

`python main.py` → `out/`; код выхода 0 = все проверки пройдены.
После прогона все файлы из `out/` переносятся в `specs/`.
