# CTX-T — CP-91, этапы 4 и 6: CAD входного вала `.15` и проработка K20 (rev13.4)

**base:** `2904cd1118669338567a1056ebd893089c670cc9` · **ref:** `rev13.4` · **режим:** CTX-T (задача, INS-91B §4)
**Сформирован:** 2026-11-12 · **источник решений:** Д-107…Д-110, Д-112 (OQ-36 закрыт), CP-91; rev13.3 влита в `main` (PR #27)

---

## 6. Инструкции для модели — дословный блок (копируется в CTX)

Ниже — точный блок, который включается в каждый CTX-файл:

Результат работы — два файла, каждый отдельным код-блоком:
1. p.diff — unified diff; первая строка: `# base: <sha>, CP-##` (sha — из
   строки «base» заголовка этого файла). Правила: пути a/… и b/…; строки
   контекста — полные и точно из этого файла; номера строк — ориентир,
   hunk ищется по содержимому (tools/fix_diff.py поправит синтаксис);
   новые файлы — заголовком diff --git, new file mode 100644,
   --- /dev/null, +++ b/<путь>; не-ASCII имена файлов — сырым UTF-8,
   без экранирования; markdown-обрамление вокруг diff не используется.
2. upd.md — для строк таблиц и новых файлов. Директива Journal: путь в
   одинарных кавычках, после двоеточия — заголовок раздела с таблицей
   (как в файле); ниже — строки таблицы; ключ — значение первой ячейки:
   есть в таблице — строка заменяется целиком, нет — добавляется в
   конец. Директива NewFile: путь в кавычках; ниже — содержимое файла
   до следующей директивы или конца. Строка содержимого, начинающаяся
   с решётки и трёх дефисов, непредставима — такие строки правимого
   файла давайте через diff.
3. Файл, нужный для задачи, но отсутствующий в контексте, называется
   явно: «Отсутствует: <путь>» — его досылают отдельно; по памяти не
   угадывать.
4. Положение относительно исходного файла: CTX-файл несёт заголовки
   `===== FILE: <путь> (строки 1–N) =====` (диапазоны — в заголовках);
   правка Journal привязывается к заголовку раздела, а не к номеру
   строки.

---

## Что изменилось после прошлого контекста (rev13.3 → rev13.4)

Прошлый патч (p.diff + p2.diff) наложен и влит в `main` через PR #27; ветка `rev13.4`
ответвлена от merge-коммита `2904cd1` — это база для нового патча. Полный прогон:
`--self-test` OK, `design --publish` rc=0.

1. **Принято целиком**: `egm/shafts.py`, `egm/shaft_doc.py` + шаблон, `INS-40`, вход по
   ID, поля `shaft.grade/state/props/tau_basis/crush_basis/blank/bore_max/rejected`.
2. **Правка сверх патча — `products.check_app`**: продукт с заданным `source` и пустыми
   `parts` теперь допустим (иначе self_test падал на `SH`). Учтено в rev13.3.
3. **Свойства марок в патче были предварительными** — заменены проверенными (Д-112):
   * 40Х: было 785/640 (перепутано: 785 — σ0,2, 640 — σв поковки КП 640) →
     **980 / 785 / 509** (ГОСТ 4543, пруток Ø25, закалка 860 °C масло + отпуск 500 °C);
   * 45: 600 / 355 / **290** (ГОСТ 1050-2013, нормализация), `d_range [0, 80]`;
   * ШХ15 — 2160 / 1670 / 652 (ГОСТ 801-78, закалка 810 + отпуск 150, сечение 30…60);
   * 40ХН2МА — 1080 / 930 / 519 (ГОСТ 4543, пруток Ø25, 850 + 620);
   * 38Х2МЮА — 980 / 835 / 392 (пруток Ø30, 940 + 640; σ₋₁ — нижняя граница 392…480);
   * 30ХГСА — 1080 / 830 / 470 (пруток Ø25, 880 + 540);
   * **38Х2Н2МА — 1080 / 930 / 363** (ГОСТ 4543, пруток: 870 °C масло + 580 °C;
     поковки КП 785 — 930 / 785; σ₋₁ 363 при n = 5·10⁶ для улучшенного состояния).
   Оценка `σ₋₁ ≈ 0.43·σв` **не применяется ни к одной марке** номенклатуры; в коде она
   остаётся только как fallback для марок без `sigma_m1`.
4. **Инцидент с YAML** (учтён, коммит `c29d6db`): вставка `sigma_*` после строки
   `use: "…"` без явного перевода строки слиплась с ней — файл перестал парситься.
   Правило для патча: вставка блока в YAML — только с завершающим `
` в конце
   предыдущей строки-якоря; после любой правки `specs/*.yaml` — контрольный
   `python3 -c "yaml.safe_load(...)"` и `--self-test`.
5. **`allow()` округляет** `tau_allow` / `sigma_crush` до 0.1 МПа — ожидания в
   `self_test` и в отчёте сверять с округлёнными значениями.
6. **Допуски при DEFAULTS (rev13.4)**: [τ] ШХ15 67.5, 40ХН2МА 53.8, 40Х 52.7,
   30ХГСА 48.7, 38Х2МЮА 40.6, 38Х2Н2МА 37.6, 45 30.0 МПа; [σсм] 101.4 — везде
   лимитирует шпонка (сталь 45). Усталость — определяющий критерий у всех марок.
7. **Прогон rev13.4 (штатно, без переопределений)**: K8 — τ 373.0, [τ] 52.7 (40Х,
   усталость), `d_req` 14.26, σсм 327.1, [σсм] 101.4 (шпонка), пруток Ø10,
   `SH-08-KEY`, статус «нет»; K10 — τ 212.7, `d_req` 14.86, σсм 191.9, пруток Ø12,
   `SH-10-KEY`, «нет». Регресс с переопределениями 25/100 — 373.0 / 327.1 / 17.94 и
   212.7 / 191.9 / 18.54, совпадает с rev13.2.


## Задача: этапы 4 и 6 CP-91 (Д-107…Д-112)

Этапы 1–3 и 5 закрыты в rev13.3 (номенклатура, `egm/shafts.py`, допуски из материала,
SPEC-12, инструкции). Открыты два:

### Этап 4 — генератор входного вала `.15` (главное)

`egm/cad/ptk_shaft.py`, по образцу `egm/cad/ptk_hub.py`. На входе — разрешённый словарь
`shaft` из `egm/shafts.resolve()` + `d["input"]` проработки, на выходе — тело детали
для сборки, в `egm/cad/assy.py` REF-примитив `.15` заменяется на неё.

Требования:

1. **Геометрия по конфигурации**: посадочные шейки под `.03` (эксцентрик) и `.10`
   (ступица) — диаметры и допуски из `output` проработки; хвостовик с пазом по
   `keys.table` (`b`, `h`, `t1`) для `link: key`; полый вал (`bore > 0`) — сквозное
   отверстие `bore`, стенка не меньше `DEFAULTS.wall_min`.
2. **Длина — по пакету**, а не из номенклатуры: B пакета + посадки `.03`/`.10` +
   выход под шпонку (в `shafts.yaml` `length` допускается `null`).
3. **Никаких чисел в коде** — диаметры/длины берутся из результата расчёта; константы
   (припуски, фаски, галтели) — в `DEFAULTS` `egm/shafts.py` с пометкой «сверить».
4. **Отказ — раньше геометрии**: если `resolve()` вернул `ok=False` или вал не
   подобран (`shaft.selection` пуст), CAD-вызов падает с понятной ошибкой, а не строит
   по первому ID.
5. **Обновить assy.py**: `.15` — реальная деталь в сборке, REF-примитив убрать;
   позиции/имена по `ptk_parts`. Проверить, что существующая сборка (REF-прогон
   заказчика) не меняет габаритов, кроме `.15`.
6. **SPEC-12 §6 (производные для `.03`/`.10`)** — источник размеров шеек для CAD;
   если генератору нужны новые поля, они добавляются в `shaft_doc.py`, а не в шаблон
   руками (Д-79).

### Этап 6 — проработка K20 на Ø20

`SH-20-KEY` в номенклатуре есть. Нужно: `designs[]` в `specs/ptk_design_input.yaml`
для PTK-063 (rev13.1) с `shaft: {id: SH-20-KEY}`, прогон, проверки τ/σсм/стенки,
отражение в SPEC-12 §3 (применимость) и в `reports/checks.md`. Новая конфигурация
вала — только если `SH-20-KEY` не проходит по `d_req`/пазу; тогда запись в
`specs/shafts.yaml` + строка в реестре §2 (генерация, не руками).

### Приёмка

- `python3 main.py --self-test` → OK (все self_test, включая `shafts` и `design_doc`
  на покрытие GLOSSARY).
- `python3 main.py design --publish` → rc=0; числа K8/K10 в `ptk_designs.yaml` не
  изменились (K8 373.0 / 14.26 / 327.1, K10 212.7 / 14.86 / 191.9).
- Регресс с переопределениями 25/100: 17.94 и 18.54 — как в rev13.2.
- CAD: сборка строится, `.15` присутствует как деталь, STEP пишется.
- Каждый новый ключ в машинном YAML — с комментарием в `GLOSSARY` (`egm/design_doc.py`).


## Целевой формат входов и выходов

### specs/ptk_design_input.yaml (после CP-91)

```yaml
# keys нет (Д-109): таблица шпонок — specs/shafts.yaml → keys.table, одна на вход и выход
designs:
  - id: PTK-063-R3X8-22M6P2
    bearing: "61819"
    name: K8
    eta: 0.8
    ecc_share: 0.5
    key_angle: 45.0
    shaft: {id: SH-08-KEY}          # Д-107: ссылка; список ID — наименьшая проходящая (Д-110)
    balance: {n_max: 3, wall: 1.0, drills: [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]}
    lighten: none
    output: {link: flange, d: 0.0, tau_allow: 25.0, sigma_crush: 130.0}
    layout: [L4, L3, L2]
```

Переопределения допусков (только для проверки (а) и для частных случаев):

```yaml
    shaft: {id: SH-08-KEY, tau_allow: 25.0, sigma_crush: 100.0}   # обоснование — в note записи
```

Обратная совместимость: `shaft:` без `id` (полный блок) — принимается, в `warnings`
добавляется «designs.<name>.shaft: полный блок устарел (Д-107) — заменить на {id: SH-…}».

### specs/shafts.yaml (после CP-91)

```yaml
keys: {table: [...]}          # Д-109 — остаётся
shafts:
  SH-08-KEY:
    name: "Вал входной Ø8, соединение шпонкой"
    d: 8.0
    bore: 0.0
    link: key
    applies_to: [PTK]
    note: "..."
    # tau_allow / sigma_crush / wall_min / length — уходят (Д-110)
```

### Результат: ptk_designs.yaml → shaft

Добавляются: `grade` (марка), `state` (термообработка), `props` (источник свойств:
`materials.yaml` | оценка), `tau_allow` + `tau_basis` (`fatigue` | `static`),
`sigma_crush` + `crush_basis` (`shaft` | `ecc` | `key`), `blank` (пруток/Ø),
`bore_max`, `rejected` (марки, отказ, причина). Плюс `input.shaft_id` — выбранный ID
(пусто, если вал задан блоком). Комментарий к КАЖДОМУ новому ключу — в
`egm/design_doc.py → GLOSSARY` (Д-105/Д-106), иначе self_test `design_doc` падает.

### Состав SPEC-12_SHAFTS.md

1. **Шпонки** — `keys.table` (d_max, b, h, t1, t2; DIN 6885 / ГОСТ 23360), Д-109.
2. **Реестр конфигураций** — ID, наименование, d, bore, link, примечание.
3. **Применимость** — продукт, проработки (K8/K10/K20), исполнения ПТК.
4. **Проверки** — τ против [τ], `d_req`, шпонка (b×h, σсм), стенка полого вала, стенки
   эксцентрика; по каждому допуску — определяющий критерий (усталость/статика,
   какая деталь лимитирует).
5. **Материал и заготовка** — выбранная марка и состояние, источник свойств, пруток,
   отказы остальных марок с причинами, `bore_max`.
6. **Производные** — шпонка по конфигурации, присоединительные размеры `.03`/`.10`.
7. **Ссылки** — `specs/shafts.yaml`, `specs/materials.yaml`, `ptk_designs.yaml`, INS-40.


## Ограничения и требования к патчу

1. **Приёмка CP-91 — две проверки** (Д-110):
   - **(а) регресс рефакторинга.** Во временном входе `shaft: {id: SH-08-KEY,
     tau_allow: 25.0, sigma_crush: 100.0}` (то же для K10) — числа в `ptk_designs.yaml`
     должны совпасть с rev13.3 (K8: τ 373.0, σсм 327.1, d_req 17.94; K10: τ 212.7,
     σсм 191.9, d_req 18.54). Это доказывает, что перенос в `egm/shafts.py` ничего не сломал.
   - **(б) расчёт из материала.** Штатный прогон — допуски из свойств марок; статусы
     K8/K10 остаются «нет» (τ на порядок выше [τ]); каждое изменение чисел объяснено
     в SPEC-12 (допуск → определяющий критерий → марка).
2. **Один источник истины.** Параметры вала — только `specs/shafts.yaml`; в
   `ptk_design_input.yaml` — только ID (+переопределения с обоснованием). Таблица
   шпонок — тоже там (Д-109), ключ `keys` во входе — `ValueError`. Умолчания — только
   `DEFAULTS` в `egm/shafts.py` (он же документация умолчаний).
3. **Порядок марок не менять**: `PTK.parts.15.material = [40Х]` (45 — резерв, прутков
   нет в `stock.yaml`). Сортировка/перестановка «по удобству» — отдельное решение.
4. **Отсутствующие свойства — не ошибка**: нет `sigma_m1` — оценка 0.43·σв (в
   результате пометить как оценку); нет марки в `materials.yaml` — отказ с причиной,
   не traceback. Пустой `stock.yaml → materials.<марка>.bars` — марка отклоняется по
   заготовке, не падает.
5. **ID стабилен.** `SH-<d>-<link>`; разбор регуляркой, ошибка формата — `ValueError`
   с путём и примером. Неизвестный ID — ошибка прогона (в `checks.md`).
6. **Никаких новых зависимостей** (PyYAML уже есть).
7. **Стиль проекта**: комментарии и докстринги по-русски, ссылки на Д-##/CP-##;
   выходы — через `egm/doc_yaml.py` (наследник `Doc`, GLOSSARY/PATTERNS/GENERIC,
   self_test на 100 % покрытие комментариями).
8. **Code-first спецификации не правятся руками** (Д-79): `SPEC-12_SHAFTS.md`
   генерируется прогоном; шаблон — `templates/SPEC-12_SHAFTS.md.tmpl`.
9. **Инструкции — часть задачи** (Д-108, этап 5): `instructions/INS-40_SHAFTS.md`
   (как добавить конфигурацию, что означает каждый параметр, как читать SPEC-12,
   порядок прогона, связь с CAD `.15`) + ссылки из `instructions/README.md §3`,
   `INS-10_PTK_CALC.md §2`, `INS-30_CAD.md`; обратные ссылки обязательны.
10. **Реестры** — только через upd.md (Journal); текст существующих строк не
    переписывать без необходимости.


---

## Файлы задачи

Ниже — свежие версии затрагиваемых файлов (rev13.4, база `2904cd1`). Порядок: входные конфиги →
материалы и заготовки → код расчёта → генерация документа → CAD → регистры.

Включены и файлы, которые модель запросила в прошлом ответе: `specs/materials.yaml`,
`egm/materials.py`, `specs/stock.yaml`, `egm/design_doc.py`, `egm/ptk_parts.py`,
`egm/cad/assy.py`, `instructions/INS-30_CAD.md`.

Не включены целиком (нужны точечно, по запросу): `egm/ptk_layout.py` (layout считается
по `d["output"]`; вал не участвует, но ключи `shaft` пересекаются),
`specs/ptk_designs.yaml` (89 КБ — эталон чисел), `docs/HG-Series-Catalog_opt.md`.


### Карта репозитория

```
configs/  (1): application.yaml
docs/  (7): HG-Series-Catalog_opt.md, HG-Series-Catalog_opt.pdf, RU2359790C1.pdf, cnc_axes_guide.md, ptk_condition.png, ptk_crown_profile.png, Материалы-заготовки  для ГК.md
egm/  (21): __init__.py, calc_vptc.py, catalog.py, catalog_doc.py, config.py, design_doc.py, doc_yaml.py, materials.py, naming.py, products.py, ptk.py, ptk_design.py, ptk_doc.py, ptk_force.py, ptk_join.py, ptk_layout.py, ptk_parts.py, ptk_profile.py, shaft_doc.py, shafts.py, srccheck.py
egm/cad/  (16): __init__.py, __main__.py, assy.py, freecad.py, model.py, ptk_collar.py, ptk_cover.py, ptk_ecc.py, ptk_hub.py, ptk_ring.py, ptk_sep.py, ptk_spacer.py, step.py, svg.py, techdraw.py, techdraw_sheet.py
instructions/  (8): INS-10_PTK_CALC.md, INS-20_CATALOG.md, INS-30_CAD.md, INS-40_SHAFTS.md, INS-90_AUDIT_BUNDLE.md, INS-91B_LOCAL.md, INS-91_CONTEXT_PREP.md, README.md
reports/  (3): cad_report.md, catalog_report.md, checks.md
specs/  (24): CANCELLED.md, CATALOGS.md, CODE_PLAN.md, DECISIONS.md, SPEC-01_NAMING.md, SPEC-02_PRECISION_EMBEDS.md, SPEC-03_PRODUCTS.md, SPEC-04_ARCHITECTURE.md, SPEC-10_PTK_CALC.md, SPEC-11_PTK_DESIGN.md, SPEC-12_SHAFTS.md, cad_set.yaml, catalog_hiwin_hg.yaml, catalog_hiwin_hg_pairs.json, concept_ptk.png, materials.yaml, products.yaml, ptk_configs.yaml, ptk_design_input.yaml, ptk_designs.yaml, ptk_input.yaml, shafts.yaml, stock.yaml, vendor_prices.yaml
templates/  (3): SPEC-10_PTK_CALC.md.tmpl, SPEC-11_PTK_DESIGN.md.tmpl, SPEC-12_SHAFTS.md.tmpl
tools/  (10): context_bundle.py, create_pr.py, ctx_task.py, fix_diff.py, freecad_egm.py, freecad_meta.py, freecad_techdraw.py, import_graph.py, make_audit_bundle.py, upd_apply.py
```

### Граф импортов (tools/import_graph.py)

```
# Импорт-граф — корни: egm, tools, main.py

egm (1 строк)
  imports: -
  imported by: egm.cad.__main__, egm.cad.assy, egm.cad.ptk_ring, egm.catalog_doc, egm.design_doc, egm.materials, egm.ptk, egm.ptk_design, egm.ptk_doc, egm.ptk_force, egm.ptk_join, egm.ptk_layout, egm.shaft_doc, egm.shafts, main
egm.cad (4 строк)
  imports: -
  imported by: egm.cad.__main__, egm.cad.assy, egm.cad.freecad, egm.cad.ptk_collar, egm.cad.ptk_cover, egm.cad.ptk_hub, egm.cad.ptk_ring, egm.cad.ptk_sep, egm.cad.ptk_spacer, egm.cad.techdraw_sheet, main, tools.freecad_techdraw
egm.cad.__main__ (475 строк)
  imports: egm, egm.cad, egm.cad.assy, egm.cad.freecad, egm.cad.ptk_collar, egm.cad.ptk_cover, egm.cad.ptk_ecc, egm.cad.ptk_hub, egm.cad.ptk_ring, egm.cad.ptk_sep, egm.cad.ptk_spacer, egm.cad.step, egm.cad.svg, egm.config, egm.design_doc, egm.products, egm.ptk, egm.ptk_design, egm.ptk_doc, egm.ptk_layout
  imported by: -
egm.cad.assy (660 строк)
  imports: egm, egm.cad, egm.cad.ptk_collar, egm.cad.ptk_cover, egm.cad.ptk_ecc, egm.cad.ptk_hub, egm.cad.ptk_ring, egm.cad.ptk_sep, egm.cad.ptk_spacer, egm.cad.step, egm.cad.techdraw, egm.config, egm.materials, egm.products, egm.ptk_layout, egm.ptk_parts, egm.ptk_profile
  imported by: egm.cad.__main__, main
egm.cad.freecad (110 строк)
  imports: egm.cad, egm.cad.step
  imported by: egm.cad.__main__, main
egm.cad.model (119 строк)
  imports: -
  imported by: egm.cad.ptk_collar, egm.cad.ptk_cover, egm.cad.ptk_ecc, egm.cad.ptk_hub, egm.cad.ptk_ring, egm.cad.ptk_sep, egm.cad.ptk_spacer, egm.cad.step, egm.cad.techdraw
egm.cad.ptk_collar (74 строк)
  imports: egm.cad, egm.cad.model, egm.cad.svg
  imported by: egm.cad.__main__, egm.cad.assy
egm.cad.ptk_cover (138 строк)
  imports: egm.cad, egm.cad.model, egm.cad.svg
  imported by: egm.cad.__main__, egm.cad.assy
egm.cad.ptk_ecc (48 строк)
  imports: egm.cad.model
  imported by: egm.cad.__main__, egm.cad.assy
egm.cad.ptk_hub (370 строк)
  imports: egm.cad, egm.cad.model, egm.cad.svg, egm.cad.techdraw
  imported by: egm.cad.__main__, egm.cad.assy, egm.cad.ptk_sep
egm.cad.ptk_ring (111 строк)
  imports: egm, egm.cad, egm.cad.model, egm.cad.svg, egm.ptk, egm.ptk_profile
  imported by: egm.cad.__main__, egm.cad.assy, main
egm.cad.ptk_sep (135 строк)
  imports: egm.cad, egm.cad.model, egm.cad.ptk_hub, egm.cad.svg
  imported by: egm.cad.__main__, egm.cad.assy, main
egm.cad.ptk_spacer (59 строк)
  imports: egm.cad, egm.cad.model, egm.cad.svg
  imported by: egm.cad.__main__, egm.cad.assy, main
egm.cad.step (119 строк)
  imports: egm.cad.model
  imported by: egm.cad.__main__, egm.cad.assy, egm.cad.freecad, main
egm.cad.svg (197 строк)
  imports: -
  imported by: egm.cad.__main__, egm.cad.ptk_collar, egm.cad.ptk_cover, egm.cad.ptk_hub, egm.cad.ptk_ring, egm.cad.ptk_sep, egm.cad.ptk_spacer
egm.cad.techdraw (297 строк)
  imports: egm.cad.model
  imported by: egm.cad.assy, egm.cad.ptk_hub, egm.cad.techdraw_sheet, main, tools.freecad_techdraw
egm.cad.techdraw_sheet (257 строк)
  imports: egm.cad, egm.cad.techdraw
  imported by: tools.freecad_techdraw
egm.calc_vptc (150 строк)
  imports: -
  imported by: -
egm.catalog (330 строк)
  imports: -
  imported by: main
egm.catalog_doc (237 строк)
  imports: egm, egm.doc_yaml
  imported by: main
egm.config (92 строк)
  imports: -
  imported by: egm.cad.__main__, egm.cad.assy, egm.materials, egm.ptk_design, egm.ptk_layout, egm.shafts, main
egm.design_doc (554 строк)
  imports: egm, egm.doc_yaml
  imported by: egm.cad.__main__, main
egm.doc_yaml (224 строк)
  imports: -
  imported by: egm.catalog_doc, egm.design_doc, egm.ptk_doc, egm.shaft_doc, main
egm.materials (112 строк)
  imports: egm, egm.config
  imported by: egm.cad.assy, egm.ptk_join, egm.ptk_layout, egm.shafts
egm.naming (71 строк)
  imports: -
  imported by: main
egm.products (68 строк)
  imports: -
  imported by: egm.cad.__main__, egm.cad.assy, main
egm.ptk (624 строк)
  imports: egm, egm.ptk_force, egm.ptk_parts, egm.ptk_profile
  imported by: egm.cad.__main__, egm.cad.ptk_ring, main
egm.ptk_design (699 строк)
  imports: egm, egm.config, egm.ptk_layout, egm.ptk_parts, egm.shafts
  imported by: egm.cad.__main__, main
egm.ptk_doc (285 строк)
  imports: egm, egm.doc_yaml
  imported by: egm.cad.__main__, main
egm.ptk_force (154 строк)
  imports: egm, egm.ptk_profile
  imported by: egm.ptk, main
egm.ptk_join (769 строк)
  imports: egm, egm.materials
  imported by: egm.ptk_layout
egm.ptk_layout (954 строк)
  imports: egm, egm.config, egm.materials, egm.ptk_join
  imported by: egm.cad.__main__, egm.cad.assy, egm.ptk_design
egm.ptk_parts (216 строк)
  imports: egm.ptk_profile
  imported by: egm.cad.assy, egm.ptk, egm.ptk_design, main
egm.ptk_profile (158 строк)
  imports: -
  imported by: egm.cad.assy, egm.cad.ptk_ring, egm.ptk, egm.ptk_force, egm.ptk_parts, main
egm.shaft_doc (167 строк)
  imports: egm, egm.doc_yaml, egm.shafts
  imported by: main
egm.shafts (287 строк)
  imports: egm, egm.config, egm.materials
  imported by: egm.ptk_design, egm.shaft_doc, main
egm.srccheck (51 строк)
  imports: -
  imported by: -
main (255 строк)
  imports: egm, egm.cad, egm.cad.assy, egm.cad.freecad, egm.cad.ptk_ring, egm.cad.ptk_sep, egm.cad.ptk_spacer, egm.cad.step, egm.cad.techdraw, egm.catalog, egm.catalog_doc, egm.config, egm.design_doc, egm.doc_yaml, egm.naming, egm.products, egm.ptk, egm.ptk_design, egm.ptk_doc, egm.ptk_force, egm.ptk_parts, egm.ptk_profile, egm.shaft_doc, egm.shafts
  imported by: -
tools.context_bundle (118 строк)
  imports: -
  imported by: -
tools.create_pr (184 строк)
  imports: -
  imported by: -
tools.ctx_task (274 строк)
  imports: -
  imported by: -
tools.fix_diff (557 строк)
  imports: -
  imported by: -
tools.freecad_egm (101 строк)
  imports: -
  imported by: -
tools.freecad_meta (42 строк)
  imports: -
  imported by: -
tools.freecad_techdraw (766 строк)
  imports: egm.cad, egm.cad.techdraw, egm.cad.techdraw_sheet
  imported by: -
tools.import_graph (154 строк)
  imports: -
  imported by: -
tools.make_audit_bundle (351 строк)
  imports: -
  imported by: -
tools.upd_apply (289 строк)
  imports: -
  imported by: -

Точки входа (не импортирует никто): egm.cad.__main__, egm.calc_vptc, egm.srccheck, main, tools.context_bundle, tools.create_pr, tools.ctx_task, tools.fix_diff, tools.freecad_egm, tools.freecad_meta, tools.freecad_techdraw, tools.import_graph, tools.make_audit_bundle, tools.upd_apply
Циклы импорта: не найдены
```

### Входные конфиги

===== FILE: specs/shafts.yaml (строки 1–89) =====
# ============================================================================
# shafts.yaml — НОМЕНКЛАТУРА входных валов редуктора (продукт SH, Д-107).
#
# Ручной конфиг (spec-first, Д-79). Здесь задаются КОНФИГУРАЦИИ вала — по одной
# записи на типоразмер и тип соединения. Проработка ПТК ссылается на запись по
# ID (specs/ptk_design_input.yaml → designs[].shaft: {id: SH-08-KEY}), а не
# описывает вал заново: одна и та же конфигурация переиспользуется всеми
# проработками и всеми продуктами (ПТК, ГК), которые её применяют.
#
# ID: SH-<d>-<link>, d — номинал Ø в мм (две цифры: 08, 10, 20), link — тип
# соединения эксцентрик–вал (key | flat | integral | spline | press). ID —
# стабильный ключ: он попадает в SPEC-12, в ptk_designs.yaml (input.shaft_id)
# и в обозначение детали .15 при генерации CAD. Переименование = новое решение.
#
# Проверка: python main.py design --publish (валидация вала идёт вместе с
# проработкой: τ, шпонка, стенки, стенка полого вала); результат — SPEC-12_SHAFTS.md
# и ptk_designs.yaml. Прогон main.py без проработок валидирует только формат.
#
# Поля записи (Д-110: только вход; умолчания — DEFAULTS в egm/shafts.py):
#   name        — наименование для спецификации и чертежа;
#   d           — Ø вала, мм: кручение, шпонка, стенки эксцентрика; он же Ø
#                 отверстия .03 и вала REF на чертежах;
#   bore        — Ø отверстия полого вала, мм; 0 — сплошной (τ растёт как 1/(1−β⁴));
#   link        — соединение эксцентрик–вал: key | flat | integral | spline | press;
#                 spline и press — только кручение (смятие не считается);
#                 flat — без смятия, в CAD круглое отверстие; integral — вал
#                 и эксцентрик одной деталью (CAD — CP-05);
#   applies_to  — продукты, где конфигурация применяется (справочно, для SPEC-12);
#   note        — примечание: откуда взята, что подтвердить; ручное значение допуска
#                 фиксируется здесь с обоснованием (Д-110).
#
# Не входят в запись (Д-110): [τ] = min(τ₋₁/(K_τ·S), 0.58·σт/S_т) и [σсм] = min(σт вала,
# .03, шпонки)/S_см — расчёт из материала; марку .15 подбирает калькулятор по
# products.15.material и stock.yaml; wall_min — DEFAULTS egm/shafts.py; length — по пакету
# (CP-91 этап 4). Ручной допуск — только переопределением в проработке:
# designs[].shaft = {id: SH-08-KEY, tau_allow: 25.0} (обоснование — в note записи).
# Устаревшие поля tau_allow / sigma_crush / wall_min в записи принимаются с
# предупреждением и считаются ручными значениями.
# Какое поле что значит и как читать SPEC-12 — instructions/INS-40_SHAFTS.md.
#
# Шпонки — общая таблица keys.table ниже (DIN 6885 / ГОСТ 23360), одна для входного
# вала и для выходного вала в ступице (CP-90). Живёт здесь, в номенклатуре валов,
# а не во входе проработки (Д-109, OQ-35 решён): паз — свойство сечения вала.
# ============================================================================

# --- Таблица шпонок (Д-109, OQ-35 решён) -------------------------------------
# Призматические шпонки исп. A (DIN 6885 / ГОСТ 23360): берётся первая строка с
# d ≤ d_max — b × h, глубина паза вала t1 и ступицы t2, мм; d_max — верхняя
# граница Ø вала, мм. Значения сверить со справочником. Одна таблица на входной
# вал и на выходной вал в ступице (CP-90): читает egm/ptk_design.keys_table()
# через products.SH.configs.shafts (Д-79); SPEC-12 печатает её разделом «Шпонки».
keys:
  table:
    - {d_max: 8, b: 2, h: 2, t1: 1.2, t2: 1.0}
    - {d_max: 10, b: 3, h: 3, t1: 1.8, t2: 1.4}
    - {d_max: 12, b: 4, h: 4, t1: 2.5, t2: 1.8}
    - {d_max: 17, b: 5, h: 5, t1: 3.0, t2: 2.3}
    - {d_max: 22, b: 6, h: 6, t1: 3.5, t2: 2.8}
    - {d_max: 30, b: 8, h: 7, t1: 4.0, t2: 3.3}
    - {d_max: 38, b: 10, h: 8, t1: 5.0, t2: 3.3}
    - {d_max: 44, b: 12, h: 8, t1: 5.0, t2: 3.3}

shafts:
  # --- Ø8: проработка K8 (перенесено из ptk_design_input.yaml, rev13.2) -----
  SH-08-KEY:
    name: "Вал входной Ø8, соединение шпонкой"
    d: 8.0
    bore: 0.0
    link: key
    applies_to: [PTK]
    note: "Исходная конфигурация проработки K8 (PTK-050, rev12.x); параметры не менялись"

  # --- Ø10: проработка K10 (перенесено из ptk_design_input.yaml, rev13.2) ---
  SH-10-KEY:
    name: "Вал входной Ø10, соединение шпонкой"
    d: 10.0
    bore: 0.0
    link: key
    applies_to: [PTK]
    note: "Исходная конфигурация проработки K10 (PTK-063, rev12.x); параметры не менялись"

  # --- Ø20: новая конфигурация (запрос заказчика, rev13.2) ------------------
  SH-20-KEY:
    name: "Вал входной Ø20, соединение шпонкой"
    d: 20.0
    bore: 0.0
    link: key
    applies_to: [PTK]
    note: "Новая конфигурация rev13.2: Ø20 под увеличенный редуктор (rev13.1). bore/link — по умолчанию; допуски и марка .15 — расчёт (Д-110), подтвердить прогоном K20 (CP-91 этап 6); полый вариант (bore > 0) — отдельной записью SH-20-KEY-B<bore>"
===== END FILE =====

===== FILE: specs/ptk_design_input.yaml (строки 1–76) =====
# Шаг 2 «Проработка» выбранных исполнений (Д-48, CP-38). Формат — YAML (Д-79).
#
# Связь шагов (Д-79): вход — ОПУБЛИКОВАННЫЙ результат шага 1 specs/ptk_configs.yaml;
# выход — specs/ptk_designs.yaml и specs/SPEC-11_PTK_DESIGN.md (их пишет машина, Д-105/Д-106).
#
# Порядок работы:
#   1) прогнать шаг 1: python main.py calc --publish;
#   2) выбрать исполнение по SPEC-10 (колонка ID);
#   3) вписать проработку в designs[] ниже;
#   4) прогнать шаг 2: python main.py design --publish — шаг 1 заново не считается.
#
# id — полный ID из SPEC-10 или префикс без хэша (Д-51): префикс переживает смену
# хэша шага 1 (правка параметров шага 1 меняет ID, проработка остаётся).

# Шпонки — specs/shafts.yaml → keys.table (Д-109): таблица одна для входного вала
# и для выходного вала в ступице (CP-90), поэтому живёт в номенклатуре валов.

# Проработки (Д-48). Несколько записей с одним id и разными name — сравнение
# вариантов вала (SPEC-11, таблица проработок).
designs:
  - id: PTK-063-R3X8-22M6P2
    # полный ID SPEC-10 или префикс без хэша (Д-51); если префиксу соответствует
    # несколько исполнений — уточнить полями bearing (подшипник) и/или gen
    # (тип генератора), иначе ошибка «неоднозначен»
    bearing: "61819"
    # имя проработки: латиница, цифры, «_», без «-», уникальное — суффикс деталей
    # <ID>.03B-<name> и сборки <ID>-<name>.step
    name: K8
    eta: 0.8          # КПД в T_вх = M/(u·eta); меньше — больше T_вх (OQ-08, OQ-15)
    ecc_share: 0.5    # доля T_вх на один эксцентрик — смятие шпонки (OQ-15)
    key_angle: 45.0   # паз ряда 1 от эксцентриситета, град; ряд k — key_angle − φk
    shaft: {id: SH-08-KEY}   # Д-107: ссылка на specs/shafts.yaml; список ID — наименьшая проходящая (Д-110);
                             # [τ], [σсм] и марка .15 — расчёт из материала (egm/shafts.py, SPEC-12);
                             # ручной допуск — {id: SH-08-KEY, tau_allow: 25.0} с обоснованием в note записи;
                             # полный блок d/bore/link/… — переходный формат, предупреждение «устарел (Д-107)»
    balance:         # балансировка пакета на шаге 2: Ø отверстий только из drills
      n_max: 3       # наибольшее число отверстий балансировки, шт
      wall: 1.0      # стенка у отверстий балансировки, мм
      drills: [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]
      # имеющиеся свёрла, мм; пусто — от bal_d_min с шагом bal_d_step (шаг 1)
    lighten: none    # облегчение ступицы — пока не используется (OQ-12)
    output:          # выходной вал в ступице (Д-102, CP-90); формат — как shaft, шпонки — keys.table
      link: key      # key | spline (только кручение); flange — до реализации отказ
      d: 0.0         # Ø вала, мм; 0 — подбор по кручению
      tau_allow: 25.0     # [τ] кручения; изгиб от потребителя не считается (OQ-17)
      sigma_crush: 130.0  # [σсм] шпонки в стальной ступице 40Х, спокойная нагрузка (130…200)
    layout: [L4, L3, L2]
    # layout: L1     # конструктив из products.yaml → PTK.layouts, по умолчанию L1:
                     #   L1 — стакан монолитом .02A (пруток);
                     #   L2 — обечайка с буртом .02B + дно-лист .13 + ступица .12A (толстостенная труба, Д-93);
                     #   L3 — обечайка без бурта .02C + дно-вставка .12B (труба любой толщины или лист);
                     #   L4 — обечайка без бурта .02C + кольцо-бурт .14 + дно-лист .13 + ступица .12A (Д-96, Д-97);
                     # список — первый, для которого есть заготовка и проходят штифты; порядок [L4, L3, L2] — Д-100;
                     # состав деталей с буквами исполнений — таблица «Конструктив» SPEC-11
    # join: {pin_d: [3.0], sig_wall: 150.0}   # штифты соединения .02–.12 (L2, L3, L4); схему задаёт конструктив
    # supports:      # опоры выхода (Д-55, Д-81): [τ] полой ступицы, стенки, поясок колец .11,
    #   tau_allow: 25.0
    #   hub_wall: 2.0
    #   seat_wall: 2.0
    #   ring_w: 2.0
    #   lip: 1.0      # буртик крышки за подшипником
    #   cup_t: 2.0    # дно стакана
    #   ax_gap: 0.5   # осевой зазор
    #   nut_h: 4.0    # гайка пакета эксцентриков (KM0)
    #   out_ext: 2.0  # выступ ступицы за .07B
  - id: PTK-063-R3X8-22M6P2
    bearing: "61819"
    name: K10
    eta: 0.8
    ecc_share: 0.5
    key_angle: 45.0
    shaft: {id: SH-10-KEY}   # Д-107, Д-110
    balance: {n_max: 3, wall: 1.0, drills: [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]}
    lighten: none
    output: {link: flange, d: 0.0, tau_allow: 25.0, sigma_crush: 130.0}   # Д-103/Д-104: момент — фланец на торце ступицы, шпонка — в гайке-опции
    layout: [L4, L3, L2]
===== END FILE =====

===== FILE: specs/products.yaml (строки 1–238) =====
# Реестр изделий и номенклатура деталей (spec-first, Д-80, SPEC-03). Формат — YAML (Д-79).
# kind: make — изготавливаемая, buy — покупная.
# variant: none | ring_phase | row | layout | thick | side — вариантность детали.
# product: <код> — деталь не изготовляется по своей номенклатуре, а берётся из продукта-источника
#   (Д-107: .15 ПТК ← продукт SH, конфигурация выбирается по ID в проработке).
# qty — число на исполнение или формула: rows, rows+1, rows-1, rows*n_bodies.
# cad — имя генератора egm/cad или null (новый генератор — INS-30 §6).

PTK:
  name: Волновой редуктор с промежуточными телами качения
  id_rule: Д-80
  parts:
    "01":
      name: "венец (жёсткое колесо)"
      kind: make
      material: [ШХ15]                 # марки по предпочтению — specs/materials.yaml (Д-67)
      variant: ring_phase   # варианты .01A, .01B — по сдвигу сверловки s (Д-19)
      qty: rows
      cad: ptk_ring
    "02":
      name: сепаратор
      kind: make
      material: [38Х2МЮА, 40Х, 40ХН2МА, 20ХН3А, 30ХГСА, "40", 35ХМ, 30Х3МФ]   # первая марка, у которой есть заготовка нужной формы (Д-68); новые — в конце (CP-86)
      variant: layout       # буква исполнения задаётся конструктивом; без конструктива (шаг 1) — одна деталь без буквы
      variants:             # исполнения (Д-73): key — ключ в layouts.parts
        A: {key: cup, layout: L1, blank: "пруток",
            name: "стакан монолитом: обечайка с окнами, дно и ступица выхода — одна деталь"}
        B: {key: collar, layout: L2, blank: "толстостенная труба",
            name: "обечайка с буртом на выходном торце; к торцу бурта — дно-лист .13 осевыми штифтами (Д-92, Д-93, CP-79)"}
        C: {key: plain, layout: L3, blank: "труба любой толщины или лист (вальцовка + сварка)",
            name: "обечайка без бурта, стенка как у окон по всей длине; внутрь — дно-вставка .12B (L3) или кольцо-бурт .14 (L4, CP-81)"}
      qty: 1
      cad: ptk_sep
    "03":
      name: эксцентрик генератора
      kind: make
      material: [40Х]                  # предварительно; ШХ15 при качении тел по эксцентрику (OQ-21)
      variant: row          # .03A… — по ряду k: паз шпонки на угле key_angle − φk (Д-46); единый вал — variant: none, qty: 1
      qty: rows
      cad: ptk_ecc
    "04":
      name: тело качения
      kind: buy
      variant: none
      qty: rows*n_bodies
      cad: null
    "05":
      name: межрядная шайба
      kind: make
      material: ["45"]                 # предварительно (OQ-21)
      variant: thick        # A — у торцов пакета, B — между рядами — по толщине h (Д-53)
      qty: rows+1
      cad: ptk_spacer
    "06":
      name: корпус
      kind: make
      variant: none
      qty: 1
      cad: null
    "07":
      name: "крышка (A — вход, B — выход)"
      kind: make
      material: ["45"]                 # предварительно (OQ-21)
      variant: side         # A — вход, B — выход (Д-54)
      qty: 2
      cad: ptk_cover
    "08":
      name: подшипник генератора
      kind: buy
      variant: none
      qty: rows
      cad: null
    "09":
      name: подшипник выхода
      kind: buy
      variant: none
      qty: 1
      cad: null
    "10":
      name: подшипник входного вала
      kind: buy
      variant: none
      qty: 2
      cad: null
    "11":
      name: дистанционное кольцо эксцентриков
      kind: make
      material: ["45"]                 # предварительно (OQ-21)
      variant: none
      qty: rows-1
      cad: ptk_cover
    "12":
      name: ступица выхода
      kind: make
      material: [40Х]                  # предварительно (OQ-21)
      variant: layout       # буква исполнения задаётся конструктивом (L2, L3); в L1 ступица — часть стакана .02A
      variants:             # исполнения (Д-73); CAD — CP-63
        A: {key: flange, layout: L2,   # key "flange" — историческое имя join-схемы, не термин
            name: "ступица с опорным ободом: при output ободом во внутреннюю сторону бурта .02B / кольца .14 (радиальные штифты со стороны окон), охватывает .09, без .13 (Д-102 п. 2); иначе к дну-листу .13 (Д-93, CP-80)"}
        B: {key: insert, layout: L3,
            name: "дно-вставка: входит внутрь обечайки .02C, бурт упирается в её торец, штифты через стенку обечайки"}
      qty: 1
      cad: ptk_hub
    "13":
      name: дно-лист
      kind: make
      material: [40Х]                  # точение из прутка (Д-93); t_s — расчёт ptk_join (OQ-27)
      variant: none         # L2: к торцу бурта .02B осевыми штифтами; ступица .12A — к нему (CP-80)
      qty: 1
      cad: ptk_leaf
    "14":
      name: кольцо-бурт
      kind: make
      material: [40Х]                  # труба или пруток по stock.yaml (CP-81); марку подтвердить — OQ-21
      variant: none         # L4: в торце обечайки .02C радиальными штифтами по окнам; к торцу — дно-лист .13 (Д-96)
      qty: 1
      cad: ptk_collar
    "15":
      name: входной вал
      kind: make
      material: [40Х]                  # предварительный выбор; по Д-110 марка подбирается
                                       # калькулятором по порядку списка (пруток в stock.yaml,
                                       # затем τ, шпонка, стенка полого вала); 45 — резерв,
                                       # прутков 45 в stock.yaml пока нет (OQ-21, OQ-32)
      variant: none         # Д-107: конфигурация — номенклатура продукта SH (specs/shafts.yaml → shafts.<ID>);
                            # в проработке задаётся только designs[].shaft.id, а не полный блок параметров.
                            # Соединение с .03 (key/flat/spline/integral/press) и шпонка (keys.table, Д-46) —
                            # поля записи вала
      product: SH           # переиспользуемая номенклатура валов (Д-107); вал входит в ПТК как деталь .15
      qty: 1
      cad: null             # генератор .15 — CP-91 этап 4 (egm/cad/ptk_shaft.py, посадки .03/.10, паз, маршрут); в сборке пока REF-примитив
    "16":
      name: "гайка выхода (опция)"     # гайка-опция под «фланец» для монтажа к валу (Д-103, Д-104)
      kind: make
      material: [40Х]                  # предварительно (OQ-21)
      variant: none         # опция: момент передаёт фланец ступицы (Д-104); в гайке — отверстие d_o со шпоночным пазом b × t2 (перенос из ступицы, Д-104) и посадка/резьба на фланец ступицы; деталировка — CP-90 этап 2b-3
      qty: 1
      cad: null             # генератор — CP-90 этап 2b-3 (OQ-33); в сборке пока REF-примитив
  layouts:
    # Д-55: конструктив — выбор деталей и вариантов; null — деталь не входит;
    # fixed / output — неподвижное и выходное звено
    # join — как сепаратор .02 соединяется со ступицей .12 (только при отдельной ступице):
    #   collar (L2) — бурт .02B, к его торцу дно-лист .13 осевыми штифтами, ступица .12A — к листу (Д-92, Д-93);
    #   insert (L3) — обечайка без бурта, дно-вставка .12B внутри, радиальные штифты через стенку по окнам;
    #   ring (L4) — кольцо-бурт .14 в торце .02C радиальными штифтами по окнам, лист .13 к кольцу осевыми (Д-96, Д-97).
    #   Момент передают штифты (τ, смятие, кромки — ptk_join);
    #   натяг или анаэробный фиксатор — только резерв; сварки нет (40Х коробит стенку 0.88 мм)
    L1:
      name: "стакан-сепаратор монолитом"
      fixed: ring
      output: cage
      parts:
        "01": ring_phase
        "02": cup          # .02A — стакан монолитом
        "03": row
        "04": body
        "05": thick
        "06": null
        "07": side
        "08": gen
        "09": out
        "10": in
        "11": ring
        "12": null         # ступица — часть стакана .02A
    L2:
      name: "обечайка с буртом + дно-лист + ступица с фланцем"
      fixed: ring
      output: cage
      join: collar         # дно-лист .13 к торцу бурта .02B, ступица .12A к листу — осевые штифты (Д-93)
      parts:
        "01": ring_phase
        "02": collar       # .02B — обечайка с буртом (толстостенная труба)
        "03": row
        "04": body
        "05": thick
        "06": null
        "07": side
        "08": gen
        "09": out
        "10": in
        "11": ring
        "12": flange       # .12A — ступица с фланцем (CP-80)
        "13": leaf         # .13 — дно-лист (CP-80)
    L3:
      name: "обечайка без бурта + дно-вставка"
      fixed: ring
      output: cage
      join: insert         # дно .12B внутри .02C, штифты через стенку обечайки по делению окон (одна установка SM-1)
      parts:
        "01": ring_phase
        "02": plain        # .02C — обечайка без бурта (труба любой толщины или лист weld)
        "03": row
        "04": body
        "05": thick
        "06": null
        "07": side
        "08": gen
        "09": out
        "10": in
        "11": ring
        "12": insert       # .12B — дно-вставка с буртом
    # L2 по Д-92/Д-93 (CP-79, CP-80): бурт .02B (наружу/внутрь — выбирает калькулятор), дно-лист — отдельная
    #   деталь на торце бурта, осевые сквозные штифты; ступица — отдельная, к дну-листу осевыми штифтами.
    L4:
      name: "обечайка без бурта + кольцо-бурт + дно-лист + ступица"
      fixed: ring
      output: cage
      join: ring           # кольцо .14 в торце .02C радиальными штифтами по окнам, лист .13 к кольцу осевыми (Д-96)
      parts:
        "01": ring_phase
        "02": plain        # .02C — обечайка без бурта (как L3)
        "03": row
        "04": body
        "05": thick
        "06": null
        "07": side
        "08": gen
        "09": out
        "10": in
        "11": ring
        "12": flange       # .12A — ступица: прямо в обод → фланец (Д-95, Д-94)
        "13": leaf         # .13 — дно-лист
        "14": collar       # .14 — кольцо-бурт (CP-81)
SH:
  name: "Входной вал редуктора (номенклатура конфигураций)"
  id_rule: "SH-<d>-<link>, Д-107"     # ID записи: d — номинал Ø (08, 10, 20), link — тип соединения с .03
  source: specs/shafts.yaml           # номенклатура: конфигурации валов (рукопиcный YAML, Д-79)
  spec: specs/SPEC-12_SHAFTS.md       # code-first спецификация валов (генерируется, CP-91 этап 3)
  instruction: instructions/INS-40_SHAFTS.md   # инструкция по номенклатуре (CP-91 этап 5, Д-108)
  cad: ptk_shaft                      # генератор детали .15 (CP-91 этап 4)
  # Номенклатура деталей продукта не ведётся: вал задаётся конфигурацией в shafts.yaml,
  # а не позициями .NN. Поле parts оставлено пустым для совместимости с check_app.
  parts: {}

HD:
  name: "Волновой редуктор с гибким колесом (ГК)"
  id_rule: "TODO(CP-09)"
  parts: {}
===== END FILE =====

===== FILE: configs/application.yaml (строки 1–54) =====
# Общий конфиг приложения (Д-79, rev 9.4). Формат — YAML (Д-79). Читается кодом
# (egm/config.py → load_app): данные берутся отсюда, а не из хардкодов в коде.
# Сами текущие конфиги сюда НЕ вкладываются: в configs: — ссылки (пути от корня
# репозитория), правятся по своим путям; код резолвит их egm/config.py → cfg_file.
# Раздел products: — по продукту из реестра configs.products (products.yaml,
# SPEC-03): новый продукт — свой раздел здесь и запись в products.yaml; полный
# прогон проверяет разделы (egm/products.py → check_app).
# Раздел cad: — механизм построения чертежей (INS-30 §7): SVG и 3D-экспорт в двух
# форматах — основной STEP и альтернативный FreeCAD (.FCStd).

app:
  name: HarmonicV2

paths:                      # каталоги от корня репозитория
  specs: specs              # ручные конфиги и code-first данные (Д-79)
  reports: reports          # отчёты прогона
  templates: templates      # шаблоны SPEC-10/SPEC-11
  out: out                  # рабочая папка прогона (в git не хранится)

configs:                    # пучок текущих конфигов — ссылки, не вложенные копии (Д-79)
  products: specs/products.yaml              # перечень изделий и номенклатура деталей (SPEC-03)
  vendor_prices: specs/vendor_prices.yaml    # тела качения и подшипники — вход шага 1
  stock: specs/stock.yaml                    # остатки склада (файл не обязателен)
  materials: specs/materials.yaml            # марки: графа 3, термообработка (Д-67)
  cad_set: specs/cad_set.yaml                # комплект чертежей (Д-61)
  catalog_md: docs/HG-Series-Catalog_opt.md  # каталог HIWIN HG — источник CAT-01

products:                   # по продукту из реестра configs.products (Д-79)
  PTK:
    enabled: true           # номенклатура и расчёт настроены (SPEC-10/SPEC-11)
    configs:                # входные конфиги продукта — шаги 1 и 2 (Д-79)
      input: specs/ptk_input.yaml                # шаг 1 «Расчёт» (SPEC-10)
      design_input: specs/ptk_design_input.yaml  # шаг 2 «Проработка» (SPEC-11)
  SH:
    enabled: true           # Д-107: номенклатура входных валов (specs/shafts.yaml); расчёт — в проработках ПТК
    configs:
      shafts: specs/shafts.yaml   # конфигурации валов SH-<d>-<link> (вход egm/shafts.py)
  HD:
    enabled: false          # заготовка: номенклатура в products.yaml пуста (TODO(CP-09))
    configs: {}             # входные конфиги ГК — по мере проработки

cad:                        # механизм построения чертежей (INS-30 §7)
  out_dir: out/cad                            # каталог вывода чертежей
  report: reports/cad_report.md               # отчёт прогона — записи добавляются (Д-79, Д-62, Д-83)
  svg:
    enabled: true                             # 2D-вид по оси (1:1, мм)
  export:                   # 3D-экспорт из одной геометрии (Д-30, Д-32) — форматы
    step:                   # основной формат — STEP (CP-29)
      enabled: true
      mode: spline          # контур впадин (INS-30 §6): spline — B-сплайн | poly — ломаная
    freecad:                # альтернативный формат — FreeCAD, .FCStd (rev 9.4)
      enabled: false        # включить — true; нужен установленный FreeCAD
      format: FCStd
      command: FreeCADCmd   # головной FreeCAD: freecadcmd | FreeCADCmd | полный путь
===== END FILE =====

### Материалы и заготовки (материал .15 подбирается здесь)

===== FILE: specs/materials.yaml (строки 1–161) =====
# Материалы — справочник марок (Д-67). Формат — YAML (Д-79). Заполняет заказчик.
# Ключ — марка; на него ссылаются products.yaml → parts.<NN>.material и
# stock.yaml → materials. Числовые марки — в кавычках ("45").
# title — графа 3 основной надписи (ГОСТ 2.104): марка и стандарт на марку; сортамент
#   заготовки пока не указывается (OQ-21). Редакции стандартов сверить.
# rho — плотность, г/см³, справочно (для массы — позже); heat — термообработка;
# use — где применяется (docs/Технология изготовления/TECH-01, TECH-02).
# E — модуль упругости при 20 °C, ГПа; alpha — КЛР 20–100 °C, 10⁻⁶ 1/°C;
# sigma_v / sigma_t / sigma_m1 — σв, σ0,2 и σ₋₁, МПа: механические свойства для расчёта
#   допусков (Д-110, Д-112): [τ] = min(σ₋₁·0.58/(K_τ·S), 0.58·σт/S_т). Заполнены для марок,
#   которые подбираются как материал вала .15 (40Х, 45); остальным — по мере надобности,
#   отсутствие поля не ошибка (σ₋₁ оценивается как 0.43·σв).
# state — состояние термообработки, к которому относятся sigma_v / sigma_t / sigma_m1;
# d_range — [Ø_min, Ø_max] заготовки, мм, для которого эти свойства справедливы.
# sigma_allow — допускаемое [σ], МПа = σт / 2.5 (σт — справочный предел текучести после
#   закалки и высокого отпуска, пруток Ø25, если не оговорено); коэффициент 2.5 — подтвердить.
#   Справочно (CP-89, Д-101): код пока не читает; для тонкостенной трубы σт брать по сертификату.
#   Заполнено для марок CP-86; остальным — по мере надобности.
# sigma_v, sigma_t, sigma_m1 — σв, σт, σ₋₁, МПа; state — термообработка, для которой они
#   справедливы; d_range — [мин, макс] Ø заготовки, мм (Д-110, OQ-36). Читает egm/shafts.py:
#   допуски вала .15 [τ] = min(0.58·σ₋₁/(K_τ·S), 0.58·σт/S_т), [σсм] — по min σт вала/.03/шпонки.
#   Нет sigma_m1 — оценка 0.43·σв (помечается в результате); нет sigma_v/sigma_t — марка
#   отклоняется для .15 с причиной. Значения ПРЕДВАРИТЕЛЬНЫЕ — сверить по ГОСТ 4543-2016 /
#   ГОСТ 1050-2013 / ГОСТ 8479 (OQ-36).
materials:
  ШХ15:
    title: "Сталь ШХ15 ГОСТ 801"
    rho: 7.81
    heat: "закалка + низкий отпуск, 60–64 HRC"
    use: "венец .01 (TECH-02), тела качения"
    sigma_v: 2160         # σв, МПа — ГОСТ 801-78, закалка 810 °C (вода до 200 °C, затем масло),
                          #   отпуск 150 °C, сечение 30…60 мм; отжиг даёт 590…730, но венец — закалённый
    sigma_t: 1670         # σ0,2, МПа — то же состояние (отжиг: 370…410)
    sigma_m1: 652         # σ₋₁ (изгиб), МПа — марочник: σ0,2 1670, σв 2160, НВ 582…670;
                          #   для отожжённого состояния (НВ 192) — 333, для НВ 616 — 804
    state: "закалка 810 °C, масло; отпуск 150 °C, 60…64 HRC"
    d_range: [0, 60]      # данные для сечения 30…60 мм; крупнее — прокаливаемость падает
  38Х2МЮА:
    title: "Сталь 38Х2МЮА ГОСТ 4543-2016"
    rho: 7.71
    heat: "улучшение + азотирование"
    use: "сепаратор .02 — основная марка (TECH-01)"
    sigma_v: 980          # σв, МПа — ГОСТ 4543, пруток Ø30: закалка 940 °C (вода/масло), отпуск 640 °C
    sigma_t: 835          # σ0,2, МПа — то же состояние (отпуск 660 °C: 810 / 650)
    sigma_m1: 392         # σ₋₁ (изгиб), МПа — нижняя граница марочника 392…480 (состояние 810/650,
                          #   НВ 255); для σв 980 взята консервативно; азотирование даёт 608…617
    state: "улучшение (закалка 940 °C, отпуск 640 °C); азотирование — опция"
    d_range: [0, 60]      # Ø60 — 1030 / 880, Ø100 — 880 / 730, Ø200 — 780 / 590
  40Х:
    title: "Сталь 40Х ГОСТ 4543-2016"
    rho: 7.82
    heat: "улучшение; азотирование — опция"
    use: "сепаратор .02, эксцентрик .03, ступица .12"
    sigma_v: 980          # σв, МПа — ГОСТ 4543, пруток Ø25: закалка 860 °C (масло), отпуск 500 °C
    sigma_t: 785          # σ0,2, МПа — то же состояние (норма: ≥980 / ≥785; марочник: 980 / 780)
    sigma_m1: 509         # σ₋₁ (изгиб, симметричный цикл), МПа — марочник 40Х для σв 960…980,
                          #   σ0,2 870; при отсутствии — оценка 0.43·σв (DEFAULTS.m1_k)
    state: "улучшение (закалка 860 °C, масло, отпуск 500 °C)"
    d_range: [0, 100]     # Ø заготовки, мм: свойства справочника — для прутка Ø25; сечения 100…300 мм
                          #   дают σв 655 / σ0,2 490 (марочник) — вне d_range марка не годится
  40ХН2МА:
    title: "Сталь 40ХН2МА ГОСТ 4543-2016"
    rho: 7.85
    heat: "улучшение ≈ 280–320 HB; азотирование — опция"
    use: "гибкое колесо ГК (TECH-01), сепаратор .02"
    sigma_v: 1080         # σв, МПа — ГОСТ 4543, пруток Ø25: закалка 850 °C (масло), отпуск 620 °C (вода);
                          #   отпуск в масле — 980 / 835 (норма ГОСТ: ≥980 / ≥835)
    sigma_t: 930          # σ0,2, МПа — то же состояние (в масле — 835)
    sigma_m1: 519         # σ₋₁ (изгиб), МПа — марочник для σв 1080 / σ0,2 880; τ₋₁ 274
    state: "улучшение (закалка 850 °C, масло, отпуск 620 °C)"
    d_range: [0, 60]      # данные для прутка Ø25…40; Ø100 (центр) — 850 / 670, Ø120 — 830 / 630
  38Х2Н2МА:
    title: "Сталь 38Х2Н2МА ГОСТ 4543-2016"
    rho: 7.85
    heat: "улучшение ≈ 280–320 HB"
    use: "гибкое колесо ГК — аналог SNCM439 (TECH-01)"
    sigma_v: 1080         # σв, МПа — ГОСТ 4543, пруток: закалка 870 °C (масло), отпуск 580 °C (воздух/масло)
    sigma_t: 930          # σ0,2, МПа — то же состояние; КП 785 (поковки) — 930 / 785
    sigma_m1: 363         # σ₋₁ (изгиб), МПа — марочник для улучшенного состояния (σ0,2 880),
                          #   n = 5·10⁶; для отпущенного до σв 720 — 300
    state: "улучшение (закалка 870 °C, масло, отпуск 580 °C)"
    d_range: [0, 60]      # Ø30 — 1000 / 860, Ø80 — 900 / 750 (закалка 860, отпуск 560);
                          #   прокаливаемость в масле — до Ø100
  20ХН3А:
    title: "Сталь 20ХН3А ГОСТ 4543-2016"
    rho: 7.85
    heat: "цементация + закалка"
    use: "сепаратор .02 (TECH-01)"
  30ХГСА:
    title: "Сталь 30ХГСА ГОСТ 4543-2016"
    rho: 7.85
    heat: "улучшение"
    use: "тонкий лист для .02, маршрут weld — лист 1.5 мм найден, наличие подтверждать (TECH-01, CP-85)"
    sigma_v: 1080         # σв, МПа — ГОСТ 4543, пруток Ø25: закалка 880 °C (масло), отпуск 540 °C
    sigma_t: 830          # σ0,2, МПа — то же состояние (отпуск 600 °C: 1000 / 880 при Ø30)
    sigma_m1: 470         # σ₋₁ (изгиб), МПа — марочник для σв 1080; для σв 880 — 372, для 1670 — 490
    state: "улучшение (закалка 880 °C, масло, отпуск 540 °C)"
    d_range: [0, 60]      # Ø30 — 1000 / 880, Ø80 — 860 / 740 (отпуск 600 °C)
  "45":
    title: "Сталь 45 ГОСТ 1050-2013"
    rho: 7.82
    heat: "нормализация / улучшение"
    use: "шайбы .05, крышки .07, кольца .11 — предварительно (OQ-21); трубы ГОСТ 21729 есть, но для .02 не применять; .12/.13/.14 — только пруток (Д-101)"
    sigma_v: 600          # σв, МПа — ГОСТ 1050-2013, пруток Ø25, нормализация
    sigma_t: 355          # σ0,2, МПа — то же состояние; марка шпонки по умолчанию (DEFAULTS.key_grade)
    sigma_m1: 290         # σ₋₁ (изгиб, симметричный цикл), МПа — справочная таблица пределов
                          #   выносливости для σв 600; при отсутствии — 0.43·σв
    state: "нормализация"
    d_range: [0, 80]      # Ø заготовки, мм: свойства — для Ø25; крупнее — σв 530 / σ0,2 275 (марочник)
  08пс:
    title: "Сталь 08пс ГОСТ 1050-2013"
    rho: 7.87
    heat: "нитроцементация, тонкий слой"
    use: "лист ГОСТ 19904; для окон .02 слабо — в .02 не допущен (TECH-01)"
  60С2А:
    title: "Сталь 60С2А ГОСТ 14959-2016"
    rho: 7.69
    heat: "закалка + средний отпуск 43–51 HRC; склонна к обезуглероживанию"
    use: "кандидат: ГК — проверить (OQ-22); для .02 не рекомендуется — не сваривается (Д-68)"
  "40":
    title: "Сталь 40 ГОСТ 1050-2013"
    rho: 7.82
    heat: "нормализация; ферритная нитроцементация (QPQ) — окна .02"
    use: "лист для .02, маршрут weld (сварка с подогревом) (Д-68)"
  "50":
    title: "Сталь 50 ГОСТ 1050-2013"
    rho: 7.81
    heat: "нормализация / закалка; ферритная нитроцементация (QPQ)"
    use: "пруток/труба для .02 без сварки; плохо сваривается (Д-68)"
  35ХМ:
    title: "Сталь 35ХМ ГОСТ 4543-2016"
    rho: 7.82
    E: 213
    alpha: 12.3
    sigma_allow: 330      # σ0.2 = 835 (пруток 25, закалка 850 °C + отпуск 560 °C)
    heat: "улучшение + азотирование"
    use: "кандидат: тонкостенная х/д труба 70…72×3…4 для .02C (L3/L4) (CP-86, TECH-01)"
  30Х3МФ:
    title: "Сталь 30Х3МФ ГОСТ 4543-2016"
    rho: 7.80
    E: 210                # по аналогу 1.7707 (30CrMoV9)
    alpha: 11.5           # по аналогу 1.7707
    sigma_allow: 330      # σт = 835 (пруток Ø25, закалка 870 °C + отпуск 620 °C)
    heat: "улучшение + азотирование; слой и твёрдость — уточнить у термиста"
    use: "кандидат: пруток Ø70–75 — альтернатива 38Х2МЮА для L1 и трепанации (CP-86)"
  40ХМФА:
    title: "Сталь 40ХМФА ГОСТ 4543-2016"
    rho: 7.82
    E: 214                # по аналогу 40Х — сверить
    alpha: 11.9           # по аналогу 40Х — сверить
    sigma_allow: 370      # σт = 930 (пруток Ø25, закалка 860 °C + отпуск 580 °C)
    heat: "улучшение; азотирование — опция"
    use: "только при наличии х/д трубы ≈70×4…5 (не подтверждено); г/д крупные — не для .02 (CP-86)"
  25CrMo4:
    title: "Сталь 25CrMo4 EN 10083-3"
    rho: 7.85
    E: 210                # типовое; MakeItFrom — 190, сверить
    alpha: 13.0           # MakeItFrom, диапазон не указан — сверить
    sigma_allow: 235      # Re ≥ 590 (+QT)
    heat: "улучшение + азотирование"
    use: "запасной: прецизионная труба EN 10305; производство в РФ не подтверждено (CP-86)"
===== END FILE =====

===== FILE: egm/materials.py (строки 1–112) =====
"""Материалы и заготовки по материалам (Д-67, CP-57).

specs/materials.yaml — справочник марок: обозначение для графы 3 основной надписи,
плотность, термообработка, применение. Деталь ссылается на марки:
products.yaml → parts.<NN>.material — список по предпочтению.
specs/stock.yaml → materials.<марка> — у каждой марки свой набор форм (tubes, sheets,
bars): сортамент зависит от материала (40ХН2МА — в основном толстостенные
горячедеформированные трубы ГОСТ 8732; лист ГОСТ 19904 — в основном 08пс, TECH-01).
Старый формат stock.yaml (tubes/sheets/bars без марки) читается как марка None.
Ключи марок — строки ("45" в YAML — в кавычках; число приводится к строке).
"""
FORMS = ("tubes", "sheets", "bars")


def grades(mats):
    """materials.yaml -> {марка (str): запись}."""
    return {str(k): (v or {}) for k, v in ((mats or {}).get("materials") or {}).items()}


def stock_by_material(stock):
    """stock.yaml -> {марка | None: {tubes, sheets, bars}}."""
    if not stock:
        return {}
    if "materials" in stock:
        return {str(k): {f: list((v or {}).get(f) or []) for f in FORMS}
                for k, v in (stock.get("materials") or {}).items()}
    return {None: {f: list(stock.get(f) or []) for f in FORMS}}


def title(mats, grade):
    """Графа 3 основной надписи по марке; нет в справочнике — сама марка; нет марки — ""."""
    if grade is None or grade == "":
        return ""
    return grades(mats).get(str(grade), {}).get("title") or str(grade)


def part_materials(prods, code, nn):
    """Марки детали code.nn по предпочтению (products.yaml → material) или []."""
    it = (((prods or {}).get(code) or {}).get("parts") or {}).get(nn) or {}
    return [str(m) for m in (it.get("material") or [])]


def props(mats, grade):
    """Механические свойства марки (Д-110, OQ-36) -> {sigma_v, sigma_t, sigma_m1, state,
    d_range} | None — марки нет в справочнике. Отсутствующие поля — None (не ошибка)."""
    if grade is None:
        return None
    g = grades(mats)
    if str(grade) not in g:
        return None
    return {k: g[str(grade)].get(k) for k in ("sigma_v", "sigma_t", "sigma_m1", "state", "d_range")}


def check(mats, prods, stock):
    """Ошибки: марки products.yaml и stock.yaml, которых нет в materials.yaml; трубы без D, s."""
    fails, known = [], set(grades(mats))
    for code, prod in (prods or {}).items():
        if not isinstance(prod, dict):
            continue
        for nn, it in (prod.get("parts") or {}).items():
            ms = (it or {}).get("material")
            if ms is None:
                continue
            if not isinstance(ms, list):
                fails.append(f"products.yaml: {code}.{nn}.material — нужен список марок (Д-67)")
                continue
            fails += [f"products.yaml: {code}.{nn}: марки {m} нет в materials.yaml (Д-67)"
                      for m in ms if str(m) not in known]
    for m, forms in stock_by_material(stock).items():
        if m is not None and m not in known:
            fails.append(f"stock.yaml: марки {m} нет в materials.yaml (Д-67)")
        for t in forms["tubes"]:
            if not isinstance(t, dict) or "D" not in t or "s" not in t:
                fails.append(f"stock.yaml: {m}: труба {t} — нужны D и s")
    return fails


def _load(app, key):
    from egm import config
    try:
        p = config.cfg_file(app, key)
    except Exception:
        return {}
    return config.load(p) if p.exists() else {}


def check_repo():
    """Сверка реальных конфигов (configs/application.yaml → configs.*): ошибки — в checks.md."""
    from egm import config
    app = config.load_app()
    fails = check(_load(app, "configs.materials"), _load(app, "configs.products"),
                  _load(app, "configs.stock"))
    assert not fails, fails
    return True


def self_test():
    mats = {"materials": {"40Х": {"title": "Сталь 40Х ГОСТ 4543-2016"}, 45: {}}}
    prods = {"PTK": {"parts": {"02": {"material": ["40Х", "38Х2МЮА"]}, "04": {}},
                     "layouts": {}}, "version": 7}
    stock = {"materials": {"40Х": {"bars": [70.0]}, "45": {"tubes": [{"D": 70.0}]}}}
    f = check(mats, prods, stock)
    assert len(f) == 2 and "38Х2МЮА" in f[0] and "D и s" in f[1], f
    assert title(mats, "40Х").startswith("Сталь 40Х") and title(mats, 45) == "45", title(mats, 45)
    assert title(mats, None) == "" and title(mats, "Х") == "Х"
    assert stock_by_material({"tubes": [1]})[None]["tubes"] == [1]
    assert stock_by_material(stock)["40Х"] == {"tubes": [], "sheets": [], "bars": [70.0]}
    assert part_materials(prods, "PTK", "02") == ["40Х", "38Х2МЮА"]
    assert part_materials(prods, "PTK", "09") == [] and part_materials(prods, "HD", "01") == []
    assert props(mats, "40Х")["sigma_v"] is None and props(mats, 45)["state"] is None
    assert props(mats, "Х") is None and props(mats, None) is None
    return True
===== END FILE =====

===== FILE: specs/stock.yaml (строки 1–193) =====
# Полуфабрикаты по маркам — заполняет заказчик (Д-56, Д-67). Формат — YAML (Д-79).
# У каждой марки свой сортамент: формы и размеры задаются внутри materials.<марка>.
# Ключ марки — из specs/materials.yaml. Размеры — пример, проверить наличие.
# Ориентир: трубы ГОСТ 8734 / EN 10305 (холоднодеф.), ГОСТ 8732 (горячедеф.);
# листы ГОСТ 19904; пруток ГОСТ 2590.
# Заготовка .02 подбирается на шаге 2 (ptk_layout.blanks): марки — по порядку
# products.yaml → PTK.parts."02".material; берётся первая с подходящей формой,
# остальные подходящие — «также» в SPEC-11.
# Запрос поставщикам (CP-85): трубы 73×5, 70×7, 73×18 в 30ХГСА и 40Х (у 40Х 73×18 в списке нет),
# пруток 40Х Ø50–75 (.12, .13, .14); х/д 35ХМ 70…72×4 (CP-86). До ответа размеры — примеры.
# Не искать (TECH-01, CP-86): 15ХФ, лист 25ХГТ, г/д 40ХМФА, трубы Ø76+ для L3/L4 PTK-050.

# Припуск на сторону: труба / лист, мм.
tube_allow: 0.5
sheet_allow: 0.3
# Допуски труб (доли), Д-72: ГОСТ 8732 обычной точности — D ±0.8 %, стенка −15 %; для 8734 — с запасом.
tube_tol_D: 0.008
tube_tol_s: 0.15

materials:
  40Х:
    tubes:                               # D — наружный Ø, s — стенка, мм
      - {D: 25.0, s: 3.0, note: "ГОСТ 8734"}
      - {D: 32.0, s: 4.0, note: "ГОСТ 8734"}
      - {D: 38.0, s: 5.0, note: "ГОСТ 8734"}
      - {D: 40.0, s: 4.0, note: "ГОСТ 8734"}
      - {D: 42.0, s: 6.0, note: "ГОСТ 8734"}
      - {D: 45.0, s: 5.0, note: "ГОСТ 8734"}
      - {D: 48.0, s: 5.0, note: "ГОСТ 8732-78"}
      - {D: 50.0, s: 6.0, note: "ГОСТ 8734"}
      - {D: 51.0, s: 10.0, note: "ГОСТ 8732-78"}
      - {D: 54.0, s: 8.0, note: "ГОСТ 8732-78"}
      - {D: 56.0, s: 8.0, note: "ГОСТ 8732-78"}
      - {D: 57.0, s: 8.0, note: "ГОСТ 8732"}
      - {D: 60.0, s: 5.0, note: "ГОСТ 8732-78"}
      - {D: 60.0, s: 6.0, note: "ГОСТ 8732-78"}
      - {D: 60.0, s: 8.0, note: "ГОСТ 8734"}
      - {D: 60.0, s: 10.0, note: "ГОСТ 8732-78"}
      - {D: 60.0, s: 14.0, note: "ГОСТ 8732-78"}
      - {D: 63.0, s: 8.0, note: "ГОСТ 8732-78"}
      - {D: 64.0, s: 8.0, note: "ГОСТ 8732-78"}
      - {D: 68.0, s: 8.0, note: "ГОСТ 8732-78"}
      - {D: 68.0, s: 14.0, note: "ГОСТ 8732-78"}
      - {D: 68.0, s: 16.0, note: "ГОСТ 8732-78"}
      - {D: 70.0, s: 7.0, note: "ГОСТ 8732-78"}
      - {D: 73.0, s: 5.0, note: "ГОСТ 8732-78"}
      - {D: 73.0, s: 7.0, note: "ГОСТ 8732-78"}
      - {D: 73.0, s: 10.0, note: "ГОСТ 8732-78"}
      - {D: 73.0, s: 12.0, note: "ГОСТ 8732"}
      - {D: 73.0, s: 16.0, note: "ГОСТ 8732-78"}
      - {D: 76.0, s: 6.0, note: "ГОСТ 8732-78"}
      - {D: 76.0, s: 8.0, note: "ГОСТ 8732-78"}
      - {D: 76.0, s: 10.0, note: "ГОСТ 8732"}
      - {D: 76.0, s: 14.0, note: "ГОСТ 8732-78"}
      - {D: 76.0, s: 18.0, note: "ГОСТ 8732-78"}
      - {D: 83.0, s: 11.0, note: "ГОСТ 8732-78"}
      - {D: 83.0, s: 12.0, note: "ГОСТ 8732"}
      - {D: 83.0, s: 16.0, note: "ГОСТ 8732"}
      - {D: 83.0, s: 19.0, note: "ГОСТ 8732"}
      - {D: 89.0, s: 16.0, note: "ГОСТ 8732"}
      - {D: 102.0, s: 14.0, note: "ГОСТ 8732"}
      - {D: 108.0, s: 16.0, note: "ГОСТ 8732"}
      - {D: 114.0, s: 18.0, note: "ГОСТ 8732"}
      - {D: 121.0, s: 20.0, note: "ГОСТ 8732"}
      - {D: 133.0, s: 16.0, note: "ГОСТ 8732"}
      - {D: 146.0, s: 22.0, note: "ГОСТ 8732"}
      - {D: 159.0, s: 20.0, note: "ГОСТ 8732"}
      - {D: 168.0, s: 25.0, note: "ГОСТ 8732"}
    bars: [6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 25, 26, 28, 30, 32, 34, 36, 38, 40, 42, 45, 48, 50, 52, 56, 60, 65, 70, 75, 80, 85, 90, 95, 100, 110, 120, 130, 140, 150, 160]       # ГОСТ 2590-2006; Ø50–75 — .12/.13/.14, наличие запросить (CP-85)
  40ХН2МА:                               # ходовые размеры: docs/Материалы-заготовки  для ГК.md
    tubes:
      - {D: 48.0, s: 12.0, note: "ГОСТ 8732, горячедеф."}
      - {D: 73.0, s: 14.0, note: "ГОСТ 8732, горячедеф."}
      - {D: 76.0, s: 10.0, note: "ГОСТ 8732, горячедеф."}
      - {D: 83.0, s: 16.0, note: "ГОСТ 8732, горячедеф."}
      - {D: 95.0, s: 10.0, note: "ГОСТ 8732, горячедеф."}
      - {D: 95.0, s: 24.0, note: "ГОСТ 8732, горячедеф."}
      - {D: 102.0, s: 22.0, note: "ГОСТ 8732, горячедеф."}
      - {D: 108.0, s: 16.0, note: "ГОСТ 8732, горячедеф."}
      - {D: 108.0, s: 25.0, note: "ГОСТ 8732, горячедеф."}
      - {D: 108.0, s: 28.0, note: "ГОСТ 8732, горячедеф."}
      - {D: 121.0, s: 20.0, note: "ГОСТ 8732, горячедеф."}
      - {D: 121.0, s: 28.0, note: "ГОСТ 8732, горячедеф."}
      - {D: 146.0, s: 25.0, note: "ГОСТ 8732, горячедеф."}
      - {D: 146.0, s: 28.0, note: "ГОСТ 8732, горячедеф."}
      - {D: 178.0, s: 35.0, note: "ГОСТ 8732, горячедеф."}
  38Х2Н2МА:
    tubes:
      - {D: 38.0, s: 2.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 89.0, s: 22.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 92.0, s: 22.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 95.0, s: 20.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 108.0, s: 12.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 114.0, s: 16.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 127.0, s: 20.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 152.0, s: 39.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 180.0, s: 25.0, note: "ГОСТ 8732-78, горячедеф."}
  35ХМ:                                  # CP-86: кандидат .02C (L3/L4); наличие не подтверждено — размеры закомментированы
    tubes: # https://bvb-alyans.ru/, https://mc.ru/, https://cvet-met.com/, https://metatorg.ru/
      - {D: 70.0, s: 4.0, note: "ГОСТ 8734-75, холоднодеф"}
      - {D: 76.0, s: 5.0, note: "ГОСТ 8734-75, холоднодеф"}
      - {D: 76.0, s: 6.0, note: "ГОСТ 8732-78, горячедеф"}
      - {D: 83.0, s: 4.0, note: "ГОСТ 8734-75, холоднодеф"}
      - {D: 89.0, s: 8.0, note: "ГОСТ 8732-78, горячедеф"}
      - {D: 108.0, s: 5.0, note: "ГОСТ 8734-75, холоднодеф"}
      - {D: 108.0, s: 10.0, note: "ГОСТ 8732-78, горячедеф"}
      - {D: 114.0, s: 8.0, note: "ГОСТ 8732-78, горячедеф"}
  30Х3МФ:                                # CP-86: альтернатива 38Х2МЮА для L1 и трепанации; круг в продаже — размер подтвердить
    bars: [20, 30, 40, 60, 80, 100, 110]                       # ГОСТ 2590
  08пс:
    sheets: [0.5, 0.55, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.4, 1.5, 1.8, 2.0, 2.5, 3.0]    # ГОСТ 19904; в .02 не допущен (TECH-01)
  30ХГСА:                              # лист для .02, маршрут weld: 1.5 мм найден (steelmart.ru, vesta-metall.ru); также brinelle-spb.ru, td-artstal.ru (CP-85)
    sheets: [0.5, 0.6, 0.7, 0.8, 1.0, 1.2, 1.5, 1.7, 2.0, 3.0, 3.5, 5.0]
    tubes:
      - {D: 32.0, s: 8.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 34.0, s: 8.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 36.0, s: 8.0, note: "ГОСТ 8732-78, горячедеф."}
#     - {D: 40.0, s: 2.0, note: "ГОСТ 8732-78, горячедеф."}   # CP-85: стенка 2 мм для г/д сомнительна — уточнить (х/д ГОСТ 8734?)
      - {D: 40.0, s: 6.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 40.0, s: 8.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 42.0, s: 4.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 42.0, s: 8.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 42.0, s: 8.5, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 42.0, s: 9.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 45.0, s: 5.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 45.0, s: 9.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 45.0, s: 10.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 48.0, s: 5.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 48.0, s: 8.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 50.0, s: 6.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 50.0, s: 8.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 53.0, s: 10.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 54.0, s: 12.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 57.0, s: 8.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 57.0, s: 12.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 60.0, s: 10.0, note: "ГОСТ 8732-78, горячедеф."}
#     - {D: 63.0, s: 1.0, note: "ГОСТ 8732-78, горячедеф."}   # CP-85: г/д 63×1 вне сортамента — опечатка? уточнить у поставщика
      - {D: 70.0, s: 7.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 70.0, s: 10.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 70.0, s: 12.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 73.0, s: 5.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 73.0, s: 7.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 73.0, s: 9.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 73.0, s: 13.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 73.0, s: 18.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 76.0, s: 15.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 76.0, s: 16.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 80.0, s: 5.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 80.0, s: 12.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 83.0, s: 14.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 83.0, s: 16.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 83.0, s: 18.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 83.0, s: 19.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 83.0, s: 20.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 85.0, s: 12.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 89.0, s: 9.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 89.0, s: 12.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 89.0, s: 14.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 89.0, s: 18.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 89.0, s: 20.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 89.0, s: 22.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 95.0, s: 20.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 95.0, s: 22.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 100.0, s: 6.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 102.0, s: 9.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 102.0, s: 17.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 102.0, s: 20.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 102.0, s: 22.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 108.0, s: 10.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 108.0, s: 12.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 108.0, s: 14.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 108.0, s: 15.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 108.0, s: 16.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 108.0, s: 17.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 108.0, s: 18.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 108.0, s: 22.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 108.0, s: 28.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 110.0, s: 7.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 114.0, s: 8.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 114.0, s: 10.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 114.0, s: 13.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 114.0, s: 14.0, note: "ГОСТ 8732-78, горячедеф."}
      - {D: 114.0, s: 16.0, note: "ГОСТ 8732-78, горячедеф."}


  38Х2МЮА:                             # пруток и поковки (листа нет); стакан L1 — пруток (Д-68)
    bars: [20, 25, 30, 36, 40, 45, 50, 56, 60, 65, 70, 75, 80, 90, 100, 110, 120]   # ГОСТ 2590 — проверить у поставщика
  60С2А:                              # лента ГОСТ 2283 — вписать найденные толщины - https://brinelle-spb.ru
    sheets: [2.0]
  #"40":                               # лист ГОСТ 16523 — вписать найденные толщины
  #  sheets: []
  #"50":
  #  sheets: []
===== END FILE =====

### Код расчёта

===== FILE: egm/ptk_design.py (строки 1–699) =====
"""Шаг 2 — проработка выбранного исполнения ПТК (Д-48, CP-38).

Вход: specs/ptk_design_input.yaml → designs[]; исполнение шага 1 — ptk_configs.yaml.
Выход: ptk_designs.yaml (комментированный YAML, design_doc) и SPEC-11_PTK_DESIGN.md; детали проработки — <ID>.03<вар>-<name>.
Исполнение задаётся полным ID или префиксом без хэша (+ bearing, gen): хэш меняется
с геометрией шага 1 (Д-80), а проработка остаётся привязанной (Д-51).
Считается: момент входного вала и доля эксцентрика, кручение вала (полый — 1 − β⁴),
шпонка (смятие), стенки эксцентрика, балансировка свёрлами из списка
(ptk_parts.eccentric), масса и момент инерции пакета на входе. Формулы — THEORY.
"""
import math
import re
from types import SimpleNamespace

from egm import config, ptk_layout, ptk_parts, shafts

LINKS = ("key", "flat", "integral", "spline", "press")
CALC = ("key", "flat", "integral")             # spline, press — только кручение вала
NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")
THEORY = (
    "Момент входного вала T_вх = M/(u·eta): M — допускаемый выходной момент SPEC-10, "
    "eta — оценка КПД из входа (η не считается, OQ-08). Доля эксцентрика T_э = ecc_share·T_вх: "
    "ряды сдвинуты по фазе, нагрузка между ними распределена неравномерно (OQ-15).\n\n"
    "Кручение вала: τ = 16·T_вх/(π·d_t³·(1 − β⁴)), d_t = d − t1 при шпонке (ослабление пазом), "
    "β = d_отв/d_t; d_req — диаметр, при котором τ = [τ]. Изгиб не считается, его покрывает "
    "запас S в [τ] = min(τ₋₁/(K_τ·S), 0.58·σт/S_т); [σсм] = min(σт вала, .03, шпонки)/S_см; "
    "марка .15 — первая проходящая из products.15.material (Д-110, egm/shafts.py, SPEC-12).\n\n"
    "Шпонка призматическая, исп. A (DIN 6885 / ГОСТ 23360, keys.table в specs/shafts.yaml, "
    "Д-109): "
    "σ_см = 2·T_э/(d·(h − t1)·l_p), l_p = t − b, t — толщина эксцентрика.\n\n"
    "Стенки эксцентрика: у паза — Y(key_angle) − d/2 − t2, напротив эксцентриситета — "
    "D_э/2 − a_ω − d/2; обе ≥ ecc_wall_min.\n\n"
    "Балансировка — Д-36, Д-46, диаметры только из balance.drills. Масса и момент инерции на "
    "входе: эксцентрики (диск со смещением a_ω, минус отверстия), подшипники как кольца, "
    "обегающие ось на a_ω (оценка сверху), вал длиной B пакета; тела не учитываются. "
    "J вых = J вх·u² — то же, приведённое к выходу.")


def select(configs, d):
    """Исполнение шага 1 по id (полный | префикс) и bearing, gen -> (cfg | None, причина)."""
    c = [r for r in configs if r.get("id", "").startswith(d["id"]) and r.get("ok") and r.get("ecc")]
    for k in ("bearing", "gen"):
        if d.get(k) is not None:
            c = [r for r in c if (r.get(k) or "") == d[k]]
    if len(c) == 1:
        return c[0], ""
    if not c:
        f = "".join(f", {k} = {d[k]}" for k in ("bearing", "gen") if d.get(k) is not None)
        return None, f"нет реализуемого исполнения {d['id']}{f} в ptk_configs.yaml (SPEC-10)"
    return None, f"id {d['id']} неоднозначен: {[r['id'] for r in c]} — уточнить bearing / gen"


def _mass(cfg, ecc, dsh, bore, rho, rows):
    """Масса, г, и момент инерции на входе, кг·м²."""
    De, t, a, b = ecc["De"], ecc["t"], ecc["a"], ecc["bal"]
    q = rho * t * math.pi / 4
    m_e = q * (De ** 2 - dsh ** 2 - b["n"] * b["d"] ** 2)
    J_e = q * De ** 2 * (De ** 2 / 8 + a ** 2) - q * dsh ** 4 / 8
    J_e -= sum(q * b["d"] ** 2 * (b["d"] ** 2 / 8 + x * x + y * y) for x, y in b["holes"])
    brg = cfg["geom"].get("bearing") if cfg["gen"] == "bearing" else None
    m_b = ecc["m_brg_g"] if brg else 0.0
    J_b = m_b * ((brg["D"] ** 2 + brg["d"] ** 2) / 8 + a ** 2) if brg else 0.0
    m_s = rho * math.pi / 4 * (dsh ** 2 - bore ** 2) * float(cfg["width"])
    J = rows * (J_e + J_b) + m_s * (dsh ** 2 + bore ** 2) / 8
    return {"ecc_g": round(m_e, 1), "brg_g": round(m_b, 1), "shaft_g": round(m_s, 1),
            "sum_g": round(rows * (m_e + m_b) + m_s, 1), "J_in": float(f"{J * 1e-9:.3e}"),
            "J_out": float(f"{J * 1e-9 * int(cfg['u']) ** 2:.3e}")}


def design(cfg, d, lim, keys, extra=None, mat_src=None):
    """Проработка одного исполнения -> запись ptk_designs.json.

    d["shaft"] — разрешённый словарь вала (shafts.resolve); mat_src — (materials, products,
    stock) для подбора марки .15 и допусков (Д-110); None — допуски DEFAULTS."""
    name, sh, bal = d["name"], d["shaft"], d.get("balance", {})
    err, warn = [], []
    u, M = int(cfg["u"]), float(cfg.get("M") or 0.0)
    eta, share = float(d.get("eta", 0.8)), float(d.get("ecc_share", 0.5))
    if M <= 0:
        warn.append("M исполнения = 0 — вал и шпонка не нагружены, проверки формальные")
    T_in = M / (u * eta)
    T_e = T_in * share
    link, dsh, bore = sh.get("link", "key"), float(sh["d"]), float(sh.get("bore", 0.0))
    key = next((k for k in keys if dsh <= k["d_max"] + 1e-9), None) if link == "key" else None
    if link == "key" and key is None:
        err.append(f"шпонка: в keys нет размера для вала Ø{dsh:g}")
    if link not in CALC:
        warn.append(f"соединение {link}: расчёт не реализован, проверено только кручение вала")
    if link == "flat":
        warn.append("лыска: смятие не считается, в CAD отверстие круглое")
    if link == "integral":
        warn.append("вал-эксцентрик заодно: CAD детали — CP-05, на чертеже .03 — отверстие вала")
    t1 = key["t1"] if key else 0.0
    d_t, wmin = dsh - t1, float(sh.get("wall_min", 1.5))
    wall = (dsh - bore) / 2 - t1
    if bore and wall < wmin - 1e-9:
        err.append(f"вал: стенка {wall:.2f} < wall_min {wmin:g} мм "
                   f"(Ø{dsh:g}, отв. {bore:g}, t1 {t1:g})")
    k4 = max(1.0 - (bore / d_t) ** 4, 1e-6)
    tau = 16 * T_in * 1e3 / (math.pi * d_t ** 3 * k4)
    i_tau = len(err)          # ошибка τ — на прежнем месте списка; [τ] известен после σсм (Д-110)
    over = {"shaft_d_min": dsh, "shaft_key_b": key["b"] if key else 0.0,
            "shaft_key_t2": key["t2"] if key else 0.0,
            "key_angle": float(d.get("key_angle", lim.key_angle)),
            "bal_n_max": int(bal.get("n_max", lim.bal_n_max)),
            "bal_wall": float(bal.get("wall", lim.bal_wall)),
            "bal_drills": sorted(float(x) for x in bal.get("drills", [])) or None}
    L = SimpleNamespace(**{**vars(lim), **over})
    g = cfg["geom"]
    ecc = ptk_parts.eccentric(int(cfg["n"]), cfg["a_w"], cfg["Drol"], g["roller"], g.get("bearing"),
                              cfg["phasing"], L, cfg["gen"], cfg["R_sum"])
    warn += [w for w in ecc.pop("warnings") if "у паза" not in w]
    wb, kw = ecc["De"] / 2 - ecc["a"] - dsh / 2, min(x["key_wall"] for x in ecc["rows"])
    if min(wb, kw) < lim.ecc_wall_min - 1e-9:
        err.append(f"эксцентрик: стенка {min(wb, kw):.2f} < ecc_wall_min {lim.ecc_wall_min:g} мм "
                   f"(напротив эксцентриситета {wb:.2f}, у паза {kw:.2f})")
    lk, sig = {"type": link, "sigma": None}, None
    if key:
        lp, kh = ecc["t"] - key["b"], key["h"] - key["t1"]
        sig = 2 * T_e * 1e3 / (dsh * kh * lp) if lp > 0 else 1e9
    mats, prods, stock = mat_src or (None, None, None)
    mat = shafts.pick(sh, tau, sig, mats, prods, stock)    # Д-110: марка .15 и допуски из материала
    ta, sa = mat["tau_allow"], mat["sigma_crush"]
    d_req = (16 * T_in * 1e3 / (math.pi * ta * k4)) ** (1 / 3) + t1
    if tau > ta + 1e-9:
        err.insert(i_tau, f"вал Ø{dsh:g}: τ = {tau:.1f} > [τ] = {ta:g} МПа "
                          f"({mat['tau_basis']}, {mat['grade'] or 'без марки'}) — нужен d ≥ {d_req:.1f} мм")
    err += mat["errors"]
    warn += mat["warnings"]
    if key:
        lk.update(b=key["b"], h=key["h"], t1=key["t1"], t2=key["t2"], lp=lp,
                  sigma=round(sig, 1), sigma_allow=sa)
        if sig > sa + 1e-9:
            err.append(f"шпонка {key['b']:g}×{key['h']:g}: σ см = {sig:.0f} > [σ] = {sa:g} МПа "
                       f"(l_p = {lp:g} мм)")
    lay = None
    if extra is not None:
        lay, le, lw = ptk_layout.layout(cfg, {**d, "_keys": keys}, ecc, dsh, L.row_gap,
                                        **extra)   # CP-90: шпонки выходного вала — та же keys.table
        err += le
        warn += lw
    parts = [{**p, "base": p["id"], "id": f"{p['id']}-{name}"}
             for p in ptk_parts.parts(cfg["id"], ecc) if p["id"].split(".", 1)[1].startswith("03")]
    return {"id": cfg["id"], "name": name, "ok": not err, "errors": err, "warnings": warn,
            "input": d, "layout": lay, "keys": keys,       # CP-90: шпонки выхода — для egm.cad
            "shaft": {"d": dsh, "bore": bore, "link": link, "eta": eta, "ecc_share": share, "M": M,
                      "T_in": round(T_in, 3), "T_e": round(T_e, 3), "tau": round(tau, 1),
                      "tau_allow": ta, "d_req": round(d_req, 2),
                      "tau_basis": mat["tau_basis"], "sigma_crush": sa,
                      "crush_basis": mat["crush_basis"], "grade": mat["grade"],
                      "state": mat["state"], "props": mat["props"], "blank": mat["blank"],
                      "bore_max": shafts.bore_max(dsh, t1, T_in, ta, wmin),
                      "rejected": mat["rejected"]},
            "link": lk, "ecc": ecc, "mass": _mass(cfg, ecc, dsh, bore, L.rho * 1e-6,
                                                  len(cfg["phasing"])),
            "parts": parts}


def keys_table(app=None):
    """Таблица шпонок из номенклатуры валов (Д-109, OQ-35 решён).

    Источник — products.SH.configs.shafts (configs/application.yaml → specs/shafts.yaml)
    → keys.table. Одна таблица на входной вал и на выходной вал в ступице (CP-90);
    во входе проработки её нет: паз — свойство сечения вала, а не проработки.
    """
    app = config.load_app() if app is None else app
    rel = config.cfg_file(app, "products.SH.configs.shafts")
    tbl = ((config.load(rel) or {}).get("keys") or {}).get("table")
    if not tbl:
        raise ValueError(f"{rel.relative_to(config.ROOT)}: нет keys.table — таблица "
                         f"шпонок живёт в номенклатуре валов (Д-109)")
    return tbl


def _mats():
    """specs/materials.yaml через configs.materials (Д-79) или None — допуски DEFAULTS."""
    try:
        p = config.cfg_file(config.load_app(), "configs.materials")
    except (KeyError, OSError, ValueError):
        return None
    return config.load(p) if p.exists() else None


def run(inp, configs, lim, extra=None, keys=None, nomen=None, mats=None):
    """ptk_design_input.yaml -> [запись]; ошибка входа — ValueError (в checks.md).

    keys — таблица шпонок; None — читается из номенклатуры валов (Д-109).
    nomen — specs/shafts.yaml; None — читается, если вал задан ID (Д-107).
    mats — specs/materials.yaml; None при extra — читается (подбор .15, Д-110).
    """
    if inp.get("keys"):
        raise ValueError("ptk_design_input: ключ keys перенесён в specs/shafts.yaml → "
                         "keys.table (Д-109) — во входе проработки его быть не должно")
    keys = sorted(keys if keys is not None else keys_table(), key=lambda k: k["d_max"])
    if mats is None and extra is not None:
        mats = _mats()
    src = (mats, (extra or {}).get("prods"), (extra or {}).get("stock"))
    out, names = [], set()
    for d in inp.get("designs", []):
        name = str(d.get("name", ""))
        if not NAME_RE.match(name) or name in names:
            raise ValueError(f"designs: имя «{name}» — латиница, цифры, _, без «-», уникальное (Д-48)")
        sp = d.get("shaft") or {}
        if "id" in sp and nomen is None:
            nomen = shafts.load()
        cands, sw = shafts.resolve(sp, nomen, f"designs.{name}")
        for _, sh in cands:
            if sh.get("link", "key") not in LINKS:
                raise ValueError(f"designs.{name}.shaft.link: {sh.get('link')} — допустимы {LINKS}")
        names.add(name)
        cfg, why = select(configs, d)
        if not cfg:
            out.append({"id": d["id"], "name": name, "ok": False, "errors": [why],
                        "warnings": sw, "input": d})
            continue
        r = None
        for sid, sh in cands:          # Д-110: список ID — наименьшая проходящая (как layout, Д-100)
            r = design(cfg, {**d, "shaft": sh}, lim, keys, extra, src)
            r["input"] = {**d, "shaft_id": sid or ""}
            if r["ok"]:
                break
        if len(cands) > 1:
            sw.append(f"shaft.id: перебраны {[s for s, _ in cands]}, взят {r['input']['shaft_id']}"
                      + ("" if r["ok"] else " — не прошёл ни один, показан наибольший"))
        r["warnings"] = sw + r["warnings"]
        out.append(r)
    return out


def find(designs, cid, name):
    """Запись ptk_designs.json по ID исполнения (детали) и имени проработки."""
    base = cid.split(".")[0]
    for r in designs:
        if r["id"] == base and r["name"] == name and r.get("ecc"):
            return r
    raise KeyError(f"проработка {name} для {base} не найдена в specs/ptk_designs.yaml — "
                   f"проверить ptk_design_input.yaml, python main.py --publish (Д-48)")


def pick(designs, arg, name=None):
    """Проработка по --design или суффиксу ID детали (<ID>.03B-K8) -> запись | None."""
    tail = arg.partition(".")[2]
    if not name and "-" in tail:
        name = tail.rsplit("-", 1)[1]
    return find(designs, arg, name) if name else None


def apply(cfg, des):
    """Исполнение шага 1 с эксцентриками и валом проработки (для egm.cad); cfg не меняется."""
    if des is None:
        return cfg
    g, lay = cfg["geom"], des.get("layout") or {}
    extra = lay.get("cad_parts") or []                 # CP-45: .02A|B, .07A/B, .11 конструктива
    drop = {"03"} | {p["id"].split(".", 1)[1][:2] for p in extra}
    keep = [p for p in cfg["parts"] if p["id"].split(".", 1)[1][:2] not in drop]
    return {**cfg, "ecc": des["ecc"], "parts": keep + des["parts"] + extra, "layout": lay or None,
            "geom": {**g, "limits": {**g["limits"], "shaft_d_min": des["shaft"]["d"]}}}


def md(res):
    """Формирование разделов SPEC-11 в новом порядке.

    Структура:
    1. Сводка (транспонированная таблица параметров × проработок)
    2. Детали проработки (таблица)
    3. Номенклатура (01–14)
    4. Конструктивы L1–L4 (справочный блок)
    5. Проработка K8 — весь блок данных по проработке:
       - Конструктив (выбранный)
       - Состав (номенклатура деталей)
       - Подшипники и опоры
       - Соединение .02–.12
       - Выход: вал в ступице
       - Заготовка .02
       - Балансировка и масса
       - Оснастка
       - Ошибки и предупреждения (внутри блока проработки)
    6. Проработка K10 — аналогично
    7. Расчёт (теория)

    Примечание: ошибки и предупреждения выводятся только внутри блоков
    проработок (К8, К10). Общие разделы "Ошибки"/"Предупреждения" в конце
    убраны — они дублировали информацию.
    """
    P = ["| Деталь | Как на шаге 1 | Паз, ° | Ряды |", "|---|---|---|---|"]

    for r in res:
        s = r.get("shaft")
        if s:
            P += [f"| {p['id']} | {p['base']} | {p['key_angle']:g} | "
                  f"{', '.join(str(x) for x in p['rows'])} |" for p in r["parts"]]

    # Генерация блоков по проработкам
    workpieces = []
    for r in res:
        if r.get("shaft"):
            workpieces.append(_md_workpiece(r))

    # Блок конструктивов L1–L4
    layouts_block = ptk_layout.md_layouts_info()

    # Блок номенклатуры
    nomenclature_block = ptk_layout.md_nomenclature()

    return {
        "summary": _md_summary(res) if res else "нет проработок",
        "parts": "\n".join(P) if len(P) > 2 else "нет",
        "workpieces": "\n\n".join(workpieces) if workpieces else "нет",
        "layouts": layouts_block,
        "nomenclature": nomenclature_block,
        "theory": THEORY,
        "n_ok": sum(r["ok"] for r in res),
        "n_all": len(res)
    }


def _md_workpiece(r):
    """Генерация полного блока данных по одной проработке (вертикальный формат)."""
    lines = []
    name = r["name"]
    ok_mark = "✓ OK" if r["ok"] else "✗ ОШИБКА"

    lines.append(f"### Проработка {name} — {ok_mark}")
    lines.append("")
    lines.append(f"**ID:** {r['id']}")
    lines.append("")

    # --- Конструктив ---
    lay = r.get("layout")
    if lay:
        lines.append("#### Конструктив")
        lines.append("")
        code = lay.get("code", "—")
        title = lay.get("name", "—")
        lines.append(f"Выбран: **{code}** — {title}")
        lines.append("")

        # Состав — список деталей в этом конструктиве
        parts_dict = lay.get("parts", {})
        var = lay.get("var", {})
        if parts_dict:
            lines.append("| Позиция | Обозначение | Наименование |")
            lines.append("|---|---|---|")
            for pos in sorted(parts_dict.keys(), key=lambda x: int(x) if x.isdigit() else 0):
                det = parts_dict[pos]
                var_name = f"{det}{var.get(pos, '')}"
                # Получаем расшифровку из номенклатуры
                desc = ptk_layout.get_nomenclature_desc(pos)
                lines.append(f"| .{pos} | {var_name} | {desc} |")
            lines.append("")

        # Длина
        length = lay.get("length")
        if length is not None:
            lines.append(f"**Длина по оси:** {length:g} мм")
            lines.append("")

    # --- Подшипники и опоры ---
    if lay:
        b09 = lay.get("b09")
        b10 = lay.get("b10")
        if b09 or b10:
            lines.append("#### Подшипники и опоры (.09 — подшипник выхода, .10 — подшипник генератора)")
            lines.append("")
            lines.append("| Подшипник | Обозначение | d×D×B, мм | C, кН | da, мм |")
            lines.append("|---|---|---|---|---|")
            if b09:
                lines.append(f"| .09 выход | {b09.get('id', '—')} | {b09.get('d', '—')}×{b09.get('D', '—')}×{b09.get('B', '—')} | {b09.get('C', '—')} | {b09.get('da', '—')} |")
            if b10:
                lines.append(f"| .10 вход | {b10.get('id', '—')} | {b10.get('d', '—')}×{b10.get('D', '—')}×{b10.get('B', '—')} | {b10.get('C', '—')} | {b10.get('da', '—')} |")
            lines.append("")

            # Доп. данные опор
            tau_hub = lay.get("tau_hub")
            if tau_hub is not None:
                tau_allow = lay.get("tau_allow", 25)
                lines.append(f"**τ ступицы:** {tau_hub:g} / [{tau_allow}] МПа — касательное напряжение кручения ступицы")
            r11 = lay.get("r11")
            if r11:
                lines.append(f"**Кольцо .11:** {r11.get('n', 0)} × {r11.get('h', 0):g} мм")
            covers = lay.get("covers")
            if covers:
                tA = covers.get("tA")
                tB = covers.get("tB")
                if tA is not None and tB is not None:
                    lines.append(f"**Крышки:** .07A (вход) = {tA:g} мм, .07B (выход) = {tB:g} мм")
            cup = lay.get("cup")
            if cup:
                z_in = cup.get("z_in")
                t = cup.get("t")
                hub_d = cup.get("hub_d")
                hub_l = cup.get("hub_l")
                if z_in is not None and t is not None:
                    txt = f"**Дно .02:** z = {z_in:g}, t = {t:g} мм"
                    if hub_d and hub_l:
                        txt += f"; ступица Ø{hub_d:g}×{hub_l:g} мм"
                    lines.append(txt)
            lines.append("")

            # --- Стопорные кольца ГОСТ 13942 / 13943 ---
            grooves = (lay.get("output") or {}).get("grooves")
            if grooves:
                ext = grooves.get("ext")
                int_ = grooves.get("int")
                if ext or int_:
                    lines.append("**Стопорные кольца .09 (ГОСТ 13942 / 13943):**")
                    if ext:
                        std = ext.get("std", "ГОСТ 13942-86")
                        s = ext.get("s", "—")
                        m = ext.get("m", "—")
                        d2 = ext.get("d2", "—")
                        d9 = b09.get("d", "—") if b09 else "—"
                        lines.append(f"- rings_ext (вал): d = {d9} → {std}, s = {s} мм, m = {m} мм, d2 = {d2} мм")
                    if int_:
                        std = int_.get("std", "ГОСТ 13943-86")
                        s = int_.get("s", "—")
                        m = int_.get("m", "—")
                        d2 = int_.get("d2", "—")
                        D9 = b09.get("D", "—") if b09 else "—"
                        lines.append(f"- rings_int (корпус): D = {D9} → {std}, s = {s} мм, m = {m} мм, d2 = {d2} мм")
                    # Кольцо .11 уже выведено выше
            lines.append("")

    # --- Соединение .02–.12 ---
    if lay and lay.get("join"):
        join = lay["join"]
        pick = join.get("pick")
        if pick:
            lines.append("#### Соединение .02–.12 (Сепаратор — Ступица выхода)")
            lines.append("")
            scheme = pick.get("scheme", "—")
            lines.append(f"**Схема:** {scheme}")

            pins = pick.get("pins")
            if pins:
                n = pins.get("n", 0)
                d = pins.get("d", 0)
                l = pins.get("l", 0)
                tau = pins.get("tau")
                sig_wall = pins.get("sig_wall")
                sig_hub = pins.get("sig_hub")
                tau_edge = pins.get("tau_edge")
                des = pins.get("des", "")
                lines.append(f"**Штифты:** {n} × Ø{d:g} × {l:g} мм — {des}")
                if tau is not None:
                    lines.append(f"  - τ среза штифта: {tau:g} МПа — касательное напряжение среза штифта")
                if sig_wall is not None:
                    lines.append(f"  - σсм стенки .02: {sig_wall:g} МПа — смятие стенки сепаратора под штифтом")
                if sig_hub is not None:
                    lines.append(f"  - σсм ступицы .12: {sig_hub:g} МПа — смятие ступицы под штифтом")
                if tau_edge is not None:
                    lines.append(f"  - τ среза к торцу: {tau_edge:g} МПа — срез перемычки от штифта до торца")
            lines.append("")

    # --- Выход: вал в ступице ---
    if lay and lay.get("output"):
        out = lay["output"]
        lines.append("#### Выход: вал в ступице")
        lines.append("")
        d_o = out.get("d")
        if d_o:
            lines.append(f"**Ø выходного вала:** {d_o:g} мм")
        key = out.get("key")
        if key:
            b, h, l_key = key.get("b", 0), key.get("h", 0), out.get("l_key", 0)
            lines.append(f"**Шпонка:** {b:g}×{h:g}×{l_key:g} мм")
        tau = out.get("tau")
        if tau is not None:
            tau_allow = out.get("tau_allow", 25)
            lines.append(f"**τ вала:** {tau:g} / [{tau_allow}] МПа")
        flange = out.get("flange")
        if flange:
            fl_txt = out.get("fl_txt", "")
            if fl_txt:
                lines.append(f"**Фланец:** {fl_txt}")
        hub_l = out.get("hub_l")
        if hub_l is not None:
            hub_by = out.get("hub_by", "")
            lines.append(f"**Длина ступицы:** {hub_l:g} мм ({hub_by})")
        rh = out.get("r_h")
        if rh is not None:
            lines.append(f"**r_h .09 (da/2):** {rh:g} мм")
        lines.append("")

    # --- Заготовка .02 ---
    if lay and lay.get("blank"):
        bl = lay["blank"]
        lines.append("#### Заготовка .02")
        lines.append("")
        mat = bl.get("material")
        if mat:
            lines.append(f"**Материал:** {mat}")
        tube = bl.get("tube")
        if tube:
            D = tube.get("D")
            s = tube.get("s")
            note = tube.get("note", "")
            txt = f"**Труба:** Ø{D:g} × {s:g} мм"
            if note:
                txt += f" ({note})"
            lines.append(txt)
        alt = bl.get("alt")
        if alt:
            lines.append(f"**Альтернативы:** {', '.join(alt)}")
        lines.append("")

    # --- Балансировка и масса ---
    ecc = r.get("ecc", {})
    bal = ecc.get("bal", {})
    mass = r.get("mass", {})
    if bal or mass:
        lines.append("#### Балансировка и масса")
        lines.append("")
        bal_n = bal.get("n", 0)
        bal_d = bal.get("d", 0)
        bal_r = bal.get("r", 0)
        if bal_n:
            lines.append(f"**Балансировка:** {bal_n} × Ø{bal_d:g} мм, радиус {bal_r:g} мм")
        res_u = bal.get("res")
        if res_u is not None:
            lines.append(f"**Остаточный дисбаланс:** {res_u:g} г·мм")
        lines.append(f"**m пакета:** {mass.get('sum_g', 0):g} г")
        lines.append(f"**J вх:** {mass.get('J_in', 0):.2e} кг·м²")
        lines.append(f"**J вых:** {mass.get('J_out', 0):.2e} кг·м²")
        lines.append("")

    # --- Оснастка ---
    if lay and lay.get("tooling"):
        tooling = lay["tooling"]
        lines.append("#### Оснастка (Д-81)")
        lines.append("")
        lines.append("| Операция | Деталь | Размер | Маршрут |")
        lines.append("|---|---|---|---|")
        for t in tooling:
            fx = t.get("fx", "—")
            part = t.get("part", "—")
            size = t.get("size", "—")
            route = t.get("route", "—")
            lines.append(f"| {fx} | {part} | {size} | {route} |")
        lines.append("")

    # --- Ошибки и предупреждения ---
    if r.get("errors"):
        lines.append("##### Ошибки")
        lines.append("")
        for e in r["errors"]:
            lines.append(f"- {e}")
        lines.append("")

    if r.get("warnings"):
        lines.append("##### Предупреждения")
        lines.append("")
        for w in r["warnings"]:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)


def _md_summary(res):
    """Транспонированная таблица «Сводка»: параметры как строки, проработки как колонки.
    Колонка «Описание» содержит расшифровку каждого параметра.
    """
    names = [r["name"] for r in res if r.get("shaft")]
    if not names:
        return "нет проработок"

    # Расшифровки параметров
    DESCR = {
        "ID": "ID исполнения шага 1 (SPEC-10).",
        "Вал d": "Ø входного вала, мм (расчёт кручения, шпонка).",
        "Соединение .03–вал": "Тип и размер: шпонка b×h / лыска / вал-эксцентрик.",
        "M выходной": "M выходной, Н·м — допускаемый момент из SPEC-10.",
        "T вх / T э": "T вх — момент на входе, Н·м; T э — доля на один эксцентрик, Н·м.",
        "τ кручения": "τ вала, МПа — кручение с ослаблением шпоночным пазом.",
        "σсм шпонки": "σсм шпонки, МПа — смятие рабочей высоты паза.",
        "Балансировка": "Балансировка: число отверстий × Ø, радиус r (Д-36, Д-46).",
        "Остат. дисб.": "Остаточный дисбаланс после балансировки, г·мм.",
        "m пакета": "m пакета, г — суммарная масса эксцентриков, подшипников и вала.",
        "J вх": "J вх, кг·м² — момент инерции пакета на входе (приведённый к выходу: J вых = J вх·u²).",
        "Итог": "✓ — все проверки пройдены; ✗ — есть ошибки (не проходят вал/шпонка/стенка).",
    }

    H = "| Параметр | " + " | ".join(names) + " | Описание |"
    R = "|---" * (len(names) + 2) + "|"

    def _ok(r):
        return "✓" if r["ok"] else "✗"

    params = {}
    for r in res:
        s = r.get("shaft")
        if not s:
            continue
        k = r["link"]
        b = r["ecc"]["bal"]

        lk = k["type"]
        if k.get("b"):
            lk = f"шпонка {k['b']:g}×{k['h']:g}"
        elif k.get("type") in ("flat",):
            lk = "лыска"
        elif k.get("type") in ("integral",):
            lk = "вал-эксцентрик"

        bal = f"{b['n']}×Ø{b['d']:g} r {b['r']:g}" if b["n"] else "нет"

        params.setdefault("ID", {})[r["name"]] = r["id"]
        params.setdefault("Вал d", {})[r["name"]] = f"Ø{s['d']:g} мм" if s["d"] else "—"
        params.setdefault("Соединение .03–вал", {})[r["name"]] = lk
        params.setdefault("M выходной", {})[r["name"]] = f"{s['M']:g} Н·м"
        params.setdefault("T вх / T э", {})[r["name"]] = f"{s['T_in']:g} / {s['T_e']:g} Н·м"
        params.setdefault("τ кручения", {})[r["name"]] = f"{s['tau']:g} / {s['tau_allow']:g} МПа"
        params.setdefault("σсм шпонки", {})[r["name"]] = (
            f"{k['sigma']:g} / {k['sigma_allow']:g} МПа" if k.get("sigma") is not None else "—"
        )
        params.setdefault("Балансировка", {})[r["name"]] = bal
        params.setdefault("Остат. дисб.", {})[r["name"]] = f"{b['res']:g} г·мм"
        params.setdefault("m пакета", {})[r["name"]] = f"{r['mass']['sum_g']:g} г"
        params.setdefault("J вх", {})[r["name"]] = f"{r['mass']['J_in']:.2e} кг·м²"
        params.setdefault("Итог", {})[r["name"]] = _ok(r)

    out = [H, R]
    for param, vals in params.items():
        cells = " | ".join(f"{vals.get(n, '—')}" for n in names)
        desc = DESCR.get(param, "")
        out.append(f"| {param} | {cells} | {desc} |")

    return "\n".join(out)


def self_test():
    """Выбор по префиксу, вал Ø8 не проходит по τ, Ø10 проходит; шпонка, детали, cad-ID."""
    lim = SimpleNamespace(sep_gap=0.05, row_gap=1.0, rho=7850.0, brg_mass_k=0.35,
                          shaft_d_min=6.0, shaft_key_b=2.0, shaft_key_t2=1.0, bal_wall=1.0,
                          bal_n_max=3, bal_d_min=1.0, bal_d_step=0.1, ecc_wall_min=1.0,
                          key_angle=45.0, groove_f=0.52)
    ph = [{"row": k + 1, "phi": p, "s": -p} for k, p in enumerate((0, 90, 180, 270))]
    base = {"u": 50, "n": 50, "a_w": 0.4, "Drol": 2.0, "R_sum": 33.5, "M": 100.0, "width": 33.0,
            "ok": True, "ecc": {"t": 7.0}, "phasing": ph,
            "parts": [{"id": "PTK-T-X-AAAAAA.01A", "rows": [1, 2, 3, 4]}],
            "geom": {"roller": {"type": "roller", "d": 2.0, "l": 4.2},
                     "bearing": {"d": 50.0, "D": 65.0, "B": 7.0}, "limits": {"shaft_d_min": 6.0}}}
    cfgs = [{**base, "id": "PTK-T-X-AAAAAA", "gen": "bearing", "bearing": "61810"},
            {**base, "id": "PTK-T-X-BBBBBB", "gen": "eccentric", "bearing": ""}]
    keys = [{"d_max": 8, "b": 2, "h": 2, "t1": 1.2, "t2": 1.0},
            {"d_max": 10, "b": 3, "h": 3, "t1": 1.8, "t2": 1.4}]
    sh = {"link": "key", "tau_allow": 25.0, "sigma_crush": 100.0}
    dr = {"drills": [3.0, 4.0, 5.0]}
    inp = {"designs": [
        {"id": "PTK-T-X", "bearing": "61810", "name": "K8", "shaft": {**sh, "d": 8.0}, "balance": dr},
        {"id": "PTK-T-X", "gen": "bearing", "name": "K10", "shaft": {**sh, "d": 10.0}, "balance": dr},
        {"id": "PTK-T-X", "name": "AMB", "shaft": {**sh, "d": 10.0}}]}
    r8, r10, amb = run(inp, cfgs, lim, keys=keys)
    assert not r8["ok"] and any("τ" in e for e in r8["errors"]), r8["errors"]
    assert r10["ok"], r10["errors"]
    assert abs(r10["shaft"]["tau"] - 23.1) < 0.2, r10["shaft"]
    assert abs(r10["link"]["sigma"] - 52.1) < 0.2, r10["link"]
    b = r10["ecc"]["bal"]
    assert b["n"] >= 1 and b["d"] in (3.0, 4.0, 5.0), b
    assert "неоднозначен" in amb["errors"][0], amb
    assert [p["id"] for p in r10["parts"]] == [f"PTK-T-X-AAAAAA.03{v}-K10" for v in "ABCD"], r10["parts"]
    assert r10["mass"]["J_in"] > 0 and r10["mass"]["sum_g"] > 0, r10["mass"]
    assert pick([r10], "PTK-T-X-AAAAAA.03B-K10") is r10
    assert pick([r10], "PTK-T-X-AAAAAA") is None and pick([r10], "PTK-T-X-AAAAAA", "K10") is r10
    c = apply(cfgs[0], r10)
    assert c["geom"]["limits"]["shaft_d_min"] == 10.0 == r10["shaft"]["d"]
    assert cfgs[0]["geom"]["limits"]["shaft_d_min"] == 6.0, "apply изменил исходную запись"
    assert sorted(p["id"] for p in c["parts"] if ".03" in p["id"])[0].endswith("-K10")
    ri = design(cfgs[0], {"name": "I", "shaft": {"d": 10.0, "link": "integral"}}, lim, keys)
    assert ri["ok"] and ri["link"]["sigma"] is None and ri["ecc"]["key_b"] == 0.0, ri["errors"]
    # Д-110: допуски из материала — 45 без прутка отклонена, 40Х (σв 785) → [τ] 39.2, усталость
    mats = {"materials": {"40Х": {"sigma_v": 785, "sigma_t": 640, "state": "улучшение",
                                  "d_range": [0, 100]},
                          "45": {"sigma_v": 600, "sigma_t": 355}}}
    prods = {"PTK": {"parts": {"15": {"material": ["45", "40Х"]}, "03": {"material": ["40Х"]}}}}
    stock = {"materials": {"40Х": {"bars": [12, 14]}}}
    rm = design(cfgs[0], {"name": "M", "shaft": {"d": 10.0, "link": "key", "wall_min": 1.5}},
                lim, keys, mat_src=(mats, prods, stock))
    sm = rm["shaft"]
    assert rm["ok"] and sm["grade"] == "40Х" and sm["tau_basis"] == "fatigue", (rm["errors"], sm)
    # фикстура без sigma_m1 — σ₋₁ оценивается как 0.43·σв (Д-112), [τ] ≈ 35 МПа
    assert abs(sm["tau_allow"] - 35.0) < 0.1 and sm["crush_basis"] == "key", sm
    assert abs(sm["sigma_crush"] - 101.4) < 0.05 and "прутка" in sm["rejected"][0]["why"], sm
    assert sm["blank"].startswith("пруток Ø12"), sm
    assert "K10" in md([r8, r10, amb])["summary"]
    try:
        run({"designs": [{"id": "x", "name": "K-8", "shaft": {"d": 8.0}}]}, cfgs, lim, keys=keys)
        raise AssertionError("имя с «-» принято")
    except ValueError:
        pass
    try:                      # Д-109: keys во входе — ошибка, а не тихое игнорирование
        run({"keys": {"table": keys}, "designs": []}, cfgs, lim)
        raise AssertionError("keys.table во входе принята")
    except ValueError as e:
        assert "Д-109" in str(e), e
    assert keys_table(), "keys.table пуста (Д-109)"
    assert ptk_layout.self_test()
    return True
===== END FILE =====

===== FILE: egm/products.py (строки 1–68) =====
"""Реестр изделий и номенклатура деталей (Д-80, SPEC-03)."""
import re

PART_RE = re.compile(r"^(?P<cfg>(?P<prod>[A-Z]+)-[^.]+)\.(?P<nn>\d{2})(?P<var>[A-Z]?)$")


def parse(part_id):
    """'PTK-...-HASH.01B' -> {'cfg','prod','nn','var'}."""
    m = PART_RE.match(part_id)
    if not m:
        raise ValueError(f"неверный код детали {part_id!r} (SPEC-03)")
    return m.groupdict()


def item(products, part_id):
    p = parse(part_id)
    prod = products.get(p["prod"])
    if prod is None or p["nn"] not in prod["parts"]:
        raise KeyError(f"{part_id}: позиции {p['prod']}.{p['nn']} нет в products.yaml")
    return prod["parts"][p["nn"]]


def check(products, configs):
    """Ошибки: детали конфигураций, отсутствующие в номенклатуре."""
    fails = []
    for r in configs:
        for part in r.get("parts", []):
            try:
                it = item(products, part["id"])
                if it["variant"] == "none" and parse(part["id"])["var"]:
                    fails.append(f"{part['id']}: позиция без вариантов имеет букву")
            except (KeyError, ValueError) as e:
                fails.append(f"products: {e}")
    return fails


def check_app(app, prods):
    """Д-79: разделы продуктов в configs/application.yaml (products:) — есть в реестре
    products.yaml; enabled — при непустой номенклатуре."""
    fails = []
    for code, sec in (app.get("products") or {}).items():
        if not isinstance(sec, dict):
            fails.append(f"application.yaml: products.{code}: раздел не словарь (Д-79)")
        elif code not in prods:
            fails.append(f"application.yaml: products.{code} отсутствует в products.yaml (Д-79)")
        elif (sec.get("enabled") and not (prods[code].get("parts") or {})
              and not prods[code].get("source")):
            # Д-107: номенклатура продукта может жить вне products.yaml — ключ source
            # (SH → specs/shafts.yaml); parts тогда пуст намеренно.
            fails.append(f"application.yaml: products.{code}: enabled, но номенклатура "
                         "в products.yaml пуста (нет ни parts, ни source)")
    return fails


def self_test():
    p = parse("PTK-063-R5X8-8M4P2-3F9A1C.01B")
    assert p == {"cfg": "PTK-063-R5X8-8M4P2-3F9A1C", "prod": "PTK", "nn": "01", "var": "B"}, p
    prods = {"PTK": {"parts": {"01": {"variant": "ring_phase"}}}}
    assert not check(prods, [{"parts": [{"id": "PTK-1-X.01A"}]}])
    assert check(prods, [{"parts": [{"id": "PTK-1-X.09"}]}])
    assert check(prods, [{"parts": [{"id": "bad"}]}])
    app_prods = {"PTK": {"parts": {"01": {}}}, "HD": {"parts": {}},
                 "SH": {"parts": {}, "source": "specs/shafts.yaml"}}
    assert not check_app({"products": {"PTK": {"enabled": True},
                                       "HD": {"enabled": False}}}, app_prods)
    assert check_app({"products": {"XX": {"enabled": True}}}, app_prods)
    assert check_app({"products": {"HD": {"enabled": True}}}, app_prods)
    return True
===== END FILE =====

===== FILE: egm/ptk_parts.py (строки 1–216) =====
"""Детали ПТК: .02 сепаратор, .03 эксцентрик — геометрия и балансировка (CP-35, Д-46).

Числа считаются здесь (слой расчёта, Д-39) и попадают в ptk_configs.yaml → sep, ecc;
egm/cad/ptk_sep.py и ptk_ecc.py только строят PartModel.

Сепаратор .02 — одна деталь на пакет: втулка R_Σ ± SEP_K·a_ω длиной B пакета с прямыми
радиальными окнами (тела движутся строго радиально); окна ряда k повёрнуты на
(−s_k·z − φk)/n mod (360/n) — ptk.phasing → cage (Д-46, Д-53).
Шайбы .05 — кольца пакета венцов по торцам и между рядами (Д-53).
Эксцентрик .03 — диск толщиной t: наружный Ø D_э со смещением a_ω (посадка подшипника d
или поверхность качения D_г), отверстие под вал shaft_d_min с пазом шпонки; паз ряда k —
на угле key_angle − φk от эксцентриситета, отсюда варианты .03A… по рядам.
Балансировка ряда (Д-36): U = U_диска + m_подш·a_ω + (n/2)·m_тела·a_ω, г·мм; снимается
N сквозными отверстиями Ø d на радиусе r_h со стороны эксцентриситета:
U_отв = ρ·t·π·d²/4·r_h·Σcos β_j. Паз шпонки (~1 % U) не учитывается.
"""
import math

from egm.ptk_profile import Y


def separator(n, R, a, D, l, pitch, rows, lim, sep_k):
    """Сепаратор: радиусы, окна w × h, положение окон рядов по оси и углу."""
    r_in, r_out = R - sep_k * a, R + sep_k * a
    w, h = D + lim.sep_gap, l + lim.sep_gap
    win = [{"row": row["row"],
            "cage": round(((-row["s"] * (n + 1) - row["phi"]) / n) % (360 / n), 4),
            "z0": round(lim.row_gap + k * (pitch + lim.row_gap) + (pitch - h) / 2, 3)}
           for k, row in enumerate(rows)]
    return {"n": n, "r_in": round(r_in, 3), "r_out": round(r_out, 3), "w": round(w, 3),
            "h": round(h, 3), "length": round(len(rows) * pitch + (len(rows) + 1) * lim.row_gap, 3),
            "web": round(2 * r_in * math.sin(math.pi / n) - w, 3), "rows": win}


def _fit(N, d, a, Re, r_lo, w):
    """N отверстий Ø d у наружной кромки, перемычки w -> (r_h, [β, рад]) | None."""
    r = Re + a - w - d / 2
    for _ in range(500):
        r = math.floor(r * 100 + 1e-9) / 100
        if r - d / 2 < r_lo - 1e-9 or (N > 1 and d + w > 2 * r):
            return None
        db = 2 * math.asin((d + w) / (2 * r)) if N > 1 else 0.0
        bs = [(j - (N - 1) / 2) * db for j in range(N)]
        if abs(bs[0]) > math.pi / 2:
            return None
        r_max = min(Y(b, a, Re) for b in bs) - w - d / 2
        if r <= r_max + 1e-9:
            return r, bs
        r = min(r - 0.01, r_max)
    return None


def balance(U, a, Re, t, rho, r_lo, lim):
    """Подбор N × Ø d с наименьшим |U − U_отв|; N = 0 — без отверстий."""
    k = rho * t * math.pi / 4
    best = (abs(U), 0, 0.0, 0.0, [], 0.0)
    ds = getattr(lim, "bal_drills", None)       # Д-48: только свёрла из списка
    for N in range(1, int(lim.bal_n_max) + 1):
        i = 0
        while True:
            if ds is not None and i >= len(ds):
                break
            d = ds[i] if ds is not None else round(lim.bal_d_min + i * lim.bal_d_step, 4)
            g = _fit(N, d, a, Re, r_lo, lim.bal_wall)
            if g is None:
                break
            r, bs = g
            Ur = k * d * d * r * sum(math.cos(b) for b in bs)
            if abs(U - Ur) < best[0] - 1e-9:
                best = (abs(U - Ur), N, d, r, bs, Ur)
            if Ur >= U:
                break
            i += 1
    _, N, d, r, bs, Ur = best
    return {"n": N, "d": d, "r": r, "U_rem": round(Ur, 2), "res": round(U - Ur, 2),
            "holes": [(round(r * math.cos(b), 3), round(r * math.sin(b), 3)) for b in bs]}


def eccentric(n, a, D, rol, brg, rows, lim, gen, R):
    """Эксцентрик ряда: размеры, дисбаланс, отверстия балансировки, пазы шпонки рядов."""
    rho = lim.rho * 1e-6                                  # г/мм³
    if gen == "bearing":
        De, t, est = brg["d"], brg["B"], not brg.get("m")
        m_b = (rho * lim.brg_mass_k * math.pi / 4 * (brg["D"] ** 2 - brg["d"] ** 2) * brg["B"]
               if est else brg["m"] * 1e3)
    else:
        De, t, m_b, est = 2 * R - D, rol["l"], 0.0, False
    ball = rol.get("type", "roller") == "ball"
    vol = math.pi * D ** 3 / 6 if ball else math.pi * D * D * rol["l"] / 4
    U = {"disk": rho * t * math.pi * De * De / 4 * a, "brg": m_b * a,
         "bodies": n / 2 * rho * vol * a}
    U["sum"] = sum(U.values())
    rs, t2 = lim.shaft_d_min / 2, lim.shaft_key_t2
    bal = balance(U["sum"], a, De / 2, t, rho, rs + t2 + lim.bal_wall, lim)
    warns = []
    if abs(bal["res"]) > 0.05 * U["sum"]:
        warns.append(f"эксцентрик: остаток дисбаланса {bal['res']:g} из {U['sum']:.1f} г·мм — "
                     f"отверстия балансировки не помещаются (Д-46)")
    out = []
    for row in rows:
        ka = round((lim.key_angle - row["phi"]) % 360, 3)
        wall = Y(math.radians(ka), a, De / 2) - rs - t2
        if wall < lim.ecc_wall_min - 1e-9:
            warns.append(f"ряд {row['row']}: стенка эксцентрика у паза шпонки {wall:.2f} < "
                         f"ecc_wall_min {lim.ecc_wall_min:g} мм — изменить key_angle (Д-46)")
        out.append({"row": row["row"], "phi": row["phi"], "key_angle": ka,
                    "key_wall": round(wall, 2)})
    return {"De": round(De, 3), "t": t, "a": a, "d_shaft": lim.shaft_d_min,
            "key_b": lim.shaft_key_b, "key_t2": t2, "m_brg_g": round(m_b, 1), "m_brg_est": est,
            "groove_r": round(lim.groove_f * D, 3) if ball and gen == "eccentric" else None,
            "U": {k: round(v, 2) for k, v in U.items()}, "bal": bal, "rows": out,
            "warnings": warns}


def parts(cid, ecc):
    """Детали .02 (одна на пакет) и .03<вариант> (по пазу шпонки ряда)."""
    out = [{"id": f"{cid}.02", "name": "сепаратор", "variant": "",
            "rows": [x["row"] for x in ecc["rows"]]}]
    var = {}
    for x in ecc["rows"]:
        v = var.setdefault(x["key_angle"], chr(ord("A") + len(var)))
        p = next((q for q in out if q["id"] == f"{cid}.03{v}"), None)
        if p is None:
            p = {"id": f"{cid}.03{v}", "name": "эксцентрик", "variant": v,
                 "key_angle": x["key_angle"], "rows": []}
            out.append(p)
        p["rows"].append(x["row"])
    return out


def spacers(d_root, d_out, d_bc, d_clear, l, pitch, rows, lim):
    """Шайбы .05 (Д-53): венец ряда k занимает zc ± l/2 (egm/cad/assy.plan), шайбы — остальное.

    У торца h = row_gap + (шаг − l)/2, между рядами h = row_gap + шаг − l; dвн = DВ + 2·spacer_gap,
    поэтому тела и сепаратор шайб не касаются; осевую фиксацию тел даёт окно сепаратора."""
    r_in = d_root / 2 + lim.spacer_gap
    h_end = round(lim.row_gap + (pitch - l) / 2, 3)
    h_mid = round(lim.row_gap + pitch - l, 3)
    pos, var, z = [], {}, 0.0
    for j in range(rows + 1):
        h = h_end if j in (0, rows) else h_mid
        v = var.setdefault(h, chr(ord("A") + len(var)))
        pos.append({"pos": j, "z": round(z, 3), "h": h, "variant": v})
        z += h + l
    web = round(d_bc / 2 - d_clear / 2 - r_in, 2)
    warns = [] if web > 0 else [f"шайба .05: dвн {2 * r_in:.2f} заходит на отверстия Dотв "
                                f"{d_bc:g} — уменьшить spacer_gap (Д-53)"]
    return {"r_in": round(r_in, 3), "d_out": d_out, "h_end": h_end, "h_mid": h_mid,
            "web": web, "pos": pos, "warnings": warns}


def spacer_parts(cid, sp, rows):
    """Детали .05<вариант>: вариант — по толщине; pos — места в пакете (0 — торец входа)."""
    out = {}
    for x in sp["pos"]:
        v = x["variant"]
        p = out.setdefault(v, {"id": f"{cid}.05{v}", "name": "межрядная шайба", "variant": v,
                               "h": x["h"], "pos": [], "rows": []})
        p["pos"].append(x["pos"])
        near = {x["pos"], x["pos"] + 1} & set(range(1, rows + 1))
        p["rows"] = sorted(set(p["rows"]) | near)
    return list(out.values())


def _sp(s):
    return (f"{2 * s['r_in']:g} / {s['d_out']:g}, {s['h_end']:g} / {s['h_mid']:g}"
            if s else "—")


def table(rows):
    """SPEC-10: детали .02, .03 реализуемых исполнений."""
    L = ["| ID | Генератор | Dэ × t, мм | Пазы шпонки, ° | U, г·мм | Отв. балансировки | "
         "Остаток, г·мм | Сепаратор dс / Dс × B | Окна w × h | Перемычка | "
         "Шайбы .05 dвн / D, h торец / между |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        e, s = r.get("ecc"), r.get("sep")
        if not e or not s:
            continue
        b = e["bal"]
        holes = f"{b['n']}×Ø{b['d']:g}, r {b['r']:g}" if b["n"] else "нет"
        keys = ", ".join(f"{x['key_angle']:g}" for x in e["rows"])
        L.append(f"| {r['id']} | {r['bearing'] or 'эксцентрик'} | {e['De']:g} × {e['t']:g} | {keys} | "
                 f"{e['U']['sum']:g} | {holes} | {b['res']:g} | "
                 f"{2 * s['r_in']:g} / {2 * s['r_out']:g} × {s['length']:g} | "
                 f"{s['w']:g} × {s['h']:g} | {s['web']:g} | {_sp(r.get('spacer'))} |")
    return "\n".join(L) if len(L) > 2 else "нет реализуемых исполнений"


def self_test():
    from types import SimpleNamespace
    lim = SimpleNamespace(sep_gap=0.05, row_gap=1.0, rho=7850.0, brg_mass_k=0.35,
                          shaft_d_min=6.0, shaft_key_b=2.0, shaft_key_t2=1.0, bal_wall=1.0,
                          bal_n_max=3, bal_d_min=1.0, bal_d_step=0.1, ecc_wall_min=1.0,
                          key_angle=45.0, groove_f=0.52, spacer_gap=0.5)
    rows = [{"row": k + 1, "phi": p, "s": -p} for k, p in enumerate((0, 90, 180, 270))]
    s = separator(50, 33.5, 0.4, 2.0, 4.2, 7.0, rows, lim, 1.1)
    assert s["web"] > 0 and len(s["rows"]) == 4, s
    c = s["rows"][1]["cage"]
    assert abs(c - 90 % 7.2) < 1e-6, ("s = −φ: cage = φ mod 360/n (Д-46)", c)
    s0 = separator(50, 33.5, 0.4, 2.0, 4.2, 7.0, [{**x, "s": 0.0} for x in rows], lim, 1.1)
    c0 = s0["rows"][1]["cage"]
    assert abs(c0 - (-90 / 50) % 7.2) < 1e-6, ("s = 0: cage = −φ/n mod 360/n (Д-46)", c0)
    e = eccentric(50, 0.4, 2.0, {"type": "roller", "d": 2.0, "l": 4.2},
                  {"d": 50.0, "D": 65.0, "B": 7.0}, rows, lim, "bearing", 33.5)
    assert e["bal"]["n"] >= 1 and abs(e["bal"]["res"]) <= 0.05 * e["U"]["sum"], e["bal"]
    assert not e["warnings"], e["warnings"]
    p = parts("PTK-T", e)
    assert [q["id"] for q in p] == ["PTK-T.02", "PTK-T.03A", "PTK-T.03B", "PTK-T.03C",
                                    "PTK-T.03D"], p
    sp = spacers(69.8, 88.0, 80.0, 4.5, 4.2, 7.0, 4, lim)           # Д-53
    assert (sp["h_end"], sp["h_mid"]) == (2.4, 3.8) and not sp["warnings"], sp
    assert abs(sum(x["h"] for x in sp["pos"]) + 4 * 4.2 - 33.0) < 1e-6, ("шайбы + венцы = B", sp)
    q = spacer_parts("PTK-T", sp, 4)
    assert [(x["id"], x["pos"]) for x in q] == [("PTK-T.05A", [0, 4]), ("PTK-T.05B", [1, 2, 3])], q
    assert q[0]["rows"] == [1, 4] and q[1]["rows"] == [1, 2, 3, 4], q
    return True
===== END FILE =====

===== FILE: egm/config.py (строки 58–73) =====
def load(name, base=None):
    """YAML-файл -> dict (Д-79). base — папка с файлом (по умолчанию specs/ корня
    репозитория); имя — с .yaml или без. Путь, существующий от текущей папки
    (например specs/cad_set.yaml из --spec), берётся как есть; абсолютный путь —
    тоже (ссылки application.yaml резолвит cfg_file, Д-79)."""
    if yaml is None:
        raise ValueError("PyYAML не установлен: pip install pyyaml "
                         "(ручные конфиги specs/*.yaml, Д-79)")
    p = Path(name)
    if p.suffix != ".yaml":
        p = p.with_suffix(".yaml")
    if base is None and not p.exists():
        p = SPECS / p.name
    return yaml.safe_load((base / p.name if base else p).read_text(encoding="utf-8"))


===== END FILE =====

### Комментарии-глоссарий результирующего YAML (куда вписать новые ключи)

===== FILE: egm/design_doc.py (строки 1–554) =====
"""egm/design_doc.py — вывод проработок шага 2 (SPEC-11, Д-48) в КОММЕНТИРОВАННЫЙ YAML.

Зачем. Прежний specs/ptk_designs.json — машиночитаемый выход шага 2 — состоял из ~200
листьев с сокращёнными именами (r_j, hole12, s_ob, sig_wall, L_r, w, …). Смысл половины
из них не восстанавливается без чтения кода. Здесь тот же результат пишется в
specs/ptk_designs.yaml, где ПЕРЕД КАЖДЫМ ключом стоит комментарий с расшифровкой,
а в шапке файла — глоссарий сокращений.

Как это устроено. Комментарии не могут быть выведены из данных: сериализатор знает
только значения. Поэтому описание ключей — отдельная таблица GLOSSARY (точные пути)
плюс PATTERNS (шаблоны для повторяющихся узлов: элементы списков, материалы,
позиции спецификации). Путь ключа строится эмиттером и ищется в таблице: сначала
точное совпадение, затем шаблоны от более специфичного к общему.

Формат. YAML пишется своим эмиттером (не yaml.dump), потому что нужны комментарии
и предсказуемый порядок ключей. Ключи-номера позиций спецификации выводятся в
кавычках: без кавычек YAML 1.1 читает 010 как 8, а 09 как строку — тип ключа
зависел бы от номера позиции. Списки скаляров — в потоковом виде [a, b, c].

Чтение. load_specs() читает .yaml, при отсутствии — старый .json (переходный путь
для песочниц без перегона шага 2). Пишет файл только шаг 2 (main.py run_design).
"""

import json
from pathlib import Path

from egm import doc_yaml

try:
    import yaml
except ImportError:                     # внятная ошибка вместо traceback импорта
    yaml = None

FILE = "ptk_designs"                    # specs/<FILE>.yaml (выход шага 2, Д-105)

# ---------------------------------------------------------------------------
# Шапка файла: назначение и глоссарий сокращений
# ---------------------------------------------------------------------------

HEADER = """\
# ============================================================================
# ptk_designs.yaml — проработки шага 2 «Проработка выбранных исполнений».
# Пишет МАШИНА: python main.py design --publish → specs/ptk_designs.yaml
#
# Руками НЕ править: изменения теряются на следующем прогоне. Управляющие
# параметры проработок (eta, ecc_share, key_angle, shaft, balance, output,
# layout, join, supports) задаются в specs/ptk_design_input.yaml — там же
# описан каждый входной ключ.
#
# Формат YAML заменяет прежний ptk_designs.json (Д-105): каждый ключ вывода
# снабжён комментарием, шапка содержит глоссарий сокращений. Ключи-номера
# позиций ("09") выводятся строкой в кавычках — иначе YAML 1.1 читает 010
# как 8, а 09 как строку, и тип ключа зависел бы от номера позиции.
#
# СОКРАЩЕНИЯ
#   .NN         позиция спецификации: .01 корпус, .02 обечайка/стакан (.02A
#               стакан L1, .02B обечайка с буртом L2, .02C обечайка без бурта
#               L3/L4), .03 эксцентрик, .04/.05 гильза и втулка, .07A/.07B
#               крышки входа/выхода, .09 подшипник выхода, .10 подшипник конца
#               входного вала, .11 кольцо дистанционное, .12 ступица (.12A
#               с опорным ободом L2/L4, .12B дно-вставка L3), .13 дно-лист
#               (CANCELLED), .14 кольцо-бурт L4, .15 входной вал, .16 гайка.
#   L1…L4       конструктив выхода (Д-73, Д-96, Д-102).
#   D, d        наружный / внутренний диаметр, мм; r0, r1 — внутренний /
#               наружный радиус, мм (r = D/2).
#   t, s        толщина: t — стенка/диск, s — толщина детали или стенка трубы.
#   m           ширина канавки по оси, мм (ГОСТ 13942/13943).
#   L, l        L — длина по оси (детали, соединения, кольца); l — длина штифта.
#   n, n_p      число элементов, шт (n_p — штифты фланца).
#   F, M, U     сила (Н), момент (Н·мм), дисбаланс (г·мм).
#   eta         КПД передачи; ecc_share — доля момента на один эксцентрик.
#   tau         касательное напряжение τ, МПа; sig_* — напряжение смятия σсм,
#               МПа; [τ], [σ] — допускаемые (в ключах — tau_allow, sig_allow).
#   hole12      глубина гнезда штифта в ступице .12, мм (Д-74).
#   need        требуемая (минимальная) величина; lim — предел/допуск.
#   b09, b10    подшипники .09 и .10 (строки vendor_prices.yaml → bearings).
#   da          диаметр заплечика подшипника (каталог); r_h = da/2.
#   s_об        толщина опорного обода .12A: s_об = r0 − r_h (Д-102 п. 4).
#   grooves     канавки под стопорные кольца ГОСТ 13942 (наружное, на ступице/вале)
#               и 13943 (внутреннее, в отверстии .07B); ключи ext (наружное,
#               rings_ext) и int (внутреннее, rings_int); параметры s (толщина
#               кольца), m (ширина канавки), d2 (Ø дна канавки).
# ============================================================================
"""

# ---------------------------------------------------------------------------
# Таблица комментариев: точные пути
# ---------------------------------------------------------------------------

GLOSSARY = {
    # --- запись проработки -------------------------------------------------
    "id": "ID записи: ID исполнения шага 1 + «-» + имя проработки (префикс без хэша, Д-51).",
    "name": "Имя проработки (K8, K10…): суффикс файлов деталей и сборки; латиница, цифры, «_», без «-».",
    "ok": "Итог: true — конструктив выбран и проверки пройдены; false — причины в errors, запись неполная.",
    "errors": "Отказы: проработка не строится (нет заготовки, не проходят штифты, нет конструктива).",
    "warnings": "Предупреждения: построено, но есть замечания (оценки, подстановки, границы).",

    # --- эхо входа ---------------------------------------------------------
    "input": "Эхо входа: дословная копия записи designs[] из specs/ptk_design_input.yaml — для воспроизводимости.",
    "input.id": "ID исполнения шага 1, к которому относится проработка.",
    "input.bearing": "Подшипник выхода .09, заданный во входе (уточняет выбор при неоднозначном префиксе ID).",
    "input.name": "Имя проработки из входа.",
    "input.eta": "КПД передачи: T_вх = M/(u·eta); меньше eta — больше момент на валу и эксцентриках.",
    "input.ecc_share": "Доля входного момента на один эксцентрик (смятие шпонки, OQ-15).",
    "input.key_angle": "Угол паза шпоночного ряда 1 от направления эксцентриситета, °; ряд k — минус φk.",
    "input.shaft": "Входной вал в эксцентрике: расчётные параметры вала и шпоночного соединения.",
    "input.shaft.d": "Ø вала, мм (кручение, шпонка, стенка эксцентрика).",
    "input.shaft.bore": "Ø отверстия полого вала, мм; 0 — сплошной.",
    "input.shaft.link": "Соединение эксцентрик–вал: key | flat | integral | spline | press.",
    "input.shaft.tau_allow": "[τ] кручения вала, МПа (изгиб не считается — занижено).",
    "input.shaft.sigma_crush": "[σсм] шпонки вала, МПа.",
    "input.shaft.wall_min": "Минимальная стенка полого вала у паза, мм.",
    "input.shaft.id": "ID конфигурации specs/shafts.yaml или список ID — наименьшая проходящая "
                      "(Д-107, Д-110).",
    "input.shaft_id": "Выбранный ID конфигурации вала (Д-110); пусто — вал задан полным блоком "
                      "(устар., Д-107).",
    "input.balance": "Балансировка пакета эксцентриков на шаге 2.",
    "input.balance.n_max": "Наибольшее число отверстий балансировки, шт.",
    "input.balance.wall": "Стенка у отверстий балансировки, мм.",
    "input.balance.drills": "Имеющиеся свёрла, мм (пусто — от bal_d_min с шагом bal_d_step шага 1).",
    "input.lighten": "Облегчение ступицы: none — не используется (OQ-12).",
    "input.output": "Выходной вал в ступице (Д-102, CP-90): формат как shaft, шпонки — keys.table.",
    "input.output.link": "Соединение ступица–потребитель: key | spline (flange — до реализации отказ).",
    "input.output.d": "Ø выходного вала, мм; 0 — подбор по кручению.",
    "input.output.tau_allow": "[τ] кручения выходного вала, МПа (изгиб от потребителя не считается).",
    "input.output.sigma_crush": "[σсм] шпонки в стальной ступице, МПа.",
    "input.layout": "Список конструктивов в порядке предпочтения: берётся первый, для которого есть заготовка и проходят штифты.",
    "input.join": "Переопределения соединения .02–.12 (штифты: pin_d, sig_wall).",
    "input.supports": "Опоры выхода и технологические минимумы (Д-55, Д-81): [τ] ступицы, стенки, кольца .11, буртик, дно, зазор, гайка.",

    # --- выбранный конструктив --------------------------------------------
    "layout": "Результат выбора конструктива и расчёт всей геометрии узла (вход генератора CAD).",
    "layout.code": "Выбранный конструктив: L1 | L2 | L3 | L4.",
    "layout.name": "Наименование конструктива по products.yaml (для таблицы «Конструктив» SPEC-11).",
    "layout.parts": "Позиции спецификации: ключ — номер позиции (строка!), значение — обозначение детали с буквой исполнения.",
    "layout.b09": "Подшипник выхода .09 — строка каталога vendor_prices.yaml → bearings.",
    "layout.b09.id": "Обозначение подшипника (61810).",
    "layout.b09.d": "Ø отверстия d, мм (посадка на ступицу).",
    "layout.b09.D": "Ø наружный D, мм (посадка в .07B).",
    "layout.b09.B": "Ширина B, мм.",
    "layout.b09.C": "Грузоподъёмность динамическая C, кН.",
    "layout.b09.C0": "Грузоподъёмность статическая C0, кН.",
    "layout.b09.da": "Ø заплечика da, мм — упор внутреннего кольца на ступице; r_h = da/2 (OQ-31).",
    "layout.b10": "Подшипник конца входного вала .10 — гнездо в ступице.",
    "layout.b10.id": "Обозначение подшипника (61800).",
    "layout.b10.d": "Ø отверстия d, мм (посадка на входной вал).",
    "layout.b10.D": "Ø наружный D, мм (гнездо в ступице).",
    "layout.b10.B": "Ширина B, мм.",
    "layout.b10.C": "Грузоподъёмность динамическая C, кН.",
    "layout.b10.C0": "Грузоподъёмность статическая C0, кН.",
    "layout.b10.da": "Ø заплечика da, мм.",
    "layout.tau_hub": "τ кручения ступицы, МПа.",
    "layout.tau_allow": "[τ] кручения ступицы, МПа.",
    "layout.r11": "Кольцо дистанционное .11 (между подшипниками и эксцентриками).",
    "layout.r11.n": "Число колец .11, шт.",
    "layout.r11.h": "Толщина кольца, мм.",
    "layout.r11.d_in": "Внутренний Ø, мм.",
    "layout.r11.d_out": "Наружный Ø, мм.",
    "layout.covers": "Крышки .07A/.07B: привалочные размеры.",
    "layout.covers.tA": "Толщина крышки входа .07A, мм.",
    "layout.covers.tB": "Толщина крышки выхода .07B, мм (по канавке ГОСТ 13943 лип_B).",
    "layout.covers.D": "Ø посадки крышки в корпус, мм.",
    "layout.covers.seat_A": "Глубина гнезда .07A, мм.",
    "layout.covers.seat_B": "Глубина гнезда .07B, мм.",
    "layout.covers.pocket": "Карман крышки: [Ø кармана, глубина], мм.",
    "layout.cup": "Стакан/обечайка .02 — осевые размеры и ступица (Д-102, Д-103).",
    "layout.cup.z_in": "Начало внутренней полости в системе корпуса, мм (z = 0 сборки).",
    "layout.cup.t": "Толщина дна стакана, мм (L1) либо длина обечайки до торца (L3/L4).",
    "layout.cup.hub_d": "Ø ступицы (посадка .09), мм.",
    "layout.cup.hub_bore": "Ø отверстия под .10, мм.",
    "layout.cup.hub_l": "Длина ступицы, мм.",
    "layout.length": "Габаритная длина проработки по оси, мм (CP-45).",
    "layout.blank": "Заготовка .02: выбранный материал, альтернативы и требования к сортаменту.",
    "layout.blank.material": "Материал заготовки .02.",
    "layout.blank.alt": "Материалы, перебранные как альтернатива.",
    "layout.blank.tried": "Материалы, для которых искали заготовку.",
    "layout.blank.alt_fit": "Заготовки по альтернативным материалам (нужны для сравнения съёма металла).",
    "layout.blank.missing": "Чего не хватило в сортаменте (причина отказа материала).",
    "layout.blank.forms": "Допустимые формы заготовки: труба | лист | пруток.",
    "layout.blank.tube": "Выбранная труба заготовки .02.",
    "layout.blank.tube.D": "Наружный Ø трубы, мм.",
    "layout.blank.tube.s": "Стенка трубы, мм.",
    "layout.blank.tube.note": "Примечание по трубе (допуск, источник).",
    "layout.blank.tube_need": "Требуемые [Ø_min, Ø_max] или [D, s] трубы, мм.",
    "layout.blank.sheet": "Лист-заготовка (для конструктива с дном-листом; ветка CANCELLED).",
    "layout.blank.sheet_need": "Требуемая толщина листа, мм.",
    "layout.blank.sheet_len": "Требуемый размер листа, мм.",
    "layout.blank.bar": "Пруток-заготовка, мм (L1 — стакан монолитом).",
    "layout.join": "Соединение .02–.12 (Д-74): выбранный вариант, перебор и пределы расчёта.",
    "layout.join.pick": "Выбранный вариант соединения (вход CAD и ячейка «Схема» SPEC-11).",
    "layout.join.pick.scheme": "Схема: collar (L2, бурт .02B) | insert (L3, дно-вставка .12B) | ring (L4, кольцо .14).",
    "layout.join.pick.material": "Материал заготовки .02 в выбранном варианте.",
    "layout.join.pick.tube": "Труба заготовки .02 выбранного варианта.",
    "layout.join.pick.tube.D": "Наружный Ø трубы, мм.",
    "layout.join.pick.tube.s": "Стенка трубы, мм.",
    "layout.join.pick.tube.note": "Примечание по трубе.",
    "layout.join.pick.pins": "Штифты соединения и проверки прочности (срез, смятие стенки и ступицы, срез к торцу).",
    "layout.join.pick.geom": "Геометрия схемы соединения: радиусы, стенка, Ø пояса и отверстия.",
    "layout.join.pick.geom.r_j": "Радиус осей штифтов, мм (для схемы «обод в отверстии» — не используется).",
    "layout.join.pick.geom.t": "Стенка, через которую проходит штифт, мм.",
    "layout.join.pick.geom.D": "Наружный Ø пояса/бурта, мм.",
    "layout.join.pick.geom.d": "Внутренний Ø пояса/бурта, мм.",
    "layout.join.pick.ring": "Кольцо-бурт .14 (L4): сидит в выходном торце обечайки .02C.",
    "layout.join.pick.ring.r0": "Радиус отверстия кольца = радиус опорного обода .12A, мм.",
    "layout.join.pick.ring.r1": "Наружный радиус кольца = радиус отверстия обечайки .02C, мм.",
    "layout.join.pick.ring.L": "Длина кольца по оси, мм (= осевая длина бурта/кольца, 2·edge_k·d).",
    "layout.join.pick.ring.w": "Ширина кольца, мм = max(t_tech, k_fit·d) — посадочная длина штифта.",
    "layout.join.pick.ring_blank": "Заготовка кольца .14: труба или пруток по products.yaml.",
    "layout.join.pick.ring_blank.material": "Материал кольца .14.",
    "layout.join.pick.ring_blank.tube": "Труба заготовки кольца .14.",
    "layout.join.pick.ring_blank.tube.D": "Наружный Ø трубы, мм.",
    "layout.join.pick.ring_blank.tube.s": "Стенка трубы, мм.",
    "layout.join.pick.ring_blank.tube.note": "Примечание по трубе.",
    "layout.join.pick.ring_blank.need": "Требуемые размеры трубы [D, s] или [D_max, s_max], мм.",
    "layout.join.variants": "Все перебранные схемы соединения с причинами отказа (для SPEC-11 и разбора).",
    "layout.join.variants[].scheme": "Схема варианта: collar | insert | ring.",
    "layout.join.variants[].geom": "Геометрия варианта.",
    "layout.join.variants[].pins": "Штифты и проверки прочности варианта (null — штифты не подобраны).",
    "layout.join.variants[].need": "Требуемые размеры заготовки, мм.",
    "layout.join.variants[].fit": "Подходящие трубы по материалам варианта.",
    "layout.join.variants[].house": "Отказ по корпусу (габарит не вписывается).",
    "layout.join.variants[].rej": "Отказ по заготовке (нет трубы/прутка нужного размера).",
    "layout.join.variants[].note": "Примечание варианта (почему не выбран).",
    "layout.join.variants[].margin": "Запас по корпусу, мм (положительный — вписывается).",
    "layout.join.tried": "Материалы, перебранные для соединения.",
    "layout.join.lim": "Пределы расчёта соединения (допускаемые напряжения и технологические минимумы).",
    "layout.join.lim.sig_wall": "[σсм] стенки .02, МПа.",
    "layout.join.lim.tau_pin": "[τ] среза штифта, МПа.",
    "layout.join.lim.sig_hub": "[σсм] ступицы/обода, МПа.",
    "layout.join.lim.r_lim": "Предельный радиус по корпусу, мм.",
    "layout.join.lim.r_free": "Свободный радиус под гайку и кольца .11, мм.",
    "layout.join.lim.k_fit": "Коэффициент посадочной длины штифта (k_fit·d).",
    "layout.join.lim.t_tech": "Технологический минимум толщины/ширины, мм.",
    "layout.join.lim.tau_disk": "[τ] среза диска, МПа.",
    "layout.output": "Выходной вал и ступица (Д-102, Д-103, Д-104, CP-90): шпонка, длина, фланец, канавки, обод.",
    "layout.output.link": "Соединение ступица–вал: key | spline | flange.",
    "layout.output.d": "Ø выходного вала (принятый), мм.",
    "layout.output.key": "Шпонка призматическая по keys.table (specs/shafts.yaml, DIN 6885 / ГОСТ 23360).",
    "layout.output.key.d_max": "Верхняя граница Ø вала для этой шпонки, мм.",
    "layout.output.key.b": "Ширина шпонки b, мм.",
    "layout.output.key.h": "Высота шпонки h, мм.",
    "layout.output.key.t1": "Глубина паза вала t1, мм.",
    "layout.output.key.t2": "Глубина паза ступицы t2, мм.",
    "layout.output.l_key": "Длина шпоночного паза l_key, мм (≥ 2M/(d_o·(h−t1)·[σсм]) + b).",
    "layout.output.tau": "τ кручения выходного вала, МПа.",
    "layout.output.tau_allow": "[τ] кручения выходного вала, МПа.",
    "layout.output.sigma_allow": "[σсм] шпонки, МПа.",
    "layout.output.hub_l": "Длина ступицы, мм (по фланцу/корпусу, Д-103; шпонка — расчётный минимум).",
    "layout.output.hub_by": "Чем задана длина ступицы (фланец, корпус, шпонка).",
    "layout.output.r_h": "Радиус заплечика .09 r_h = da/2, мм — внутренняя граница опорного обода .12A.",
    "layout.output.da_est": "true — da .09 взят оценкой d + 0.3·(D−d): граница s_об условна (OQ-31).",
    "layout.output.flush": "true — наружный торец ступицы заподлицо с .07B (Д-103).",
    "layout.output.lip_B": "Буртик крышки .07B за подшипником, мм (по канавке ГОСТ 13943).",
    "layout.output.flange": "Фланец выхода (Д-104): винты трением либо штифты срезом, отверстия под гайку .16.",
    "layout.output.flange.screw": "Тип винтов фланца.",
    "layout.output.flange.n": "Число винтов, шт.",
    "layout.output.flange.r": "Радиус окружности винтов, мм.",
    "layout.output.flange.d_tap": "Ø резьбы, мм.",
    "layout.output.flange.depth": "Глубина резьбы, мм.",
    "layout.output.flange.T_fric": "Момент, передаваемый трением фланца, Н·мм.",
    "layout.output.flange.n_p": "Число штифтов фланца (срезом), шт.",
    "layout.output.flange.pin_d": "Ø штифтов фланца, мм.",
    "layout.output.flange.pin_depth": "Глубина гнёзд штифтов фланца, мм.",
    "layout.output.flange.fl_txt": "Готовый текст фланца для SPEC-11.",
    "layout.output.grooves": "Канавки под стопорные кольца ГОСТ 13942 (наружное, на ступице/вале) и 13943 (внутреннее, в отверстии .07B): фиксируют внутреннее и наружное кольца подшипника .09.",
    "layout.output.grooves.ext": "Канавка ГОСТ 13942-86 (rings_ext) на ступице .12 / вале .03: наружная фиксация внутреннего кольца .09 от осевого смещения наружу. Ключ подбора — Ø отверстия d подшипника .09.",
    "layout.output.grooves.int": "Канавка ГОСТ 13943-86 (rings_int) в корпусе крышки .07B: внутренняя фиксация наружного кольца .09 от осевого смещения внутрь. Ключ подбора — Ø наружный D подшипника .09.",
    "layout.output.s_ob": "Толщина опорного обода .12A: s_об = r0 − r_h, мм (Д-102 п. 4).",
    "layout.output.s_ob_need": "Требуемая толщина обода: max(hole12 + pin_wall, ob_min), мм.",
    "layout.var": "Буквы исполнений деталей в этом конструктиве (ключ — позиция).",
    "layout.var_name": "Полные обозначения исполнений .02 и .12.",
    "layout.tooling": "Оснастка и маршрут обработки (для техпроцесса).",
    "layout.tooling[].fx": "Операция (фрезерование, сверление, точение).",
    "layout.tooling[].part": "Деталь, к которой относится операция.",
    "layout.tooling[].size": "Размер/инструмент операции.",
    "layout.tooling[].route": "Маршрут (порядок операций).",
    "layout.shaft_d": "Ø входного вала, мм.",
    "layout.ax_gap": "Осевой зазор, мм.",
    "layout.cad_parts": "Готовые входные структуры для генератора CAD (то, что читает egm.cad).",
    "layout.cad_parts[].id": "ID детали для генератора (например PTK-050-…-L4.12A).",
    "layout.cad_parts[].base": "Позиция спецификации (01, 02, 03, 07, 09…).",
    "layout.cad_parts[].rows": "Ряды детали (для эксцентриков и гильз — номера рядов).",
    "layout.cad_parts[].join": "Параметры соединения .02–.12 для CAD этой детали.",
    "layout.cad_parts[].join.scheme": "Схема соединения: collar | insert | ring.",
    "layout.cad_parts[].join.z": "Осевая координата соединения, мм.",
    "layout.cad_parts[].join.L": "Длина пояса/кольца, мм.",
    "layout.cad_parts[].join.f": "Высота бурта-упора f (insert), мм; 0 — нет.",
    "layout.cad_parts[].join.r_in": "Внутренний радиус обечайки, мм.",
    "layout.cad_parts[].join.r_out": "Наружный радиус бурта, мм.",
    "layout.cad_parts[].join.r_j": "Радиус осей осевых штифтов, мм.",
    "layout.cad_parts[].join.D": "Наружный Ø пояса/бурта, мм.",
    "layout.cad_parts[].join.d": "Внутренний Ø пояса/бурта, мм.",
    "layout.cad_parts[].join.pin_d": "Ø штифтов, мм.",
    "layout.cad_parts[].join.pin_n": "Число штифтов, шт.",
    "layout.cad_parts[].join.pin_l": "Длина штифта, мм.",
    "layout.cad_parts[].join.hole12": "Глубина гнезда в ступице .12, мм.",
    "layout.cad_parts[].join.pin_z": "Осевая координата штифтов, мм.",
    "layout.cad_parts[].join.pin_a": "Углы штифтов, ° (выровнены по окнам сепаратора).",
    "layout.cad_parts[].join.hub_d": "Ø ступицы, мм.",
    "layout.cad_parts[].join.hub_bore": "Ø отверстия под .10, мм.",
    "layout.cad_parts[].join.hub_l": "Длина ступицы, мм.",
    "layout.cad_parts[].join.weld": "Сварной маршрут (null — не применяется).",
    "layout.cad_parts[].side": "Сторона детали: A — вход, B — выход (крышки .07A/.07B).",
    "layout.output.fl_txt": "Готовая строка вывода для SPEC-11 (фланец или причина его неприменимости).",
    "layout.cad_parts[].join.seat": "true — схема «опорный обод .12A в отверстии бурта/кольца» (Д-102 п. 2).",
    "layout.cad_parts[].join.axial": "Осевые штифты (в seat-схеме false — их нет).",
    "layout.cad_parts[].join.r_seat": "Радиус опорного обода = радиус отверстия бурта/кольца, мм.",
    "layout.cad_parts[].join.ring": "Кольцо-бурт .14 для CAD (L4).",
    "layout.cad_parts[].join.ring.r0": "Радиус отверстия кольца, мм.",
    "layout.cad_parts[].join.ring.r1": "Наружный радиус кольца, мм.",
    "layout.cad_parts[].join.ring.L": "Длина кольца, мм.",
    "layout.cad_parts[].join.ring.w": "Ширина кольца, мм.",
    "layout.cad_parts[].join.fit": "Посадка опорного обода (seat_fit), например H7/js6.",

    # --- шпонки, вал, эксцентрик, массы, детали ---------------------------
    "keys": "Таблица шпонок призматических (specs/shafts.yaml → keys.table, Д-109): первая "
            "строка с d ≤ d_max; одна для входа и выхода в ступице (CP-90).",
    "keys[].d_max": "Верхняя граница Ø вала для шпонки, мм.",
    "keys[].b": "Ширина шпонки b, мм.",
    "keys[].h": "Высота шпонки h, мм.",
    "keys[].t1": "Глубина паза вала t1, мм.",
    "keys[].t2": "Глубина паза ступицы t2, мм.",
    "shaft": "Расчёт входного вала: Ø, напряжения, момент на эксцентрике.",
    "shaft.d": "Принятый Ø вала, мм.",
    "shaft.bore": "Ø отверстия полого вала, мм; 0 — сплошной.",
    "shaft.link": "Тип соединения эксцентрик–вал: key | flat | integral | spline | press.",
    "shaft.eta": "КПД передачи, принятый в расчёте.",
    "shaft.ecc_share": "Доля входного момента на один эксцентрик.",
    "shaft.M": "Момент на валу, Н·мм.",
    "shaft.T_in": "Момент на входе (с учётом КПД), Н·мм.",
    "shaft.T_e": "Момент на одном эксцентрике, Н·мм.",
    "shaft.tau": "τ кручения вала, МПа.",
    "shaft.tau_allow": "[τ] кручения вала, МПа.",
    "shaft.d_req": "Требуемый по кручению Ø вала, мм.",
    "shaft.tau_basis": "Определяющий критерий [τ] (Д-110): fatigue — усталость τ₋₁/(K_τ·S), "
                       "static — текучесть 0.58·σт/S_т, override — переопределение в проработке, "
                       "default — умолчание без материала.",
    "shaft.sigma_crush": "[σсм] шпонки, МПа = min(σт вала, .03, шпонки)/S_см (Д-110).",
    "shaft.crush_basis": "Деталь, лимитирующая [σсм]: shaft | ecc (.03) | key (шпонка) | override | default.",
    "shaft.grade": "Марка вала .15 — первая проходящая из products.15.material (Д-110); null — не подобрана.",
    "shaft.state": "Термообработка, для которой взяты свойства марки (materials.yaml → state).",
    "shaft.props": "Источник свойств: materials.yaml (σ₋₁ — оценка 0.43·σв, если нет sigma_m1) | по умолчанию.",
    "shaft.blank": "Заготовка вала: пруток stock.yaml Ø ≥ d + 2·припуск.",
    "shaft.bore_max": "Наибольшее отверстие полого вала, мм, при котором проходят τ и стенка у паза; "
                      "null — не проходит и сплошной.",
    "shaft.rejected": "Отказы марок .15 с причинами: справочник, заготовка, τ, σсм (Д-110).",
    "shaft.rejected[].grade": "Марка.",
    "shaft.rejected[].why": "Причина отказа.",
    "link": "Соединение эксцентрик–вал: тип, напряжения, размеры шпонки.",
    "link.type": "Тип соединения: key | flat | integral | spline | press.",
    "link.sigma": "σсм соединения, МПа.",
    "link.b": "Ширина шпонки b, мм.",
    "link.h": "Высота шпонки h, мм.",
    "link.t1": "Глубина паза вала t1, мм.",
    "link.t2": "Глубина паза в эксцентрике t2, мм.",
    "link.lp": "Длина шпонки/соединения, мм.",
    "link.sigma_allow": "[σсм] соединения, МПа.",
    "ecc": "Эксцентрик .03: размеры, дисбаланс, балансировка, ряды.",
    "ecc.De": "Наружный Ø эксцентрика, мм.",
    "ecc.t": "Толщина (длина по оси) эксцентрика, мм.",
    "ecc.a": "Эксцентриситет (смещение оси эксцентрика от оси вала), мм; стенка на тонкой стороне = De/2 − a − d/2.",
    "ecc.d_shaft": "Ø отверстия под вал, мм.",
    "ecc.key_b": "Ширина шпоночного паза, мм.",
    "ecc.key_t2": "Глубина паза в эксцентрике t2, мм.",
    "ecc.m_brg_g": "Масса подшипника эксцентрика, г.",
    "ecc.m_brg_est": "true — масса подшипника взята оценкой.",
    "ecc.groove_r": "Радиус канавки облегчения (null — нет).",
    "ecc.U": "Дисбалансы эксцентрика, г·мм.",
    "ecc.U.disk": "Дисбаланс диска, г·мм.",
    "ecc.U.brg": "Дисбаланс подшипника, г·мм.",
    "ecc.U.bodies": "Дисбаланс тел качения, г·мм.",
    "ecc.U.sum": "Суммарный дисбаланс до балансировки, г·мм.",
    "ecc.bal": "Балансировка: число и Ø отверстий, остаточный дисбаланс.",
    "ecc.bal.n": "Число отверстий балансировки, шт.",
    "ecc.bal.d": "Ø отверстия балансировки, мм.",
    "ecc.bal.r": "Радиус окружности отверстий, мм.",
    "ecc.bal.U_rem": "Дисбаланс, снимаемый отверстиями, г·мм.",
    "ecc.bal.res": "Остаточный дисбаланс, г·мм.",
    "ecc.bal.holes": "Углы отверстий балансировки, °.",
    "ecc.rows": "Ряды эксцентриков (пакет): углы и стенки под шпонку.",
    "ecc.rows[].row": "Номер ряда (1…N).",
    "ecc.rows[].phi": "Угол поворота ряда относительно ряда 1, °.",
    "ecc.rows[].key_angle": "Угол паза этого ряда от эксцентриситета, °.",
    "ecc.rows[].key_wall": "Стенка под шпоночным пазом, мм.",
    "mass": "Массово-инерционные характеристики пакета.",
    "mass.ecc_g": "Масса эксцентриков, г.",
    "mass.brg_g": "Масса подшипников эксцентриков, г.",
    "mass.shaft_g": "Масса входного вала, г.",
    "mass.sum_g": "Суммарная масса, г.",
    "mass.J_in": "Момент инерции входа, г·мм².",
    "mass.J_out": "Момент инерции выхода, г·мм².",
    "parts": "Детали проработки (суффикс имени = <ID>.<позиция>-<name>).",
    "parts[].id": "ID детали для генератора чертежей.",
    "parts[].name": "Наименование детали.",
    "parts[].variant": "Буква исполнения детали (A, B, C…).",
    "parts[].key_angle": "Угол шпоночного паза детали, °.",
    "parts[].rows": "Ряды детали.",
    "parts[].base": "Позиция спецификации (01, 02, 03, 07, 09…).",
}

# Шаблоны для повторяющихся узлов: '*' — любой сегмент (материал), '#' — номер.
PATTERNS = [
    (r"layout.blank.alt_fit.*.D", "Ø трубы альтернативного материала, мм."),
    (r"layout.blank.alt_fit.*.s", "Стенка трубы альтернативного материала, мм."),
    (r"layout.blank.alt_fit.*.note", "Примечание по заготовке альтернативного материала."),
    (r"layout.join.variants\[\].fit.*.D", "Ø подходящей трубы, мм."),
    (r"layout.join.variants\[\].fit.*.s", "Стенка подходящей трубы, мм."),
    (r"layout.join.variants\[\].fit.*.note", "Примечание по трубе."),
    (r"layout.join.variants[].pins.(d|n|F|tau|sig_wall|sig_hub|tau_edge|L|pitch|t|need|l|des|key|hole12|seat|r0|fit|L_r|w)",
     None),                              # см. GENERIC_PINS
    (r"layout.join.pick.pins.(d|n|F|tau|sig_wall|sig_hub|tau_edge|L|pitch|t|need|l|des|key|hole12|seat|r0|fit|L_r|w)",
     None),
    (r"layout.parts.#", "Позиция спецификации .NN: обозначение детали с буквой исполнения (ключ — строка «09», не число)."),
    (r"layout.var.#", "Буква исполнения детали этой позиции (A, B, C…)."),
    (r"layout.var_name.#", "Полное обозначение исполнения детали этой позиции."),
    (r"layout.output.grooves.(ext|int).s", "s — толщина стопорного кольца по ГОСТ (мм)."),
    (r"layout.output.grooves.(ext|int).m", "m — ширина осевой канавки под кольцо, мм (допуск H13)."),
    (r"layout.output.grooves.(ext|int).d2", "d2 — Ø дна канавки под кольцо, мм."),
]

# Общие комментарии для штифтов соединения: одинаковы в pick и variants[].
GENERIC_PINS = {
    "d": "Ø штифта, мм (ГОСТ 24296-93, m6).",
    "n": "Число штифтов, шт (делитель числа окон сепаратора).",
    "F": "Сила на штифт, Н.",
    "tau": "τ среза штифта, МПа.",
    "sig_wall": "σсм стенки .02, МПа.",
    "sig_hub": "σсм ступицы/обода .12, МПа.",
    "tau_edge": "τ среза к торцу, МПа.",
    "L": "Длина соединения / пояса по оси, мм.",
    "pitch": "Шаг штифтов по окружности, мм.",
    "t": "Толщина стенки под штифтом, мм.",
    "need": "Требуемая длина штифта (стенка + pin_depth_k·d), мм.",
    "l": "Длина штифта по ГОСТ 24296-93, мм.",
    "des": "Обозначение штифта («Штифт 3×8 ГОСТ 24296-93»).",
    "key": "Ключ vendor_prices.yaml → pins (P3x8).",
    "hole12": "Глубина гнезда в ступице/ободе .12: l − t + pin_gap, мм (Д-74).",
    "seat": "true — схема «опорный обод .12A в отверстии бурта/кольца» (Д-102 п. 2).",
    "r0": "Радиус обода = радиус отверстия бурта/кольца, мм.",
    "fit": "Посадка опорного обода по цилиндру (seat_fit), H7/js6.",
    "L_r": "Длина кольца-бурта .14, мм.",
    "w": "Ширина кольца-бурта .14, мм = max(t_tech, k_fit·d).",
}


# Общий словарь по последнему сегменту: последний рубеж, когда специфичного описания нет.
# Тексты нейтральные, но верные для любого узла с таким именем листа.
GENERIC = {
    "D": "Наружный диаметр, мм.",
    "d": "Диаметр посадки/отверстия, мм.",
    "t": "Толщина (стенка), мм.",
    "s": "Толщина стенки/детали, мм.",
    "m": "Ширина по оси, мм.",
    "L": "Длина по оси, мм.",
    "l": "Длина, мм.",
    "n": "Число элементов, шт.",
    "w": "Ширина, мм.",
    "h": "Высота/толщина, мм.",
    "r0": "Внутренний радиус, мм.",
    "r1": "Наружный радиус, мм.",
    "r_j": "Радиус осей штифтов, мм.",
    "r_h": "Радиус заплечика .09 (r_h = da/2), мм.",
    "fit": "Посадка.",
    "note": "Примечание.",
    "material": "Материал.",
    "margin": "Запас, мм.",
    "scheme": "Схема соединения.",
    "geom": "Геометрия узла.",
    "pins": "Штифты и проверки прочности.",
    "ring": "Кольцо-бурт .14.",
    "ring_blank": "Заготовка кольца .14.",
    "tube": "Труба заготовки.",
    "bar": "Пруток заготовки.",
    "sheet": "Лист заготовки.",
    "need": "Требуемые размеры, мм.",
    "alt_fit": "Заготовки по материалам-альтернативам.",
    "variants": "Перебранные варианты.",
    "pick": "Выбранный вариант.",
    "house": "Отказ по корпусу.",
    "rej": "Отказ по заготовке.",
    "des": "Обозначение по стандарту.",
    "key": "Ключ каталога или шпонка.",
    "F": "Сила, Н.",
    "tau": "Касательное напряжение τ, МПа.",
    "sig_wall": "σсм стенки, МПа.",
    "sig_hub": "σсм ступицы, МПа.",
    "sig_ring": "σсм кольца, МПа.",
    "tau_edge": "τ среза к торцу, МПа.",
    "U": "Дисбаланс, г·мм.",
    "theta": "Угол, °.",
    "phi": "Угол, °.",
}

# ---------------------------------------------------------------------------
# Документ (эмиттер — общий, egm/doc_yaml.py)
# ---------------------------------------------------------------------------

class _Designs(doc_yaml.Doc):
    """Проработки шага 2: шапка файла и таблица комментариев этого документа."""
    HEADER = HEADER
    GLOSSARY = GLOSSARY
    PATTERNS = PATTERNS
    GENERIC = GENERIC
    EXTRA = GENERIC_PINS


_DOC = _Designs()


def comment(path):
    """Комментарий к пути ключа (совместимость с прежним API модуля)."""
    return _DOC.comment(path)


def dump(res):
    """Список записей проработок -> текст specs/ptk_designs.yaml."""
    return _DOC.dump(res)


def load_specs(specs_dir=None):
    """Проработки шага 2 -> list. Читает .yaml; нет — старый .json (переходный путь)."""
    d = Path(specs_dir) if specs_dir else Path(__file__).resolve().parents[1] / "specs"
    y, j = d / f"{FILE}.yaml", d / f"{FILE}.json"
    if y.exists():
        if yaml is None:
            raise ValueError("PyYAML не установлен: pip install pyyaml (чтение specs/ptk_designs.yaml)")
        data = yaml.safe_load(y.read_text(encoding="utf-8"))
        return data or []
    if j.exists():
        return json.loads(j.read_text(encoding="utf-8"))
    return []


def self_test():
    """Эмиттер: кавычки для номеров позиций, комментарии у каждого ключа, round-trip."""
    res = [{"id": "PTK-T", "name": "K1", "ok": True, "errors": [], "warnings": ["w"],
            "layout": {"code": "L4", "parts": {"09": "61810", "02": "02C"},
                       "b09": {"id": "61810", "d": 50.0, "da": 52.0},
                       "output": {"grooves": {"int": {"s": 1.7, "m": 1.9, "d2": 62,
                                                      "std": "ГОСТ 13943-86"},
                                               "ext": {"s": 2.0, "m": 2.2, "d2": 47,
                                                       "std": "ГОСТ 13942-86"}},
                                  "s_ob": 9.06},
                       "join": {"pick": {"pins": {"d": 3.0, "n": 10, "hole12": 5.0, "seat": True}}}},
            "keys": [{"d_max": 38, "b": 10}]}]
    txt = dump(res)
    back = yaml.safe_load(txt)
    assert back == res, (back, res)                      # типы и значения сохранены
    assert '"09":' in txt and '"02":' in txt, txt        # номера позиций — строки в кавычках
    assert "# Ø заплечика da" in txt                     # комментарий у ключа
    assert "# m — ширина осевой канавки под кольцо" in txt  # обновлённый шаблон
    assert "# Глубина гнезда в ступице/ободе" in txt     # общий словарь штифтов
    assert "# Ширина шпонки b" in txt
    return True
===== END FILE =====

### Генерация code-first документа (образец для egm/shaft_doc.py)

===== FILE: egm/doc_yaml.py (строки 1–224) =====
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
===== END FILE =====

===== FILE: egm/ptk_doc.py (строки 1–285) =====
"""egm/ptk_doc.py — выход шага 1 (SPEC-10, расчёт ПТК) в КОММЕНТИРОВАННЫЙ YAML.

Пишет main.py run_calc: specs/ptk_configs.yaml. Прежний ptk_configs.json читался, но не
объяснял смысл ~130 сокращённых ключей (R_sum, Drol_max, t_hold, M_H, sep_web, a_w…).
Здесь над каждым ключом стоит комментарий, в шапке — глоссарий сокращений.

Эмиттер — общий, egm/doc_yaml.py (Д-106). Таблица комментариев этого документа ниже:
GLOSSARY — точные пути, PATTERNS — повторяющиеся узлы (ряды, детали, позиции шайб),
GENERIC — последний рубеж по имени листа.
"""

from pathlib import Path

from egm import doc_yaml

FILE = "ptk_configs"                    # specs/ptk_configs.yaml (выход шага 1, Д-106)

HEADER = """\
# ============================================================================
# ptk_configs.yaml — результаты шага 1 «Расчёт» (SPEC-10).
# Пишет МАШИНА: python main.py calc --publish → specs/ptk_configs.yaml
#
# Руками НЕ править: теряется на следующем прогоне. Управляющие параметры шага 1 —
# specs/ptk_input.yaml (диапазоны перебора) и specs/vendor_prices.yaml (тела качения,
# подшипники, штифты, цены); стартовые значения пределов — там же.
#
# Формат — комментированный YAML (Д-106): каждый ключ снабжён комментарием, в шапке
# глоссарий. Данные те же, что были в ptk_configs.json: шаг 2 читает этот файл как
# ОПУБЛИКОВАННЫЙ вход (связка шаг 1 → шаг 2, Д-79).
#
# СОКРАЩЕНИЯ
#   u           число тел качения в одном ряду (в исполнении — сумма по рядам).
#   z           число зубьев/окон сепаратора = u + 1 (запас на подрез профиля).
#   R_Σ (R_sum) наименьший радиус наружного профиля по подрезу и перемычке сепаратора.
#   a_ω (a_w)   coefficient профиля: смещение центра дуги; больше — меньше угол давления.
#   α (alpha_max) максимальный угол давления на зубе, °.
#   D_г (Dgen)  диаметр генератора волн (подшипник/магнит), мм.
#   d_root, d_tip  диаметры впадин и вершин зубьев венца, мм.
#   sep_web     перемычка (толщина тела) сепаратора между окнами, мм.
#   d_bc        диаметр окружности крепёжных отверстий венца, мм.
#   d_out       наружный диаметр венца, мм.
#   M_H, M_B    моменты, выдерживаемые венцом (H — holder) и подшипником генератора (B), Н·мм.
#   t_hold      момент удержания венца крепежом и посадкой, Н·мм.
#   Drol_max    наибольший допустимый диаметр тела качения для этого исполнения, мм.
#   ecc         эксцентрик .03; De — наружный Ø, t — толщина, a — эксцентриситет.
#   U           дисбаланс, г·мм; res — остаточный после балансировки.
#   φ (phi)     угол поворота ряда, °; cage — угловое смещение окна сепаратора, °.
# ============================================================================
"""

GLOSSARY = {
    # --- исполнение --------------------------------------------------------
    "u": "Число тел качения в одном ряду, шт (в исполнении — сумма по рядам).",
    "roller": "Ключ тела качения из vendor_prices.yaml → rollers (R_D3x8, B_D3…).",
    "Drol": "Ø тела качения, мм.",
    "id": "ID исполнения: PTK-<u>-<тело>-<отверстия>-<хэш геометрии> (Д-80); хэш — от geom.",
    "n": "Число окон (гнёзд) сепаратора, шт.",
    "z": "Число зубьев профиля сепаратора = u + 1: запас на подрез профиля.",
    "a_w": "Коэффициент профиля a_ω: смещение центра дуги; больше — меньше угол давления.",
    "R_sum": "Наименьший R_Σ наружного профиля — максимум по подрезу и перемычке сепаратора, мм (Д-38).",
    "R_by": "Чем определён R_Σ: «подрез» (профиль зуба) или «сепаратор» (перемычка).",
    "Dgen": "Ø генератора волн (подшипник или магнит), мм.",
    "bearing": "Подшипник генератора (618xx) при gen = bearing; иначе null.",
    "gen": "Тип генератора волн: bearing | eccentric | magnet.",
    "d_root": "Ø впадин зубьев венца, мм.",
    "d_tip": "Ø вершин зубьев венца, мм.",
    "alpha_max": "Максимальный угол давления на зубе, ° (ограничение зацепления).",
    "r_tip": "Радиус вершины зуба, мм.",
    "sep_web": "Перемычка сепаратора между окнами (толщина тела), мм.",
    "holes": "Отверстия крепления венца: «8×M4+2шт Ø4» — n×резьба + штифты.",
    "mount": "Схема крепления венца: резьба × число + шаг (M4x8P2).",
    "d_bc": "Ø окружности крепёжных отверстий венца, мм.",
    "d_out": "Наружный Ø венца, мм.",
    "width": "Ширина пакета (осевая длина исполнения), мм.",
    "Drol_max": "Наибольший допустимый Ø тела качения для исполнения, мм.",
    "t_hold": "Момент удержания венца крепежом и посадкой, Н·мм.",
    "M_H": "Момент, который выдерживает венец (крепёж и посадка), Н·мм.",
    "M_B": "Момент, который выдерживает подшипник генератора, Н·мм.",
    "M": "Принятый момент исполнения M = min(M_H, M_B), Н·мм.",
    "M_by": "Чем ограничен момент: «венец» | «подшипник».",
    "ring_variants": "Число вариантов исполнения венца (фаз), шт.",
    "ok": "Итог: true — исполнение прошло проверки; false — причины в errors.",
    "errors": "Отказы: исполнение не строится (габарит, стенка, прочность).",
    "warnings": "Предупреждения: построено, но есть замечания (оценки, границы).",
    "tech": "Технологические ограничения, влияющие на исполнение.",
    "excluded": "Причина исключения исполнения из выдачи (пусто — не исключено).",

    # --- фазовка рядов -----------------------------------------------------
    "phasing": "Фазовка рядов тел качения: один ряд = одно окно сепаратора со смещением.",
    "phasing[].row": "Номер ряда (1…N).",
    "phasing[].phi": "Угол поворота ряда относительно ряда 1, °.",
    "phasing[].delta_p": "Смещение ряда в долях шага тел p, °.",
    "phasing[].s": "Угловое смещение окна ряда для равномерного износа, °.",
    "phasing[].cage": "Угловое положение окна сепаратора для этого ряда, °.",
    "phasing[].variant": "Буква варианта венца (A, B, C…): варианты различаются смещением окон.",
    "phasing[].s_arc_mm": "То же смещение по дуге, мм.",

    # --- детали ------------------------------------------------------------
    "parts": "Детали исполнения с их вариантами (суффикс файла: <ID>.<позиция><вариант>).",
    "parts[].id": "ID детали для генератора чертежей.",
    "parts[].name": "Наименование детали.",
    "parts[].variant": "Буква варианта детали (A, B, C…).",
    "parts[].s": "Смещение окон (угол), °.",
    "parts[].s_arc_mm": "Смещение окон по дуге, мм.",
    "parts[].rows": "Номера рядов, в которых применяется этот вариант.",
    "parts[].pos": "Позиция детали по оси (0 — перед первым рядом).",
    "parts[].key_angle": "Угол шпоночного паза детали от эксцентриситета, °.",

    # --- геометрия (входит в хэш ID) ---------------------------------------
    "geom": "Снимок геометрии исполнения: из него считается хэш ID (Д-80), он же вход CAD.",
    "geom.rev": "Ревизия расчётной геометрии: меняется при изменении формул (сбрасывает хэши ID).",
    "geom.u": "Число тел качения в ряду, шт.",
    "geom.gen": "Тип генератора волн: bearing | eccentric | magnet.",
    "geom.roller": "Тело качения из каталога (vendor_prices.yaml → rollers).",
    "geom.roller.type": "Тип тела: roller (ролик) | ball (шарик).",
    "geom.roller.d": "Ø тела качения, мм.",
    "geom.roller.l": "Длина ролика, мм (у шарика равна d).",
    "geom.roller.a_w": "Переопределение a_ω для этого тела (null — из limits).",
    "geom.roller.wall_min": "Переопределение минимальной стенки для этого тела (null — из limits).",
    "geom.bearing": "Подшипник генератора (d, D, B) при gen = bearing; иначе null.",
    "geom.bearing.d": "Ø отверстия подшипника, мм.",
    "geom.bearing.D": "Ø наружный, мм.",
    "geom.bearing.B": "Ширина, мм.",
    "geom.limits": "Пределы шага 1, при которых получено исполнение (входят в хэш ID).",
    "geom.limits.a_k": "Коэффициент a_k профиля (зазор/подрез).",
    "geom.limits.r_tip_min": "Минимальный радиус вершины зуба, мм.",
    "geom.limits.sep_web_min": "Минимальная перемычка сепаратора, мм.",
    "geom.limits.shaft_d_min": "Минимальный Ø входного вала, мм.",
    "geom.limits.ecc_wall_min": "Минимальная стенка эксцентрика у паза шпонки, мм.",
    "geom.limits.wall_min": "Минимальная стенка деталей, мм.",
    "geom.limits.row_gap": "Осевой зазор между рядами, мм.",
    "geom.limits.rows": "Число рядов тел качения, шт.",
    "geom.limits.row_phases": "Заданные фазы рядов, ° (по умолчанию 0/90/180/270).",
    "geom.limits.d_bc_step": "Шаг округления d_bc, мм.",
    "geom.limits.d_out_step": "Шаг округления d_out, мм.",
    "geom.limits.dgen_step": "Шаг округления Dgen, мм.",
    "geom.limits.sep_gap": "Зазор сепаратора, мм.",
    "geom.ring_holes": "Отверстия крепления венца (Д-16).",
    "geom.ring_holes.bolt": "Резьба крепёжных винтов (M4).",
    "geom.ring_holes.n": "Число винтов, шт.",
    "geom.ring_holes.pins": "Число штифтов фиксации, шт.",
    "geom.ring_holes.pin_d": "Ø штифтов, мм.",
    "geom.ring_holes.head_margin": "Запас под головку винта, мм.",
    "geom.fastener": "Крепёж из таблицы fasteners (для d_bc и запаса под головку).",
    "geom.fastener.d_clear": "Ø отверстия под винт (с зазором), мм.",
    "geom.fastener.dk": "Ø головки винта, мм.",

    # --- сепаратор .02 -----------------------------------------------------
    "sep": "Сепаратор (.02): размеры и раскладка окон по рядам.",
    "sep.n": "Число окон, шт.",
    "sep.r_in": "Внутренний радиус, мм.",
    "sep.r_out": "Наружный радиус, мм.",
    "sep.w": "Ширина окна, мм.",
    "sep.h": "Высота окна, мм.",
    "sep.length": "Осевая длина сепаратора, мм.",
    "sep.web": "Перемычка между окнами, мм.",
    "sep.rows": "Ряды окон сепаратора.",
    "sep.rows[].row": "Номер ряда (1…N).",
    "sep.rows[].cage": "Угловое положение окна в ряду, °.",
    "sep.rows[].z0": "Начало ряда по оси от торца сепаратора, мм.",

    # --- эксцентрик .03 ----------------------------------------------------
    "ecc": "Эксцентрик (.03): размеры, дисбаланс, балансировка, ряды.",
    "ecc.De": "Наружный Ø эксцентрика, мм.",
    "ecc.t": "Толщина (длина по оси), мм.",
    "ecc.a": "Эксцентриситет (смещение оси), мм; стенка на тонкой стороне De/2 − a − d/2.",
    "ecc.d_shaft": "Ø отверстия под входной вал, мм.",
    "ecc.key_b": "Ширина шпоночного паза, мм.",
    "ecc.key_t2": "Глубина паза в эксцентрике t2, мм.",
    "ecc.m_brg_g": "Масса подшипника эксцентрика, г.",
    "ecc.m_brg_est": "true — масса подшипника взята оценкой.",
    "ecc.groove_r": "Радиус канавки облегчения (null — нет).",
    "ecc.U": "Дисбалансы эксцентрика, г·мм.",
    "ecc.U.disk": "Дисбаланс диска, г·мм.",
    "ecc.U.brg": "Дисбаланс подшипника, г·мм.",
    "ecc.U.bodies": "Дисбаланс тел качения, г·мм.",
    "ecc.U.sum": "Суммарный дисбаланс до балансировки, г·мм.",
    "ecc.bal": "Балансировка: отверстия и остаточный дисбаланс.",
    "ecc.bal.n": "Число отверстий балансировки, шт (0 — не помещаются).",
    "ecc.bal.d": "Ø отверстия балансировки, мм.",
    "ecc.bal.r": "Радиус окружности отверстий, мм.",
    "ecc.bal.U_rem": "Дисбаланс, снимаемый отверстиями, г·мм.",
    "ecc.bal.res": "Остаточный дисбаланс, г·мм.",
    "ecc.bal.holes": "Координаты отверстий балансировки (x, y), мм.",
    "ecc.rows": "Ряды эксцентриков (пакет).",
    "ecc.rows[].row": "Номер ряда (1…N).",
    "ecc.rows[].phi": "Угол поворота ряда относительно ряда 1, °.",
    "ecc.rows[].key_angle": "Угол шпоночного паза этого ряда от эксцентриситета, °.",
    "ecc.rows[].key_wall": "Стенка под шпоночным пазом, мм.",

    # --- межрядная шайба .05 -----------------------------------------------
    "spacer": "Межрядная шайба (.05): размеры и позиции по оси.",
    "spacer.r_in": "Внутренний радиус, мм.",
    "spacer.d_out": "Наружный Ø, мм.",
    "spacer.h_end": "Толщина концевых шайб, мм.",
    "spacer.h_mid": "Толщина средних шайб, мм.",
    "spacer.web": "Перемычка (тело) шайбы, мм.",
    "spacer.pos": "Позиции шайб по оси.",
    "spacer.pos[].pos": "Номер позиции (0 — перед первым рядом).",
    "spacer.pos[].z": "Осевая координата позиции, мм.",
    "spacer.pos[].h": "Толщина шайбы в позиции, мм.",
    "spacer.pos[].variant": "Буква варианта шайбы (A, B…).",
}

PATTERNS = [
    (r"phasing[]", "Ряд фазовки: угол, смещение окна, вариант венца."),
    (r"parts[]", "Деталь исполнения: ID, наименование, вариант, применяемые ряды."),
    (r"sep.rows[]", "Ряд окон сепаратора: угловое положение и начало по оси."),
    (r"ecc.rows[]", "Ряд эксцентрика: угол поворота и паза шпонки."),
    (r"spacer.pos[]", "Позиция шайбы по оси."),
]

GENERIC = {
    "row": "Номер ряда (1…N).",
    "phi": "Угол, °.",
    "variant": "Буква варианта (A, B, C…).",
    "name": "Наименование.",
    "id": "Идентификатор.",
    "type": "Тип.",
    "d": "Ø, мм.",
    "D": "Наружный Ø, мм.",
    "n": "Число элементов, шт.",
    "h": "Высота/толщина, мм.",
    "w": "Ширина, мм.",
    "z": "Осевая координата, мм.",
    "z0": "Начало по оси, мм.",
}


class _Configs(doc_yaml.Doc):
    """Результаты шага 1: шапка файла и таблица комментариев этого документа."""
    HEADER = HEADER
    GLOSSARY = GLOSSARY
    PATTERNS = PATTERNS
    GENERIC = GENERIC


_DOC = _Configs()


def comment(path):
    """Комментарий к пути ключа."""
    return _DOC.comment(path)


def dump(rows):
    """Список исполнений шага 1 -> текст specs/ptk_configs.yaml."""
    return _DOC.dump(rows)


def load_specs(specs_dir=None):
    """Исполнения шага 1 -> list. Читает .yaml; нет — старый .json (переходный путь)."""
    d = Path(specs_dir) if specs_dir else Path(__file__).resolve().parents[1] / "specs"
    y, j = d / f"{FILE}.yaml", d / f"{FILE}.json"
    if y.exists():
        return doc_yaml.load(y) or []
    if j.exists():
        import json
        return json.loads(j.read_text(encoding="utf-8"))
    return []


def self_test():
    """Комментарии покрывают все ключи записи шага 1; YAML читается обратно."""
    rec = {"id": "PTK-T", "u": 10, "z": 11, "R_sum": 11.0, "R_by": "подрез", "ok": True,
           "errors": [], "warnings": [], "sep": {"n": 10, "rows": [{"row": 1, "z0": 0.5}]},
           "ecc": {"De": 10.0, "U": {"sum": 4.87}, "bal": {"holes": []}},
           "geom": {"rev": 1.0, "limits": {"rows": 4.0, "row_phases": [0.0, 90.0]}},
           "phasing": [{"row": 1, "phi": 0.0, "variant": "A"}]}
    txt = dump([rec])
    assert doc_yaml.yaml.safe_load(txt) == [rec], txt
    miss = []
    def scan(n, p=""):
        if isinstance(n, dict):
            for k, v in n.items():
                q = f"{p}.{k}" if p else str(k)
                if not comment(q):
                    miss.append(q)
                scan(v, q)
        elif isinstance(n, list):
            for x in n:
                scan(x, p + "[]")
    scan(rec)
    assert not miss, miss
    return True
===== END FILE =====

===== FILE: templates/SPEC-11_PTK_DESIGN.md.tmpl (строки 1–30) =====
# SPEC-11 — проработка исполнений ПТК (шаг 2, Д-48)

> Code-first: `python main.py` из `specs/ptk_design_input.yaml` и `specs/ptk_configs.json`
> (шаг 1, SPEC-10), код `egm/ptk_design.py`. НЕ ПРАВИТЬ РУКАМИ — правится вход (INS-10, шаг 2).

Проработок: {n_all}, прошли проверки: {n_ok}. Детали проработки строит
`python -m egm.cad <ID>.03<вар>-<проработка>` или `python -m egm.cad <ID> --design <проработка> --assy` (INS-30).

## Сводка

{summary}

## Детали проработки

{parts}

## Номенклатура

{nomenclature}

## Конструктивы L1–L4

{layouts}

{workpieces}

## Расчёт

{theory}

===== END FILE =====

### Точки входа

===== FILE: main.py (строки 1–100) =====
"""Точка входа: python main.py [calc|design|all] [--publish]. Код выхода 0 — все проверки.

Шаги (Д-79): calc — шаг 1 «Расчёт» (SPEC-10, ptk_configs.yaml из ptk_input.yaml +
vendor_prices.yaml); design — шаг 2 «Проработка» (SPEC-11, ptk_designs.yaml из
ptk_design_input.yaml по ОПУБЛИКОВАННОМУ specs/ptk_configs.yaml — связка выход шага 1 →
вход шага 2); all (по умолчанию) — весь прогон, как прежде: шаг 1 → шаг 2 по его
результату → проверки products → каталог.

Конфигурация — configs/application.yaml (Д-79): пути, ссылки на пучок конфигов
(configs:), разделы продуктов (products.PTK — входы шагов 1 и 2), механизм чертежей (cad:).

out/specs/   — code-first спецификации и БД -> переносятся в specs/   (Д-79)
out/reports/ — отчёты прогона               -> переносятся в reports/ (Д-79)
--publish    — скопировать самому: reports — всегда, specs — только при коде 0.
"""
import json
import re
import shutil
import sys
from pathlib import Path

from egm import doc_yaml, ptk_doc, catalog_doc, design_doc, catalog, config, naming, products, ptk, ptk_design, ptk_force, ptk_parts, ptk_profile, shaft_doc, shafts
from egm.cad import (assy as cad_assy, freecad as cad_freecad, ptk_ring, ptk_sep, ptk_spacer,
                     step as cad_step, techdraw as cad_techdraw)

ROOT = Path(__file__).resolve().parent
APP = config.load_app()                     # общий конфиг приложения (Д-79)
PATHS = APP.get("paths") or {}
SPECS = ROOT / PATHS.get("specs", "specs")      # каталоги — application.yaml (Д-79)
REPORTS = ROOT / PATHS.get("reports", "reports")
TPL = ROOT / PATHS.get("templates", "templates")
OUT = ROOT / PATHS.get("out", "out")
DEST = {"specs": SPECS, "reports": REPORTS}


def write(kind, name, text):
    """kind: 'specs' | 'reports' (Д-79)."""
    d = OUT / kind
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8", newline="\n")


FIELD_RE = re.compile(r"\{([A-Za-z_]\w*)\}")


def fill(tpl, **kw):
    """Подстановка полей {name} шаблона за один проход -> (текст, отсутствующие поля).

    Не str.format: в шаблоне LaTeX ($D_\\text{ш}$), его скобки — не поля. Заменяются
    только переданные ключи; прочие {…} и скобки в подставленных значениях не трогаются."""
    missing = sorted(k for k in kw if "{" + k + "}" not in tpl)
    text = FIELD_RE.sub(lambda m: str(kw[m[1]]) if m[1] in kw else m[0], tpl)
    return text, missing


def fill_self_test():
    t, miss = fill(r"$D_\text{ш}$ {a} {b} {x}", a=1, b="{a}", c=0)
    assert t == r"$D_\text{ш}$ 1 {a} {x}" and miss == ["c"], (t, miss)
    return True


def publish(ok):
    for kind, dst in DEST.items():
        if kind == "specs" and not ok:
            print("publish: specs/ не обновлены — есть непрошедшие проверки")
            continue
        src = OUT / kind
        if not src.exists():
            continue
        dst.mkdir(exist_ok=True)
        for f in sorted(src.iterdir()):
            if f.is_file():
                shutil.copy2(f, dst / f.name)
                print(f"publish: {kind}/{f.name}")


def run_ptk(prices):
    """SPEC-10: калькулятор ПТК по входу шага 1 (application.yaml → products.PTK, Д-79)."""
    try:
        lim, mounts, fast, mode = ptk.load_config(
            config.load(config.cfg_file(APP, "products.PTK.configs.input")))
    except (KeyError, ValueError, TypeError) as e:
        return [f"products.PTK.configs.input: {e!r}"]
    rows = ptk.to_rows(ptk.sweep(prices["rollers"], prices.get("bearings", {}), lim, mounts,
                                 fast, mode), mounts)
    write("specs", ptk_doc.FILE + ".yaml", ptk_doc.dump(rows))
    table, errs, warns, excl = [], [], [], []
    for r in rows:
        if r["excluded"]:                                # Д-45: не молча — в конец SPEC-10
            excl.append(f"| {r['id']} | {r['u']} | {r['roller']} | {r['gen']} | {r['excluded']} |")
            continue
        m = f"{r['M']:g} ({r['M_by']})" if r["M"] else "—"
        gen = (r["bearing"] or "—") if r["gen"] == "bearing" else "эксцентрик"
        st = ("OK" if r["ok"] else "нет") + (f" ({', '.join(r['tech'])})" if r["tech"] else "")
        table.append(f"| {r['id']} | {r['u']} | {r['roller']} | {r['Drol']} | "
                     f"{r['Drol_max'] or '—'} | "
                     f"{r['n']} | {r['z']} | {r['a_w']} | {gen} | "
                     f"{r['Dgen'] or '—'} | {r['d_root']} | "
                     f"{r['alpha_max'] or '—'} | "
                     f"{(r['holes'] + ' (' + r['mount'] + ')') if r['holes'] else '—'} | "
===== END FILE =====

===== FILE: main.py (строки 140–250) =====
    return [f"catalog: {e}" for e in rep["errors"]]


def run_design(cfg_rows, require=False):
    """SPEC-11: проработка выбранных исполнений, шаг 2 (Д-48).

    cfg_rows — исполнения шага 1 (ptk_configs.yaml): полный прогон — свежие из
    out/specs/, режим design — опубликованные specs/ (связь выход шага 1 → вход
    шага 2, Д-79)."""
    if not config.cfg_file(APP, "products.PTK.configs.design_input").exists():
        if require:
            return ["products.PTK.configs.design_input: файл не найден — "
                    "проработки designs[] не заданы"]
        return []
    if cfg_rows is None:
        if require:
            return ["specs/ptk_configs.yaml: не найден — сначала шаг 1: "
                    "python main.py calc --publish (Д-79)"]
        return []
    try:
        lim = ptk.load_config(
            config.load(config.cfg_file(APP, "products.PTK.configs.input")))[0]
        stock = config.cfg_file(APP, "configs.stock")
        extra = {"prods": config.load(config.cfg_file(APP, "configs.products")),
                 "bears": config.load(
                     config.cfg_file(APP, "configs.vendor_prices")).get("bearings", {}),
                 "pins": config.load(
                     config.cfg_file(APP, "configs.vendor_prices")).get("pins", {}),
                 "stock": config.load(stock) if stock.exists() else None}
        res = ptk_design.run(config.load(
            config.cfg_file(APP, "products.PTK.configs.design_input")), cfg_rows, lim, extra)
    except (KeyError, ValueError, TypeError) as e:
        return [f"входные конфиги шага 2 (Д-79): {e!r}"]
    write("specs", design_doc.FILE + ".yaml", design_doc.dump(res))
    tpl = (TPL / "SPEC-11_PTK_DESIGN.md.tmpl").read_text(encoding="utf-8")
    text, missing = fill(tpl, **ptk_design.md(res))
    write("specs", "SPEC-11_PTK_DESIGN.md", text)
    tpl12 = (TPL / "SPEC-12_SHAFTS.md.tmpl").read_text(encoding="utf-8")   # CP-91 этап 3, Д-107
    text12, miss12 = fill(tpl12, **shaft_doc.md(res))
    write("specs", "SPEC-12_SHAFTS.md", text12)
    fails = [f"SPEC-11: в шаблоне нет полей {missing}"] if missing else []
    return fails + ([f"SPEC-12: в шаблоне нет полей {miss12}"] if miss12 else [])


def main(argv):
    args = argv[1:]
    mode = "all"
    if args and args[0] in ("calc", "design", "all"):
        mode = args.pop(0)
    for kind in DEST:
        shutil.rmtree(OUT / kind, ignore_errors=True)
    fails = []
    if mode in ("all", "calc"):         # шаг 1: проверки ПО + расчёт по диапазону (SPEC-10)
        for name, test in (("doc_yaml", doc_yaml.self_test), ("ptk_doc", ptk_doc.self_test),
                           ("catalog_doc", catalog_doc.self_test),
                           ("design_doc", design_doc.self_test),
                           ("config", config.self_test), ("ptk", ptk.self_test),
                           ("naming", naming.self_test),
                           ("catalog", catalog.self_test), ("products", products.self_test),
                           ("ptk_profile", ptk_profile.self_test), ("cad", ptk_ring.self_test),
                           ("fill", fill_self_test), ("step", cad_step.self_test),
                           ("freecad", cad_freecad.self_test),
                           ("force", ptk_force.self_test), ("parts", ptk_parts.self_test),
                           ("sep_svg", ptk_sep.self_test), ("spacer", ptk_spacer.self_test),
                           ("assy", cad_assy.self_test),
                           ("techdraw", cad_techdraw.self_test),
                           ("techdraw_sheet", __import__("egm.cad.techdraw_sheet", fromlist=["self_test"]).self_test),
                           ("hub", __import__("egm.cad.ptk_hub", fromlist=["self_test"]).self_test),
                           ("materials", __import__("egm.materials", fromlist=["self_test"]).self_test),
                           ("materials_cfg", __import__("egm.materials", fromlist=["check_repo"]).check_repo),
                           ("srccheck", __import__("egm.srccheck", fromlist=["self_test"]).self_test),
                           ("join", __import__("egm.ptk_join", fromlist=["self_test"]).self_test),
                           ("shafts", shafts.self_test),
                           ("shafts_cfg", shafts.check_repo),
                           ("shaft_doc", shaft_doc.self_test),
                           ("design", ptk_design.self_test)):
            try:
                test()
            except AssertionError as e:
                fails.append(f"{name}.self_test: {e!r}")
            except Exception as e:      # CP-45: не AssertionError — тоже строка в checks.md, прогон идёт
                import traceback
                f = traceback.extract_tb(e.__traceback__)[-1]
                fails.append(f"{name}.self_test: {e!r} ({f.filename.replace(chr(92), '/').rsplit('/', 1)[-1]}:{f.lineno})")
        try:
            prods = config.load(config.cfg_file(APP, "configs.products"))
            prices = config.load(config.cfg_file(APP, "configs.vendor_prices"))
            fails += products.check_app(APP, prods)   # Д-79: разделы продуктов есть в реестре
            fails += run_ptk(prices)
            cfg_path = OUT / "specs"
            rows = ptk_doc.load_specs(cfg_path) if cfg_path.exists() else None
            if mode == "all":           # шаг 2 — по свежим исполнениям шага 1
                fails += run_design(rows)
            if cfg_path.exists():
                fails += products.check(prods,
                                        ptk_doc.load_specs(cfg_path))
            if mode == "all":
                fails += run_catalog(prices)
        except (KeyError, ValueError, TypeError) as e:
            fails.append(f"входные конфигурации: {e!r}")
    elif mode == "design":              # шаг 2 — по ОПУБЛИКОВАННОМУ шагу 1 (Д-79)
        cfg_path = SPECS
        rows = ptk_doc.load_specs(cfg_path) if cfg_path.exists() else None
        fails += run_design(rows, require=True)
    # TODO(CP-03): cost.report(); TODO(CP-04): машины по naming.MACHINES (HMC + VMC)
    write("reports", "checks.md", "# Проверки прогона (code-first, НЕ ПРАВИТЬ РУКАМИ)\n\n"
          + ("\n".join(f"- {f}" for f in fails) or "все пройдены") + "\n")
    ok = not fails
    print("OK" if ok else "FAIL", *fails, sep="\n")
    if "--publish" in args:
        publish(ok)
===== END FILE =====

### CAD: как вал .15 живёт в сборке сейчас (этап 4 — отдельный патч)

===== FILE: egm/cad/assy.py (строки 1–11) =====
"""Сборка ПТК в один STEP (Д-49): дерево «исполнение → ряд k → детали», слои, цвета, метаданные.

Система корпуса: ось z — ось вала, z = 0 — торец пакета (как z0 окон сепаратора);
угол 0° — впадина 0 венца ряда 1; отверстия всех венцов пакета совпадают (Д-19).
Ряд k (φk, s_k из ptk.phasing): венец .01<вар> повёрнут на −s_k; эксцентрик .03<вар> — на φk,
паз шпонки тогда у всех рядов на key_angle; подшипник .08 — центр a_ω на угле φk; тела .04 —
ptk_profile.bodies(θe = φk + s_k), повёрнутые на −s_k, — попадают в окна .02 (cage, Д-46).
Детали .01–.03 — те же PartModel и step.solid, что у STEP деталей; .04, .08, вал — примитивы.
Одинаковые детали — одно определение и экземпляры с положением (тела — rows·n экземпляров).
Сохранённые виды AP242 (Views) OCCT не пишет — предлагаемые виды в <ID>.assy.json (OQ-14).
"""
===== END FILE =====

===== FILE: egm/cad/assy.py (строки 17–69) =====
from egm import products, ptk_profile
from egm.cad import (ptk_collar, ptk_cover, ptk_ecc, ptk_hub, ptk_ring, ptk_sep, ptk_spacer, step,
                     techdraw)

LAYERS = {"01": ("01_RING", "венец"), "02": ("02_CAGE", "сепаратор"),
          "03": ("03_ECC", "эксцентрик"), "04": ("04_BODIES", "тела качения"),
          "05": ("05_SPACER", "межрядные шайбы"), "07": ("07_COVER", "крышки"),
          "08": ("08_BEARING", "подшипник генератора"), "09": ("09_BEARING_OUT", "подшипник выхода"),
          "10": ("10_BEARING_IN", "подшипники входного вала"),
          "11": ("11_DIST", "дистанционные кольца эксцентриков"), "12": ("12_HUB", "ступица выхода"),
          "13": ("13_LEAF", "дно-лист"),
          "14": ("14_COLLAR", "кольцо-бурт"),
          "ref": ("REF", "примитивы: вал")}
COLORS = {"01": (0.55, 0.57, 0.60), "02": (0.80, 0.60, 0.20), "03": (0.30, 0.50, 0.80),
          "04": (0.85, 0.20, 0.20), "05": (0.45, 0.47, 0.52), "08": (0.20, 0.65, 0.30),
          "07": (0.62, 0.64, 0.68), "09": (0.20, 0.55, 0.25), "10": (0.25, 0.60, 0.35),
          "11": (0.35, 0.55, 0.85), "12": (0.75, 0.50, 0.20), "13": (0.60, 0.45, 0.30),
          "14": (0.70, 0.55, 0.25),
          "ref": (0.70, 0.70, 0.70)}
VIEWS = [{"name": "ISO", "dir": [1, -1, 1], "layers": "все"},
         {"name": "по оси", "dir": [0, 0, 1], "layers": "все"},
         {"name": "сбоку", "dir": [1, 0, 0], "layers": "все"},
         {"name": "без венцов и сепаратора", "dir": [1, -1, 1], "layers": "03, 04, 08, REF"}]
SCHEMA = "AP242DIS"
ALIAS = {"01": "RING", "02": "CAGE", "03": "ECC", "04": "BODY", "05": "SPACER",
         "07": "COVER", "08": "BEARING", "09": "BRG_OUT", "10": "BRG_IN", "11": "DIST",
         "12": "HUB", "13": "LEAF", "14": "COLLAR", "ref": "SHAFT"}   # Д-52: имена узлов STEP — только латиница
_ENT = re.compile(r"#(\d+)\s*=\s*([A-Z0-9_]+)\s*\((.*?)\)\s*;", re.S)
_TOK = re.compile(r"'EGM(\d+)'")


def _nn(pid):
    return pid.split(".", 1)[1][:2]


def _base(pid):
    """ID детали без суффикса проработки (Д-48): <ID>.03B-K8 -> <ID>.03B."""
    head, _, tail = pid.partition(".")
    return f"{head}.{tail.split('-')[0]}" if tail else pid


def _txt(v):
    return f"{v:g}" if isinstance(v, float) else str(v)


def _shaft(cfg):
    """Вал (REF) -> (z0, длина): с конструктивом шага 2 — от .07A до второй .10 в ступице."""
    lay = cfg.get("layout") or {}
    cov, cup, b10 = lay.get("covers"), lay.get("cup") or {}, lay.get("b10") or {}
    if cov and cup.get("z_in"):
        z0 = -cov["tA"] - 5.0
        return z0, cup["z_in"] + b10.get("B", 0.0) - z0
    return -5.0, cfg["sep"]["length"] + 10
===== END FILE =====

===== FILE: instructions/INS-30_CAD.md (строки 23–36) =====
## 2. Правила и flow

Место в цепочке (INS-10 §2): после шага 1 («Расчёт») и шага 2 («Проработка»).
Генератор читает **опубликованные** `specs/ptk_configs.yaml` и `specs/ptk_designs.yaml` —
они должны соответствовать текущему коду и конфигам: сначала
`python main.py --publish` с кодом выхода 0. Конфигурация механизма —
`configs/application.yaml` (Д-79, §7); ручной конфиг комплекта —
`specs/cad_set.yaml` (Д-61, §3), номенклатура — `specs/products.yaml`;
выход в `out/cad/` в git не хранится — чертёж воспроизводится командой по ID.

Для STEP нужен CadQuery: `pip install cadquery`. Без него строятся только SVG,
в выводе «step: пропущен». Для `.FCStd` — установленный FreeCAD (§7); без него
«freecad: пропущен».

===== END FILE =====

===== FILE: instructions/INS-30_CAD.md (строки 175–183) =====
## 9. Новый генератор детали

1. `egm/cad/<имя>.py`: `build(cfg, part, row) -> PartModel` (`egm/cad/model.py`)
   и `self_test()`; рендеры `svg.render` и `step.export` общие для всех деталей (Д-32);
   альтернативный экспорт .FCStd — общий, из STEP (§7), в генераторе не нужен.
   Размеры и легенда подписываются обозначениями колонок SPEC-10.
2. Регистрация в `egm/cad/__main__.py → GENERATORS`, self_test — в `main.py`.
3. `"cad": "<имя>"` у позиции в `specs/products.yaml`.

===== END FILE =====

### Регистры и инструкции

===== FILE: specs/DECISIONS.md (строки 161–176) =====
- Д-107: (2026-11-12; CP-91) входной вал — ПРОДУКТ с номенклатурой, а не блок параметров в проработке: номенклатура — specs/shafts.yaml → shafts: {SH-<d>-<link>: {name, d, bore, link, tau_allow, sigma_crush, wall_min, length, applies_to, note}}; продукт SH зарегистрирован в specs/products.yaml (source: shafts.yaml, spec: SPEC-12_SHAFTS.md, cad: ptk_shaft) и в configs/application.yaml → products.SH; деталь ПТК .15 получает product: SH, а designs[].shaft задаётся ссылкой {id: SH-10-KEY} (полный блок — переходный формат с предупреждением). Одна конфигурация переиспользуется всеми проработками и продуктами (ПТК, ГК). Разрешение записи — egm/shafts.py: приоритет «переопределение проработки > поле номенклатуры > умолчание кода», результат — тот же словарь shaft, что ждёт ptk_design.design(). ID стабилен и разбирается регуляркой; неизвестный ID — ошибка прогона. Code-first представление — SPEC-12_SHAFTS.md (генератор egm/shaft_doc.py на общем эмиттере doc_yaml: реестр конфигураций, применимость, проверки по применяющим проработкам, производные для .03/.10). Номенклатура заведена сразу на три конфигурации: SH-08-KEY (K8), SH-10-KEY (K10), SH-20-KEY (Ø20, под увеличенный редуктор rev13.1). Согласованность полей с egm/ptk_design.py: tau_allow/sigma_crush/wall_min/bore/link переходят как есть.
- Д-108: (2026-11-12; CP-91 этап 5) организация инструкций: у каждой code-first спецификации есть отдельная инструкция в instructions/, и каждая инструкция ссылается на свою спецификацию — соответствие ведётся таблицей в instructions/README.md §3 («Инструкция → спецификация / БД → входные файлы»). Новая инструкция INS-40_SHAFTS.md (номенклатура валов: как добавить конфигурацию, что означает каждый параметр, как читать SPEC-12, порядок прогона, связь с проработками и CAD .15); ссылки на неё обязательны из instructions/README.md §3, INS-10_PTK_CALC.md §2 (шаг 2: shaft по ID) и INS-30_CAD.md (генератор .15). Обратные ссылки из инструкции на соответствующие §-и и на specs/shafts.yaml — обязательны. Правило распространяется на все последующие спецификации: спецификация без инструкции и без обратной ссылки считается незавершённой.
- Д-109: (2026-11-12; CP-91 этап 1, OQ-35 решён) таблица шпонок keys.table живёт в номенклатуре валов specs/shafts.yaml (ключ keys → table), а не во входе проработки: перенесена из specs/ptk_design_input.yaml без изменения значений (8 строк, d_max 8…44). Основание: паз — свойство сечения вала, а не проработки; таблица одна для входного вала и для выходного вала в ступице (CP-90), значит её место там, где задаётся сечение. Чтение — egm/ptk_design.keys_table(): путь products.SH.configs.shafts из configs/application.yaml (Д-79); пустая или отсутствующая таблица — ValueError. Ключ keys во входе проработки — ValueError со ссылкой на это решение (тихого игнорирования нет). SPEC-12_SHAFTS.md печатает таблицу разделом «Шпонки»; правка таблицы — правка номенклатуры, перепрогон main.py design --publish пересчитывает шпонки всех проработок.
- Д-110: (2026-11-12; CP-91, уточняет Д-107; по разбору ответа модели) допуски вала — РАСЧЁТНЫЕ, а не вход номенклатуры. specs/shafts.yaml → shafts.<ID>: вход — name, d, bore, link, applies_to, note; tau_allow и sigma_crush из записей убираются (ручное значение — только переопределением в проработке с обоснованием в note), wall_min — технологический минимум в DEFAULTS egm/shafts.py, length — по пакету (этап 4). Материал .15 подбирает калькулятор по тому же принципу, что .02 (Д-67/Д-68): марки products.15.material по порядку предпочтения, для каждой проверяется пруток Ø ≥ d + 2·припуск в stock.yaml, затем τ, шпонка и стенка полого вала; берётся первая проходящая, отказы остальных с причинами — в результат. Порядок марок НЕ меняется (первой остаётся 40Х; 45 — резерв, пока в stock.yaml нет прутков 45). [τ] = min(τ₋₁/(K_τ·S), 0.58·σт/S_т), τ₋₁ = 0.58·σ₋₁, σ₋₁ ≈ 0.43·σв при отсутствии в справочнике; [σсм] = min(σт вала, .03, шпонки)/S_см, материал шпонки — DEFAULTS (сталь 45). Коэффициенты K_τ (по типу соединения), S, S_т, S_см и припуск на пруток — DEFAULTS egm/shafts.py; свойства марок (σв, σт, σ₋₁, состояние термообработки, диапазон Ø, для которого они справедливы) — specs/materials.yaml (поля sigma_v, sigma_t, sigma_m1, state, d_range; значения сверить по ГОСТ 4543 / ГОСТ 1050 — OQ-36). Роль заниженного [τ] (покрывал неучтённый изгиб) переходит к запасу S; определяющий критерий (усталость или статика) выводится в результат. designs[].shaft.id — ID или СПИСОК ID (как список layout, Д-100): берётся наименьшая проходящая конфигурация, выбранный ID пишется в input.shaft_id. Вывод в ptk_designs.yaml → shaft и в SPEC-12: марка и состояние, источник свойств, [τ] с определяющим критерием, [σсм] с определяющей деталью, заготовка (пруток), bore_max (наибольшее отверстие, при котором проходит), отказы марок. Критерий приёмки CP-91 переписан на две проверки: (а) регресс рефакторинга — с переопределениями tau_allow 25 / sigma_crush 100 числа K8/K10 совпадают с прежними; (б) расчёт из материала — изменения чисел объяснены в SPEC-12. Замечание по факту: K8 и K10 в rev13.2 ОБА не проходят по τ (373.0 и 212.7 при [τ] = 25 МПа), поэтому расчётные допуски (30…39 МПа) статус не переворачивают — «отрицательный пример» K8 сохраняется сам собой, отдельно задавать его не нужно. Таблица шпонок — Д-109 (specs/shafts.yaml), в расчёте σсм участвует оттуда.
- Д-112: (2026-11-12; CP-91, закрывает OQ-36) свойства марок и коэффициенты допусков вала проверены по справочникам. **Материалы** (specs/materials.yaml): 40Х — ГОСТ 4543, пруток Ø25, закалка 860 °C (масло) + отпуск 500 °C: σв 980, σ0,2 785 МПа (норма ≥980/≥785; марочник 980/780), σ₋₁ 509 МПа (марочник для σв 960…980, σ0,2 870); 45 — ГОСТ 1050-2013, пруток Ø25, нормализация: σв 600, σ0,2 355 МПа, σ₋₁ 290 МПа. Прежние значения 40Х (785/640) были перепутаны: 785 — это σ0,2, а 640 — σв поковки КП 640, не прутка. Поля sigma_v/sigma_t/sigma_m1/state/d_range — источник расчёта; отсутствие sigma_m1 не ошибка (оценка 0.43·σв, консервативнее справочника). **Коэффициенты** (DEFAULTS egm/shafts.py): K_τ по типу соединения key 1.6 (справочный диапазон для шпоночного паза при кручении 1.4…1.7; взят верх — материал улучшенный, σв ≈ 980), flat 1.3, spline 1.5, integral 1.2, press 2.5; S 3.5 — запас по усталости, покрывающий НЕучтённый изгиб (роль прежнего заниженного [τ] = 15…30, Д-110), калиброван по 45: τ₋₁ = 0.58·290 = 168 МПа, [τ] = 168/(1.6·3.5) = 30 МПа = верх прежнего диапазона; S_т 2.0 (для валов 1.5…2.5); S_см 3.5 → [σсм] = 355/3.5 = 101 МПа (практика для неподвижного соединения сталь–сталь 100…150 МПа); tau_k 0.58 — консервативно (марочник 40Х даёт τ₋₁ = 240 МПа при σ₋₁ = 333, т.е. 0.72·σ₋₁). **Результат прогона** (rev13.3): [τ] 40Х 52.7 МПа (было 39.2 по оценке σ₋₁), [τ] 45 30.0 МПа; [σсм] 101.4 МПа (лимитирует шпонка 45); статика не лимитирует (0.58·785/2.0 = 228 МПа у 40Х). K8/K10 остаются «нет» (τ 373.0 / 212.7 МПа > 52.7), d_req 14.26 / 14.86 мм вместо 15.61 / 16.21. Дополнено 2026-11-12: заполнены и остальные марки, участвующие в номенклатуре, — ШХ15 (σв 2160 / σ0,2 1670 / σ₋₁ 652, закалка + отпуск 150 °C, ГОСТ 801-78), 40ХН2МА (1080 / 930 / 519), 38Х2МЮА (980 / 835 / 392 — нижняя граница марочника 392…480 взята консервативно), 30ХГСА (1080 / 830 / 470), 38Х2Н2МА (1080 / 930 / 363); для всех оценка σ₋₁ = 0.43·σв больше не нужна ([τ] при DEFAULTS: ШХ15 67.5, 40ХН2МА 53.8, 40Х 52.7, 30ХГСА 48.7, 38Х2МЮА 40.6, 38Х2Н2МА 37.6, 45 30.0 МПа; во всех случаях лимитирует усталость, статика даёт 241…484 МПа).

### Архив (поглощённые сводными, исторические)

Поглощённые сводными — состав в кластерах и группах выше; полные тексты и
разбивка — в [archive/DECISIONS-2026-10.md](archive/DECISIONS-2026-10.md). Исторические:

- Д-23: тег rev6 (историческое, состояние CP-19).
- Д-28: папка review_reports (механизм заменён bundle/INS-91).
- Д-50: уточнено Д-52 (имена узлов STEP — только латиница).
- Д-56: переведён на YAML (Д-67, CP-48).

===== END FILE =====

===== FILE: specs/DECISIONS.md (строки 165–176) =====
- Д-112: (2026-11-12; CP-91, закрывает OQ-36) свойства марок и коэффициенты допусков вала проверены по справочникам. **Материалы** (specs/materials.yaml): 40Х — ГОСТ 4543, пруток Ø25, закалка 860 °C (масло) + отпуск 500 °C: σв 980, σ0,2 785 МПа (норма ≥980/≥785; марочник 980/780), σ₋₁ 509 МПа (марочник для σв 960…980, σ0,2 870); 45 — ГОСТ 1050-2013, пруток Ø25, нормализация: σв 600, σ0,2 355 МПа, σ₋₁ 290 МПа. Прежние значения 40Х (785/640) были перепутаны: 785 — это σ0,2, а 640 — σв поковки КП 640, не прутка. Поля sigma_v/sigma_t/sigma_m1/state/d_range — источник расчёта; отсутствие sigma_m1 не ошибка (оценка 0.43·σв, консервативнее справочника). **Коэффициенты** (DEFAULTS egm/shafts.py): K_τ по типу соединения key 1.6 (справочный диапазон для шпоночного паза при кручении 1.4…1.7; взят верх — материал улучшенный, σв ≈ 980), flat 1.3, spline 1.5, integral 1.2, press 2.5; S 3.5 — запас по усталости, покрывающий НЕучтённый изгиб (роль прежнего заниженного [τ] = 15…30, Д-110), калиброван по 45: τ₋₁ = 0.58·290 = 168 МПа, [τ] = 168/(1.6·3.5) = 30 МПа = верх прежнего диапазона; S_т 2.0 (для валов 1.5…2.5); S_см 3.5 → [σсм] = 355/3.5 = 101 МПа (практика для неподвижного соединения сталь–сталь 100…150 МПа); tau_k 0.58 — консервативно (марочник 40Х даёт τ₋₁ = 240 МПа при σ₋₁ = 333, т.е. 0.72·σ₋₁). **Результат прогона** (rev13.3): [τ] 40Х 52.7 МПа (было 39.2 по оценке σ₋₁), [τ] 45 30.0 МПа; [σсм] 101.4 МПа (лимитирует шпонка 45); статика не лимитирует (0.58·785/2.0 = 228 МПа у 40Х). K8/K10 остаются «нет» (τ 373.0 / 212.7 МПа > 52.7), d_req 14.26 / 14.86 мм вместо 15.61 / 16.21. Дополнено 2026-11-12: заполнены и остальные марки, участвующие в номенклатуре, — ШХ15 (σв 2160 / σ0,2 1670 / σ₋₁ 652, закалка + отпуск 150 °C, ГОСТ 801-78), 40ХН2МА (1080 / 930 / 519), 38Х2МЮА (980 / 835 / 392 — нижняя граница марочника 392…480 взята консервативно), 30ХГСА (1080 / 830 / 470), 38Х2Н2МА (1080 / 930 / 363); для всех оценка σ₋₁ = 0.43·σв больше не нужна ([τ] при DEFAULTS: ШХ15 67.5, 40ХН2МА 53.8, 40Х 52.7, 30ХГСА 48.7, 38Х2МЮА 40.6, 38Х2Н2МА 37.6, 45 30.0 МПа; во всех случаях лимитирует усталость, статика даёт 241…484 МПа).

### Архив (поглощённые сводными, исторические)

Поглощённые сводными — состав в кластерах и группах выше; полные тексты и
разбивка — в [archive/DECISIONS-2026-10.md](archive/DECISIONS-2026-10.md). Исторические:

- Д-23: тег rev6 (историческое, состояние CP-19).
- Д-28: папка review_reports (механизм заменён bundle/INS-91).
- Д-50: уточнено Д-52 (имена узлов STEP — только латиница).
- Д-56: переведён на YAML (Д-67, CP-48).

===== END FILE =====
===== FILE: specs/DECISIONS.md (строки 207–208) =====
| OQ-35 | Где хранить таблицу шпонок keys.table (DIN 6885 / ГОСТ 23360): в specs/ptk_design_input.yaml (как сейчас — одна таблица на входной и выходной вал, CP-90) или перенести в specs/shafts.yaml как «номенклатуру сечения вала»? Влияет на то, чем задаётся паз: конфигурацией вала (шаг 2) или общей таблицей. Решение — Д-109: таблица перенесена в specs/shafts.yaml (паз — свойство сечения вала), вход проработки её не содержит, читает egm/ptk_design.keys_table() | решён (Д-109) |
| OQ-36 | Свойства марок для расчёта допусков вала (Д-110): в specs/materials.yaml нужны sigma_v (σв), sigma_t (σт), sigma_m1 (σ₋₁), state (нормализация / улучшение / закалка + отпуск) и d_range (диапазон Ø заготовки, для которого справедливы свойства) — табличные значения зависят и от термообработки, и от диаметра прутка. Сверить по ГОСТ 4543-2016 (40Х, 40ХН2МА, 38Х2МЮА), ГОСТ 1050-2013 (45), плюс коэффициенты K_τ по типу соединения, запасы S, S_т, S_см и припуск на пруток в DEFAULTS egm/shafts.py. Калибровка для сверки: 45 нормализованная (σв ≈ 600) при K_τ = 2.0 и S = 2.5 → [τ] ≈ 30 МПа; σт шпонки 355 при S_см = 3.5 → [σсм] ≈ 100 МПа (совпадает с нынешней заглушкой); 40Х улучшенная (σв ≈ 790) → [τ] ≈ 39 МПа. Решение — Д-112: свойства 40Х/45 и коэффициенты K_τ, S, S_т, S_см сверены по ГОСТ 4543 / ГОСТ 1050 и справочникам, занесены в materials.yaml и DEFAULTS egm/shafts.py | решён (Д-112) |
===== END FILE =====
===== FILE: specs/DECISIONS.md (строки 208–208) =====
| OQ-36 | Свойства марок для расчёта допусков вала (Д-110): в specs/materials.yaml нужны sigma_v (σв), sigma_t (σт), sigma_m1 (σ₋₁), state (нормализация / улучшение / закалка + отпуск) и d_range (диапазон Ø заготовки, для которого справедливы свойства) — табличные значения зависят и от термообработки, и от диаметра прутка. Сверить по ГОСТ 4543-2016 (40Х, 40ХН2МА, 38Х2МЮА), ГОСТ 1050-2013 (45), плюс коэффициенты K_τ по типу соединения, запасы S, S_т, S_см и припуск на пруток в DEFAULTS egm/shafts.py. Калибровка для сверки: 45 нормализованная (σв ≈ 600) при K_τ = 2.0 и S = 2.5 → [τ] ≈ 30 МПа; σт шпонки 355 при S_см = 3.5 → [σсм] ≈ 100 МПа (совпадает с нынешней заглушкой); 40Х улучшенная (σв ≈ 790) → [τ] ≈ 39 МПа. Решение — Д-112: свойства 40Х/45 и коэффициенты K_τ, S, S_т, S_см сверены по ГОСТ 4543 / ГОСТ 1050 и справочникам, занесены в materials.yaml и DEFAULTS egm/shafts.py | решён (Д-112) |
===== END FILE =====

===== FILE: specs/CODE_PLAN.md (строки 72–72) =====
| CP-91 | Д-107/Д-108/Д-109/Д-110: номенклатура входных валов как продукт SH. Этапы 1–3, 5 — патч rev13.3: egm/shafts.py (ID, resolve, DEFAULTS, подбор марки .15, допуски из материала, bore_max), egm/shaft_doc.py + templates/SPEC-12_SHAFTS.md.tmpl, ptk_design (shaft_id, список ID, поля shaft.*), materials.py props, materials.yaml σв/σт 40Х и 45 (предв., OQ-36), shafts.yaml без переходных полей, вход по ID, INS-40 + ссылки README §3/INS-10 §2/INS-30 §9. Этап 4 — CAD .15; этап 6 — K20/Ø20. Приёмка: (а) с переопределениями tau_allow 25 / sigma_crush 100 числа K8/K10 прежние; (б) штатно — изменения объяснены в SPEC-12, K8/K10 «нет» | egm/shafts.py, egm/shaft_doc.py, templates/SPEC-12_SHAFTS.md.tmpl, egm/ptk_design.py, egm/design_doc.py, egm/materials.py, main.py, specs/shafts.yaml, specs/ptk_design_input.yaml, specs/materials.yaml, instructions/INS-40_SHAFTS.md, instructions/README.md, instructions/INS-10_PTK_CALC.md, instructions/INS-30_CAD.md | Д-107, Д-108, Д-109, Д-110, OQ-36 | CP-90 | этапы 1–3, 5 — закрыт (прогон подтверждён заказчиком 2026-11-12): self-test OK, design --publish rc=0; регресс (а) с переопределениями 25/100 — K8 τ 373.0 / σсм 327.1 / d_req 17.94, K10 τ 212.7 / σсм 191.9 / d_req 18.54 (совпало с rev13.2); штатно (б) — 40Х, [τ] 39.2 (усталость), [σсм] 101.4 (лимитирует шпонка), d_req 15.61 / 16.21, оба «нет»; Д-112 закрыл OQ-36: [τ] 40Х 52.7 / 45 30.0, [σсм] 101.4 (шпонка), d_req 14.26 / 14.86; этап 4 (CAD .15), этап 6 (K20/Ø20) — открыты |
===== END FILE =====

===== FILE: instructions/README.md (строки 138–161) =====
## 3. Порядок работы с code-first спецификациями (Д-79)

Code-first спецификация — результат прогона `main.py`, руками она не правится.
Чтобы изменить результат, меняют **входные файлы** и запускают прогон заново.
Инструкция описывает, какие входные файлы есть, что означает каждый параметр
и как читать результат.

| Инструкция | Спецификация / БД | Входные файлы |
|---|---|---|
| [INS-10_PTK_CALC.md](INS-10_PTK_CALC.md) | `specs/SPEC-10_PTK_CALC.md`, `specs/SPEC-11_PTK_DESIGN.md`, `specs/ptk_configs.yaml`, `specs/ptk_designs.json` | `specs/ptk_input.yaml`, `specs/ptk_design_input.yaml`, `specs/vendor_prices.yaml` → `rollers`, `bearings` |
| [INS-20_CATALOG.md](INS-20_CATALOG.md) | `specs/catalog_hiwin_hg.yaml`, `specs/catalog_hiwin_hg_pairs.json`, `reports/catalog_report.md` | `docs/HG-Series-Catalog_opt.md`, `specs/vendor_prices.json` |
| [INS-40_SHAFTS.md](INS-40_SHAFTS.md) | `specs/SPEC-12_SHAFTS.md`, `specs/ptk_designs.yaml` → `shaft` | `specs/shafts.yaml`, `specs/materials.yaml`, `specs/stock.yaml`, `specs/products.yaml` → `PTK.parts.15.material` |

1. Правите входной файл — ручной конфиг `specs/*.yaml` (`ptk_input`, `ptk_design_input`,
   `vendor_prices`, `products`, `stock`; Д-79).
2. `python main.py` — результат в `out/specs/` и `out/reports/`.
3. Смотрите `out/reports/checks.md`: «все пройдены» = код выхода 0.
4. Переносите результат: вручную или `python main.py --publish` (Д-79).
5. Коммит.

Ручные конфиги — YAML: описание каждого параметра — комментарий рядом с ним (Д-79),
ключи `_comment` больше не используются. Неизвестный параметр (опечатка в имени) —
ошибка прогона, а не молчаливое игнорирование.

===== END FILE =====

===== FILE: instructions/INS-10_PTK_CALC.md (строки 25–50) =====
## 2. Правила и flow

| Этап | Команда | Вход | Выход |
|---|---|---|---|
| 1. Расчёт | `python main.py calc --publish` | `specs/ptk_input.yaml`, `specs/vendor_prices.yaml` | `specs/SPEC-10_PTK_CALC.md`, `specs/ptk_configs.yaml` |
| — выбор | **человек**: по SPEC-10 выбрать исполнение (ID) | SPEC-10 | исполнение для шага 2 |
| 2. Проработка | `python main.py design --publish` | **опубликованный** `specs/ptk_configs.yaml` (выход шага 1), `specs/ptk_design_input.yaml` | `specs/SPEC-11_PTK_DESIGN.md`, `specs/ptk_designs.yaml` |
| 3. Чертежи | `python -m egm.cad --spec specs/cad_set.yaml` | `specs/cad_set.yaml` + `ptk_configs.yaml` + `ptk_designs.yaml` | `out/cad/**.svg|.step` |

Связь шагов явная (Д-79): вход шага 2 — опубликованный результат шага 1
`specs/ptk_configs.yaml`. Шаг 2 гоняется отдельно, не пересчитывая шаг 1: прогнали шаг 1,
выбрали исполнение, вписали проработку в `designs[]`, прогнали шаг 2 — сколько угодно раз.
`python main.py` без аргументов — прежний полный прогон: проверки ПО, шаг 1, шаг 2 по его
же свежим исполнениям, проверка номенклатуры, каталог (INS-20).

Почему у шага 2 «вход из будущего»: `designs[].id` ссылается на результат шага 1, хотя
файл заполняется до его прогона — это нормально, порядок такой: шаг 1 → выбор → шаг 2.
Чтобы проработка не терялась при смене хэша шага 1 (правка параметров меняет ID),
`id` пишут **префиксом без хэша** (Д-51, пример — в `ptk_design_input.yaml`); уточнение
нескольких исполнений под одним префиксом — полями `bearing` / `gen`.

Порядок изменения результатов — code-first: правите ручной конфиг (`specs/*.yaml`) →
прогон → смотрите `out/reports/checks.md` («все пройдены» = код выхода 0) → переносите
`--publish` → коммит. Значения и их смысл — в комментариях конфигов (первоисточник, Д-79);
этот файл — про логику и следствия.

===== END FILE =====

---

## Отсутствующее (досылается по запросу)

- `egm/cad/ptk_hub.py` — образец генератора детали для этапа 4 (`ptk_shaft`).
- `egm/ptk_layout.py` — целиком; вал напрямую не участвует, но layout читает `d["output"]` и пересекается по ключам `shaft`.
- `specs/ptk_designs.yaml` — опубликованное состояние (эталон чисел для проверки (а)); 89 КБ, выдаётся отдельным файлом.
- `docs/HG-Series-Catalog_opt.md` — каталог (нужен только для `.10`/`.09`).
