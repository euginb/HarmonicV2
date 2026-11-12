# CTX-T — CP-91: номенклатура входных валов как продукт SH

**base:** `f962de160076ff3223e770f16c8bac827fb97125` · **ref:** `rev13.2` · **режим:** CTX-T (задача, INS-91B §4)
**Сформирован:** 2026-11-12 · **источник решений:** Д-107, Д-108, Д-109, CP-91

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

## Задача: номенклатура входных валов как продукт (CP-91, Д-107/Д-108)

### Что есть сейчас

Проработка ПТК задаётся в `specs/ptk_design_input.yaml` → `designs[]`. В каждой
записи блок `shaft:` — ПОЛНЫЙ набор параметров вала (d, bore, link, tau_allow,
sigma_crush, wall_min). Две проработки (K8, K10) различаются только `d` и
`output.link`, но описание вала продублировано целиком. Третья конфигурация
(Ø20) потребовала бы третьей копии блока.

Параметры вала читает `egm/ptk_design.py`: `design()` берёт `d["shaft"]` напрямую,
считает τ, шпонку по `keys.table` (таблица уже перенесена в `specs/shafts.yaml` —
Д-109, OQ-35 решён), стенки эксцентрика, массу/инерцию пакета. Таблицу шпонок
из входа проработки `ptk_design.run()` больше не берёт: `keys` во входе — `ValueError`,
штатное чтение — `keys_table()` через `products.SH.configs.shafts` (Д-79).
Валидация блока — только `link in LINKS` в `run()`; остальные поля берутся с
`.get(..., умолчание)`.

### Целевое состояние (Д-107)

1. **Номенклатура валов** — `specs/shafts.yaml`, ключ `shafts`, ID `SH-<d>-<link>`
   (например `SH-08-KEY`). Файл УЖЕ СОЗДАН в этой ревизии с тремя записями
   (`SH-08-KEY`, `SH-10-KEY`, `SH-20-KEY`); формат и комментарии — в нём самом.
2. **Продукт SH** — запись в `specs/products.yaml` (реестр изделий, SPEC-03) и
   раздел `products.SH` в `configs/application.yaml`. Вал перестаёт быть
   «настройкой проработки» и становится переиспользуемым продуктом: тем же
   `SH-10-KEY` будут пользоваться ПТК и (в будущем) ГК.
3. **Ссылка по ID** — в `designs[]` вместо блока `shaft:` пишется
   `shaft: {id: SH-10-KEY}` (плюс необязательные переопределения отдельных полей —
   см. п. 4 ниже). Деталь `.15` ПТК получает `product: SH`.
4. **Разрешение записи** — новый модуль `egm/shafts.py`: чтение `specs/shafts.yaml`,
   проверка ID/полей, слияние «запись номенклатуры + переопределения проработки»
   в тот же словарь, который сейчас ждёт `ptk_design.design()`. Приоритет:
   переопределение записи > поле номенклатуры > умолчание кода. Переопределения
   нужны для частных случаев (полый вал под конкретную проработку), но в
   `ptk_design_input.yaml` по умолчанию — только `id`.
5. **Code-first спецификация** — `specs/SPEC-12_SHAFTS.md` (генератор
   `egm/shaft_doc.py` на общем эмиттере `egm/doc_yaml.py` + шаблон
   `templates/SPEC-12_SHAFTS.md.tmpl`): таблица конфигураций × параметров,
   применимость (какие проработки/продукты используют), результаты проверок по
   каждой применяющей проработке, ссылка на `specs/shafts.yaml`.
6. **CAD** — генератор детали `.15` (`egm/cad/ptk_shaft.py`, имя в products.yaml →
   `cad: ptk_shaft`): вал по конфигурации (Ø, паз по `keys.table`, шейки под .03 и
   .10, длина по пакету). Сейчас `.15` в сборке — REF-примитив (OQ-32).
7. **Третья конфигурация Ø20** — `SH-20-KEY` уже в номенклатуре; для неё нужна
   проработка на увеличенном исполнении (rev13.1: PTK-063) — `name: K20`,
   `shaft: {id: SH-20-KEY}`, `layout: [L4, L3, L2]`, `output.link: flange`
   (как K10). Прогон покажет, проходит ли Ø20 по стенкам эксцентрика и шпонке.


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
    shaft: {id: SH-08-KEY}          # Д-107: ссылка на номенклатуру; полный блок — deprecated
    balance: {n_max: 3, wall: 1.0, drills: [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]}
    lighten: none
    output: {link: flange, d: 0.0, tau_allow: 25.0, sigma_crush: 130.0}
    layout: [L4, L3, L2]
```

Обратная совместимость: если в `shaft:` нет `id` (пришёл полный блок), прогон
НЕ падает — блок принимается как раньше, в `warnings` добавляется строка
«designs.<name>.shaft: полный блок устарел (Д-107) — заменить на {id: SH-…}».
Так старые входы и уже опубликованные `ptk_designs.yaml` остаются валидными.

### Состав SPEC-12_SHAFTS.md (целевой)

1. **Шпонки** — таблица `keys.table` из `specs/shafts.yaml` (d_max, b, h, t1, t2;
   DIN 6885 / ГОСТ 23360), одна для входного вала и выхода в ступице (Д-109).
2. **Реестр конфигураций** — таблица: ID, наименование, d, bore, link,
   tau_allow, sigma_crush, wall_min, примечание.
3. **Применимость** — по каждой конфигурации: продукт, проработки (K8/K10/K20),
   исполнения ПТК, к которым они привязаны.
4. **Проверки по применяющим проработкам** — τ вала против [τ], d_req, шпонка
   (b×h, σсм), стенка полого вала, стенки эксцентрика; статус ok/ошибка.
5. **Производные** — выбранная шпонка по каждой конфигурации, присоединительные
   размеры для `.03` (отверстие) и `.10` (шейка).
6. **Ссылки** — `specs/shafts.yaml` (вход), `ptk_designs.yaml` (результаты),
   INS-40 (инструкция).

### Результат проработки (ptk_designs.yaml)

Поле `input.shaft` остаётся эхом входа (полный разрешённый словарь — для
воспроизводимости), плюс новое `input.shaft_id: SH-08-KEY` (пусто, если вал
задан блоком). Комментарии к новым ключам — в `egm/design_doc.py` (GLOSSARY),
иначе сломается инвариант «комментарий у каждого ключа» (Д-105/Д-106);
проверяется прогоном `python main.py design --publish` и self_test `design_doc`.


## Ограничения и требования к патчу

1. **Не ломать текущие проработки.** `python main.py --publish` должен давать
   rc=0, а `ptk_designs.yaml` — те же числа для K8/K10, что до патча (кроме
   новых полей `input.shaft_id`). Проверять сравнением с зафиксированным
   состоянием (см. «Файлы» → ptk_designs.yaml).
2. **Один источник истины.** Параметры вала живут только в `specs/shafts.yaml`;
   в `ptk_design_input.yaml` — только ID. Никакого дублирования умолчаний в коде,
   кроме словаря `DEFAULTS` в `egm/shafts.py` (и он же — документация умолчаний).
   Таблица шпонок — тоже один источник: `specs/shafts.yaml` → `keys.table` (Д-109);
   ключ `keys` во входе проработки — `ValueError`, а не тихое игнорирование.
3. **ID стабилен.** `SH-<d>-<link>`; разбор ID — регуляркой, ошибка формата —
   `ValueError` с путём и допустимым примером. Неизвестный ID — ошибка прогона
   (в `checks.md`), не молчаливый пропуск.
4. **Никаких новых зависимостей.** PyYAML уже используется (`egm/config.py`,
   `egm/doc_yaml.py`).
5. **Стиль проекта.** Комментарии и докстринги — по-русски, ссылки на Д-##/CP-##;
   формат выходов — `egm/doc_yaml.py` (наследник `Doc`, таблицы GLOSSARY/PATTERNS/
   GENERIC, self_test на 100% покрытие комментариями).
6. **Спецификации code-first не правятся руками** (Д-79): `SPEC-12_SHAFTS.md`
   генерируется прогоном; шаблон — `templates/SPEC-12_SHAFTS.md.tmpl`.
7. **Инструкции — часть задачи** (Д-108, CP-91 этап 5): новая
   `instructions/INS-40_SHAFTS.md` (как править номенклатуру, что означает каждый
   параметр, как читать SPEC-12, порядок прогона) и ссылки на неё из
   `instructions/README.md` §3 (таблица «Инструкция → спецификация → входы»),
   `INS-10_PTK_CALC.md` §2 (шаг 2: `shaft: {id: …}` вместо блока) и
   `INS-30_CAD.md` (генератор `.15`). Обратная ссылка из инструкции на §-и
   спецификации обязательна.
8. **Реестры.** Новые решения/пункты — только через upd.md (Journal), текст
   существующих строк не переписывать целиком без необходимости.


---

## Файлы задачи

Ниже — свежие версии затрагиваемых файлов. Порядок: входные конфиги → код
расчёта → генерация документа → регистры.

Затрагиваемые, но НЕ включённые целиком (нужны только точечно):
`egm/ptk_layout.py` (layout считается по `d["output"]`, вал не участвует),
`egm/cad/*` (генератор `.15` — новый файл, образец — `egm/cad/ptk_hub.py`),
`specs/ptk_input.yaml` (шаг 1, вал не участвует), `specs/stock.yaml`,
`specs/vendor_prices.yaml` (только `pins`/`bearings`/`keys` — для `.15`).


### Карта репозитория

```
configs/  (1): application.yaml
docs/  (7): HG-Series-Catalog_opt.md, HG-Series-Catalog_opt.pdf, RU2359790C1.pdf, cnc_axes_guide.md, ptk_condition.png, ptk_crown_profile.png, Материалы-заготовки  для ГК.md
egm/  (19): __init__.py, calc_vptc.py, catalog.py, catalog_doc.py, config.py, design_doc.py, doc_yaml.py, materials.py, naming.py, products.py, ptk.py, ptk_design.py, ptk_doc.py, ptk_force.py, ptk_join.py, ptk_layout.py, ptk_parts.py, ptk_profile.py, srccheck.py
egm/cad/  (16): __init__.py, __main__.py, assy.py, freecad.py, model.py, ptk_collar.py, ptk_cover.py, ptk_ecc.py, ptk_hub.py, ptk_ring.py, ptk_sep.py, ptk_spacer.py, step.py, svg.py, techdraw.py, techdraw_sheet.py
instructions/  (7): INS-10_PTK_CALC.md, INS-20_CATALOG.md, INS-30_CAD.md, INS-90_AUDIT_BUNDLE.md, INS-91B_LOCAL.md, INS-91_CONTEXT_PREP.md, README.md
reports/  (3): cad_report.md, catalog_report.md, checks.md
specs/  (23): CANCELLED.md, CATALOGS.md, CODE_PLAN.md, DECISIONS.md, SPEC-01_NAMING.md, SPEC-02_PRECISION_EMBEDS.md, SPEC-03_PRODUCTS.md, SPEC-04_ARCHITECTURE.md, SPEC-10_PTK_CALC.md, SPEC-11_PTK_DESIGN.md, cad_set.yaml, catalog_hiwin_hg.yaml, catalog_hiwin_hg_pairs.json, concept_ptk.png, materials.yaml, products.yaml, ptk_configs.yaml, ptk_design_input.yaml, ptk_designs.yaml, ptk_input.yaml, shafts.yaml, stock.yaml, vendor_prices.yaml
templates/  (2): SPEC-10_PTK_CALC.md.tmpl, SPEC-11_PTK_DESIGN.md.tmpl
tools/  (10): context_bundle.py, create_pr.py, ctx_task.py, fix_diff.py, freecad_egm.py, freecad_meta.py, freecad_techdraw.py, import_graph.py, make_audit_bundle.py, upd_apply.py
```

### Граф импортов (tools/import_graph.py)

```
# Импорт-граф — корни: egm, tools, main.py

egm (1 строк)
  imports: -
  imported by: egm.cad.__main__, egm.cad.assy, egm.cad.ptk_ring, egm.catalog_doc, egm.design_doc, egm.materials, egm.ptk, egm.ptk_design, egm.ptk_doc, egm.ptk_force, egm.ptk_join, egm.ptk_layout, main
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
  imported by: egm.cad.__main__, egm.cad.assy, egm.materials, egm.ptk_design, egm.ptk_layout, main
egm.design_doc (536 строк)
  imports: egm, egm.doc_yaml
  imported by: egm.cad.__main__, main
egm.doc_yaml (224 строк)
  imports: -
  imported by: egm.catalog_doc, egm.design_doc, egm.ptk_doc, main
egm.materials (99 строк)
  imports: egm, egm.config
  imported by: egm.cad.assy, egm.ptk_join, egm.ptk_layout
egm.naming (71 строк)
  imports: -
  imported by: main
egm.products (64 строк)
  imports: -
  imported by: egm.cad.__main__, egm.cad.assy, main
egm.ptk (624 строк)
  imports: egm, egm.ptk_force, egm.ptk_parts, egm.ptk_profile
  imported by: egm.cad.__main__, egm.cad.ptk_ring, main
egm.ptk_design (638 строк)
  imports: egm, egm.config, egm.ptk_layout, egm.ptk_parts
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
egm.srccheck (51 строк)
  imports: -
  imported by: -
main (248 строк)
  imports: egm, egm.cad, egm.cad.assy, egm.cad.freecad, egm.cad.ptk_ring, egm.cad.ptk_sep, egm.cad.ptk_spacer, egm.cad.step, egm.cad.techdraw, egm.catalog, egm.catalog_doc, egm.config, egm.design_doc, egm.doc_yaml, egm.naming, egm.products, egm.ptk, egm.ptk_design, egm.ptk_doc, egm.ptk_force, egm.ptk_parts, egm.ptk_profile
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

===== FILE: specs/shafts.yaml (строки 1–97) =====
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
# Поля записи (значения по умолчанию — в JOIN-блоке расчёта, egm/ptk_design.py):
#   name        — наименование для спецификации и чертежа;
#   d           — Ø вала, мм: кручение, шпонка, стенки эксцентрика; он же Ø
#                 отверстия .03 и вала REF на чертежах;
#   bore        — Ø отверстия полого вала, мм; 0 — сплошной (τ растёт как 1/(1−β⁴));
#   link        — соединение эксцентрик–вал: key | flat | integral | spline | press;
#                 spline и press — только кручение (смятие не считается);
#                 flat — без смятия, в CAD круглое отверстие; integral — вал
#                 и эксцентрик одной деталью (CAD — CP-05);
#   tau_allow   — [τ] кручения, МПа; изгиб не считается, поэтому занижено
#                 (сталь 45: 15…30); τ > [τ] — отказ с требуемым d_req;
#   sigma_crush — [σсм] шпонки, МПа; σсм > [σ] — отказ;
#   wall_min    — минимальная стенка полого вала у паза, мм;
#   length      — габаритная длина вала, мм; null — не задана (считается по пакету:
#                 B пакета + посадки .03/.10 + выход под шпонку);
#   applies_to  — продукты, где конфигурация применяется (справочно, для SPEC-12);
#   note        — примечание: откуда взята, что подтвердить.
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
    tau_allow: 25.0
    sigma_crush: 100.0
    wall_min: 1.5
    length: null
    applies_to: [PTK]
    note: "Исходная конфигурация проработки K8 (PTK-050, rev12.x); параметры не менялись"

  # --- Ø10: проработка K10 (перенесено из ptk_design_input.yaml, rev13.2) ---
  SH-10-KEY:
    name: "Вал входной Ø10, соединение шпонкой"
    d: 10.0
    bore: 0.0
    link: key
    tau_allow: 25.0
    sigma_crush: 100.0
    wall_min: 1.5
    length: null
    applies_to: [PTK]
    note: "Исходная конфигурация проработки K10 (PTK-063, rev12.x); параметры не менялись"

  # --- Ø20: новая конфигурация (запрос заказчика, rev13.2) ------------------
  SH-20-KEY:
    name: "Вал входной Ø20, соединение шпонкой"
    d: 20.0
    bore: 0.0
    link: key
    tau_allow: 25.0
    sigma_crush: 100.0
    wall_min: 1.5
    length: null
    applies_to: [PTK]
    note: "Новая конфигурация rev13.2: Ø20 под увеличенный редуктор (rev13.1). bore/link/tau_allow/sigma_crush/wall_min — по умолчанию, подтвердить прогоном; полый вариант (bore > 0) — при необходимости отдельной записью SH-20-KEY-B<bore>"
===== END FILE =====

===== FILE: specs/ptk_design_input.yaml (строки 1–84) =====
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
    shaft:            # вал в эксцентрике
      # Д-107 (CP-91): целевой формат — {id: SH-08-KEY} — ссылка на номенклатуру
      # specs/shafts.yaml. Полный блок ниже — переходный формат: работает, но выдаёт
      # предупреждение «устарел (Д-107)».
      d: 8.0          # Ø вала, мм — кручение, шпонка, стенки эксцентрика; Ø отверстия .03 и вала REF на чертежах
      bore: 0.0       # отверстие полого вала, мм; 0 — сплошной; τ растёт как 1/(1−β⁴), стенка ≥ wall_min
      link: key       # соединение эксцентрик–вал: key | flat | integral | spline | press;
                      # spline, press — только кручение; flat — без смятия, в CAD круглое отверстие;
                      # integral — вал-эксцентрик заодно (CAD — CP-05)
      tau_allow: 25.0     # [τ] кручения, МПа; изгиб не считается, поэтому занижено (сталь 45: 15…30); τ > [τ] — статус «нет» и d_req
      sigma_crush: 100.0  # [σ см] шпонки, МПа; σ см > [σ] — «нет»
      wall_min: 1.5       # стенка полого вала у паза, мм
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
    shaft: {d: 10.0, bore: 0.0, link: key, tau_allow: 25.0, sigma_crush: 100.0, wall_min: 1.5}   # Д-107: → {id: SH-10-KEY}
    balance: {n_max: 3, wall: 1.0, drills: [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]}
    lighten: none
    output: {link: flange, d: 0.0, tau_allow: 25.0, sigma_crush: 130.0}   # Д-103/Д-104: момент — фланец на торце ступицы, шпонка — в гайке-опции
    layout: [L4, L3, L2]
===== END FILE =====

===== FILE: specs/products.yaml (строки 1–235) =====
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
      material: [40Х]                  # предварительно (OQ-21, OQ-32)
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

### Код расчёта

===== FILE: egm/ptk_design.py (строки 1–638) =====
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

from egm import config, ptk_layout, ptk_parts

LINKS = ("key", "flat", "integral", "spline", "press")
CALC = ("key", "flat", "integral")             # spline, press — только кручение вала
NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")
THEORY = (
    "Момент входного вала T_вх = M/(u·eta): M — допускаемый выходной момент SPEC-10, "
    "eta — оценка КПД из входа (η не считается, OQ-08). Доля эксцентрика T_э = ecc_share·T_вх: "
    "ряды сдвинуты по фазе, нагрузка между ними распределена неравномерно (OQ-15).\n\n"
    "Кручение вала: τ = 16·T_вх/(π·d_t³·(1 − β⁴)), d_t = d − t1 при шпонке (ослабление пазом), "
    "β = d_отв/d_t; d_req — диаметр, при котором τ = [τ]. Изгиб не считается, его покрывает "
    "заниженное [τ] (сталь 45 на предварительном этапе — 15…30 МПа).\n\n"
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


def design(cfg, d, lim, keys, extra=None):
    """Проработка одного исполнения -> запись ptk_designs.json."""
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
    ta = float(sh.get("tau_allow", 25.0))
    tau = 16 * T_in * 1e3 / (math.pi * d_t ** 3 * k4)
    d_req = (16 * T_in * 1e3 / (math.pi * ta * k4)) ** (1 / 3) + t1
    if tau > ta + 1e-9:
        err.append(f"вал Ø{dsh:g}: τ = {tau:.1f} > [τ] = {ta:g} МПа — нужен d ≥ {d_req:.1f} мм")
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
    lk = {"type": link, "sigma": None}
    if key:
        lp, kh = ecc["t"] - key["b"], key["h"] - key["t1"]
        sig = 2 * T_e * 1e3 / (dsh * kh * lp) if lp > 0 else 1e9
        sa = float(sh.get("sigma_crush", 100.0))
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
                      "tau_allow": ta, "d_req": round(d_req, 2)},
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


def run(inp, configs, lim, extra=None, keys=None):
    """ptk_design_input.yaml -> [запись]; ошибка входа — ValueError (в checks.md).

    keys — таблица шпонок; None — читается из номенклатуры валов (Д-109).
    """
    if inp.get("keys"):
        raise ValueError("ptk_design_input: ключ keys перенесён в specs/shafts.yaml → "
                         "keys.table (Д-109) — во входе проработки его быть не должно")
    keys = sorted(keys if keys is not None else keys_table(), key=lambda k: k["d_max"])
    out, names = [], set()
    for d in inp.get("designs", []):
        name = str(d.get("name", ""))
        if not NAME_RE.match(name) or name in names:
            raise ValueError(f"designs: имя «{name}» — латиница, цифры, _, без «-», уникальное (Д-48)")
        if d["shaft"].get("link", "key") not in LINKS:
            raise ValueError(f"designs.{name}.shaft.link: {d['shaft'].get('link')} — допустимы {LINKS}")
        names.add(name)
        cfg, why = select(configs, d)
        out.append(design(cfg, d, lim, keys, extra) if cfg else
                   {"id": d["id"], "name": name, "ok": False, "errors": [why], "warnings": [], "input": d})
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

===== FILE: egm/products.py (строки 1–64) =====
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
        elif sec.get("enabled") and not (prods[code].get("parts") or {}):
            fails.append(f"application.yaml: products.{code}: enabled, но номенклатура "
                         "в products.yaml пуста")
    return fails


def self_test():
    p = parse("PTK-063-R5X8-8M4P2-3F9A1C.01B")
    assert p == {"cfg": "PTK-063-R5X8-8M4P2-3F9A1C", "prod": "PTK", "nn": "01", "var": "B"}, p
    prods = {"PTK": {"parts": {"01": {"variant": "ring_phase"}}}}
    assert not check(prods, [{"parts": [{"id": "PTK-1-X.01A"}]}])
    assert check(prods, [{"parts": [{"id": "PTK-1-X.09"}]}])
    assert check(prods, [{"parts": [{"id": "bad"}]}])
    app_prods = {"PTK": {"parts": {"01": {}}}, "HD": {"parts": {}}}
    assert not check_app({"products": {"PTK": {"enabled": True},
                                       "HD": {"enabled": False}}}, app_prods)
    assert check_app({"products": {"XX": {"enabled": True}}}, app_prods)
    assert check_app({"products": {"HD": {"enabled": True}}}, app_prods)
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

### Комментарии-глоссарий результирующего YAML (куда добавить input.shaft_id)

===== FILE: egm/design_doc.py (строки 312–318) =====
    "keys": "Таблица шпонок призматических (specs/shafts.yaml → keys.table, Д-109): первая "
            "строка с d ≤ d_max; одна для входа и выхода в ступице (CP-90).",
    "keys[].d_max": "Верхняя граница Ø вала для шпонки, мм.",
    "keys[].b": "Ширина шпонки b, мм.",
    "keys[].h": "Высота шпонки h, мм.",
    "keys[].t1": "Глубина паза вала t1, мм.",
    "keys[].t2": "Глубина паза ступицы t2, мм.",
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

from egm import doc_yaml, ptk_doc, catalog_doc, design_doc, catalog, config, naming, products, ptk, ptk_design, ptk_force, ptk_parts, ptk_profile
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
    return [f"SPEC-11: в шаблоне нет полей {missing}"] if missing else []


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
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
===== END FILE =====

### Регистры и инструкции

===== FILE: specs/DECISIONS.md (строки 126–166) =====
- Д-107: (2026-11-12; CP-91) входной вал — ПРОДУКТ с номенклатурой, а не блок параметров в проработке: номенклатура — specs/shafts.yaml → shafts: {SH-<d>-<link>: {name, d, bore, link, tau_allow, sigma_crush, wall_min, length, applies_to, note}}; продукт SH зарегистрирован в specs/products.yaml (source: shafts.yaml, spec: SPEC-12_SHAFTS.md, cad: ptk_shaft) и в configs/application.yaml → products.SH; деталь ПТК .15 получает product: SH, а designs[].shaft задаётся ссылкой {id: SH-10-KEY} (полный блок — переходный формат с предупреждением). Одна конфигурация переиспользуется всеми проработками и продуктами (ПТК, ГК). Разрешение записи — egm/shafts.py: приоритет «переопределение проработки > поле номенклатуры > умолчание кода», результат — тот же словарь shaft, что ждёт ptk_design.design(). ID стабилен и разбирается регуляркой; неизвестный ID — ошибка прогона. Code-first представление — SPEC-12_SHAFTS.md (генератор egm/shaft_doc.py на общем эмиттере doc_yaml: реестр конфигураций, применимость, проверки по применяющим проработкам, производные для .03/.10). Номенклатура заведена сразу на три конфигурации: SH-08-KEY (K8), SH-10-KEY (K10), SH-20-KEY (Ø20, под увеличенный редуктор rev13.1). Согласованность полей с egm/ptk_design.py: tau_allow/sigma_crush/wall_min/bore/link переходят как есть.
- Д-108: (2026-11-12; CP-91 этап 5) организация инструкций: у каждой code-first спецификации есть отдельная инструкция в instructions/, и каждая инструкция ссылается на свою спецификацию — соответствие ведётся таблицей в instructions/README.md §3 («Инструкция → спецификация / БД → входные файлы»). Новая инструкция INS-40_SHAFTS.md (номенклатура валов: как добавить конфигурацию, что означает каждый параметр, как читать SPEC-12, порядок прогона, связь с проработками и CAD .15); ссылки на неё обязательны из instructions/README.md §3, INS-10_PTK_CALC.md §2 (шаг 2: shaft по ID) и INS-30_CAD.md (генератор .15). Обратные ссылки из инструкции на соответствующие §-и и на specs/shafts.yaml — обязательны. Правило распространяется на все последующие спецификации: спецификация без инструкции и без обратной ссылки считается незавершённой.
- Д-109: (2026-11-12; CP-91 этап 1, OQ-35 решён) таблица шпонок keys.table живёт в номенклатуре валов specs/shafts.yaml (ключ keys → table), а не во входе проработки: перенесена из specs/ptk_design_input.yaml без изменения значений (8 строк, d_max 8…44). Основание: паз — свойство сечения вала, а не проработки; таблица одна для входного вала и для выходного вала в ступице (CP-90), значит её место там, где задаётся сечение. Чтение — egm/ptk_design.keys_table(): путь products.SH.configs.shafts из configs/application.yaml (Д-79); пустая или отсутствующая таблица — ValueError. Ключ keys во входе проработки — ValueError со ссылкой на это решение (тихого игнорирования нет). SPEC-12_SHAFTS.md печатает таблицу разделом «Шпонки»; правка таблицы — правка номенклатуры, перепрогон main.py design --publish пересчитывает шпонки всех проработок.
#### Д-89 — ПТК — CAD и чертежи

Действующий набор принципов (тексты и разбивка членов — в [archive/DECISIONS-2026-10.md](archive/DECISIONS-2026-10.md)):

- Д-30: чертёж 2D строится аналитически из той же геометрии, что и 3D: *_geom() даёт замкнутый контур profile из сегментов (дуги; для точного профиля CP-08 — ломаная/сплайн), по нему строятся STEP и SVG; проекция из STEP — только дополнительные виды (CP-06); инструкция — INS-30.
- Д-32: чертежи: генератор детали строит модель egm/cad/model.py: PartModel (контур, отверстия, оси, размеры, метки, легенда); рендеры — svg.py (2D) и step.py (3D); размеры и легенда подписываются обозначениями колонок SPEC-10; ряд редуктора — --phase/--row; уточняет Д-30.
- Д-44: сборочные примитивы на чертежах деталей: egm/cad/model.py → Disk, PartModel.prims: тела (ptk_profile.bodies — на траектории (6) и окружности R_Σ генератора), подшипник (D, d) или эксцентрик (D_г), вал shaft_d_min, кольцо сепаратора R_Σ ± 1.1a_ω; тонкие цветные линии SVG, в STEP детали не входят; 3D-детали .02–.08 — CP-05, CP-28.
- Д-47: чертёж сепаратора .02 — развёртка втулки по Dm = 2RΣ (x — дуга от 0°, y — ось от торца, 1:1), окна всех рядов, ряд --row — основной линией, у рядов — z0 и поворот окон; Dс, dс, толщина hс, длины окружностей, шаг окон — сносками в легенде, не изображаются; PartModel.view = "unroll", svg.render_unroll; STEP без изменений.
- Д-49: сборка исполнения в один STEP: python -m egm.cad <ID> --assy → out/cad/<ID>/<ID>.step + <ID>.assy.json, egm/cad/assy.py; XCAF: изделие → ROWk → .01, .03, .08, .04 (одно определение, экземпляры с положением); .02 и вал REF — на уровне изделия; система корпуса: z — ось вала от торца пакета, 0° — впадина 0 венца ряда 1; слои STEP по позициям, цвета, имена ASCII (= ID), схема AP242DIS; метаданные — TDataStd_NamedData (в STEP при SetMetaMode у OCCT), всегда в .assy.json; .04, .08, вал — примитивы; .05–.07 — CP-05; имя изделия в дереве — тег файла (Д-91, CP-76).
- Д-52: имена узлов STEP сборки — только латиница: RING/CAGE/ECC/BODY/BEARING/SHAFT (.<NN><вар>[ код]), ROWk (phi = … deg), BODIES_ROWk (n pcs); ключи --names, --enc удалены (уточняет Д-50, Д-51: --names ru --enc utf8 во FreeCAD даёт неверные имена); кириллица — только в значениях атрибутов CAx-IF, кодом \X2\ по ISO 10303-21; в .assy.json — UTF-8.
- Д-61: комплект чертежей — по спецификации specs/cad_set.yaml (python -m egm.cad --spec): запись items[] — исполнение целиком (id — исполнение или деталь, design — проработка шага 2, assy — сборка одним STEP, фильтры rows/parts); строятся все детали исполнения с генераторами products.yaml → cad; поштучный запуск по ID (python -m egm.cad <ID>…) остаётся низкоуровневым путём.
- Д-62: отчёт построения чертежей reports/cad_report.md (Д-14): весь вывод консоли python -m egm.cad дублируется в отчёт — переписывается каждым запуском, в конце лога печатается, куда сохранён; пути в выводе — от корня репозитория (полный путь избыточен); перед каждой позицией в отчёте легенда: что это за чертёж (SVG — 2D-вид по оси, STEP — 3D-модель, генератор) и что это за деталь (позиция, название, вариант, ряды пакета, проработка шага 2).
- Д-65: чертежи деталей во FreeCAD — TechDraw из 3D-геометрии STEP: виды — проекции формы детали из <ID>.step (метка-алиас, система детали); все размеры на листе и геометрические значения легенды измеряются по 3D (сечение формы, цилиндрические грани, BoundBox) макросом tools/freecad_techdraw.py; из <ID>.assy.json → drawings — только эталоны сверки (из PartModel, Д-32), обозначения и смысл колонок SPEC-10/SPEC-11, неизмеримые величины (u, z…).
- Д-66: лист TechDraw и один макрос FreeCAD: свой шаблон A3 <ID>.A3.svg (рамка ГОСТ 2.301, упрощённая основная надпись ф. 1 ГОСТ 2.104, поля EditableTexts) вместо штатного; зоны листа — виды слева, предупреждения под видами, легенда/примечания/ISO справа над основной надписью (egm/cad/techdraw_sheet.py, без FreeCAD); легенда, примечания, предупреждения — SVG-символы (DrawViewSymbol), Spreadsheet/LegendView и аннотации не создаются.
- Д-70: TechDraw: FreeCAD считает HLR видов в фоновом потоке, recompute() результата не ждёт; макрос ждёт кромки у каждого вида (опрос getEdgeByIndex с прокачкой очереди Qt, предел WAIT_S = 180 с) и только затем добавляет косметические окружности, размеры и PDF; вид без геометрии за предел — повтор с CoarseView; время HLR, грубые виды, виды без геометрии и недобавленная косметика — в заголовке листа в <ID>.techdraw.md.
- Д-71: TechDraw в проходах: 1) замеры по 3D, листы и виды всех деталей без размеров; 2) один recompute — HLR всех видов параллельно, в это время легенды и примечания; 3) общее ожидание (WAIT_S), CoarseView для опоздавших; 4) косметика всех листов, recompute; 5) размеры, PDF; у детали с числом граней > HEAVY_FACES (300) вид по оси строится по слою той же формы STEP z ± 0.5 мм (кромки окон вдоль оси вырождаются, HLR не даёт геометрии), примечание на листе; длина без цельной кромки — DistanceX по крайним вершинам вида сбоку.
- Д-74: SPEC-11 «Конструктив» — четыре таблицы вместо одной строки: «Состав» (конструктив, исполнения .02/.12 с буквой и кратким именем из products.yaml → variants, детали, длина), «Опоры, кольца, крышки, дно», «Соединение .02–.12» (только L2/L3: схема, заготовка, штифты n × Ø × l, напряжения / допускаемые), «Заготовка .02» (строка на марку: выбрана / альтернатива / нет подходящей).
- Д-76: соединение .02–.12 в CAD (CP-63): штифты радиально на z = z_in + L/2, углы — оси окон последнего ряда (cage + j·360/n); дно/пояс по оси max(cup_t, belt), belt = L (collar) или L + cup_t (insert, бурт .12B = cup_t); стенка под гнездом ≥ pin_wall = 1 мм; шов weld — на перемычке ряда 1 (cage₁ + 180/n), мимо штифтов; z-положение штифтов вне окон проверяется по 3D (Д-65); JOIN.weld — марки листа (по умолчанию пусто). Уточнено Д-92 (collar — осевые штифты через бурт; реализация — CP-79).
- Д-91: имя root-ноды STEP сборки — тег имени файла (Д-49, Д-51, Д-73): изделие в дереве = ID + суффикс проработки/конструктива (-K8, -L2), как в имени файла; без проработки/конструктива — ID; реализация — CP-76.

#### Д-90 — ПТК — технология и материалы

Действующий набор принципов (тексты и разбивка членов — в [archive/DECISIONS-2026-10.md](archive/DECISIONS-2026-10.md)):

- Д-45: технологические нюансы — в данных калькулятора, варианты не исчезают молча: коды egm/ptk.py → TECH (Т1–Т4), поля tech, excluded в ptk_configs.json, коды в колонке «Статус» SPEC-10, расшифровка и список исключённых — в конце SPEC-10; шарик на подшипнике — исключён (Т1: жёлоб на покупном кольце не сделать); шарик на эксцентрике — контакт с жёлобом limits.groove_f·D_ш (Т2), венец без жёлоба (Т3, OQ-11); тело на эксцентрике — скольжение (Т4, OQ-10); groove_f в хэш ID не входит.
- Д-67: материалы и заготовки по маркам: справочник specs/materials.yaml (title — графа 3 основной надписи, rho, heat, use); stock.yaml → materials.<марка> — у каждой марки свой набор форм tubes/sheets/bars (старый формат без марок читается как марка None); products.yaml → parts.<NN>.material — допустимые марки по предпочтению; шаг 2 (ptk_layout.blanks) берёт для .02 первую марку с подходящей формой; основная надпись: .02 — марка выбранной заготовки, прочие — первая марка детали (assy.material → drawings[].material); проверка materials_cfg в main.py — все марки есть в справочнике (egm/materials.py).
- Д-68: заготовка .02 по конструктиву: формы FORMS_BY_02 — cup (L1) → пруток, sleeve (L2) → труба/лист; в SPEC-11 — выбранная марка с формами, «альтернатива <марка>: формы», «нет подходящей заготовки» (вместо «также»); марки .02: 38Х2МЮА (пруток, азотирование) — L1; 40Х — труба L2; Сталь 40 / 30ХГСА — лист, маршрут weld, ХТО — QPQ; 60С2А и Сталь 50 не свариваются, поэтому в weld не идут; макросы FreeCAD: проверка __name__ != модуля, окно итога/ошибки, открытие первого листа.

### Архив (поглощённые сводными, исторические)

Поглощённые сводными — состав в кластерах и группах выше; полные тексты и
разбивка — в [archive/DECISIONS-2026-10.md](archive/DECISIONS-2026-10.md). Исторические:

- Д-23: тег rev6 (историческое, состояние CP-19).
- Д-28: папка review_reports (механизм заменён bundle/INS-91).
- Д-50: уточнено Д-52 (имена узлов STEP — только латиница).
- Д-56: переведён на YAML (Д-67, CP-48).

===== END FILE =====

===== FILE: specs/DECISIONS.md (строки 196–197) =====
| OQ-34 | Опорный обод .12A в отверстии бурта/кольца (Д-102 п. 2, редакция 2026-11-07): посадка seat_fit H7/js6 и w кольца .14 = max(t_tech, k_fit·d) — предварительно (прогон 2026-11-07: сборка L4 — 19 деталей, STEP OK, кольцо .14 Ø66.12/Ø60.12×9, .12A обод Ø60.12×9, 10×Ø3, гнездо 5.0; .07B с канавкой 13943; .13 и осевых отверстий нет); проверить смятие кольца под штифтом и сборку «обечайка + кольцо + обод» со сверловкой в сборе (SM-1, ось C); извлечение штифтов — OQ-29; da .09 для 61813+ и граница s_об — OQ-31 | открыт |
| OQ-35 | Где хранить таблицу шпонок keys.table (DIN 6885 / ГОСТ 23360): в specs/ptk_design_input.yaml (как сейчас — одна таблица на входной и выходной вал, CP-90) или перенести в specs/shafts.yaml как «номенклатуру сечения вала»? Влияет на то, чем задаётся паз: конфигурацией вала (шаг 2) или общей таблицей. Решение — Д-109: таблица перенесена в specs/shafts.yaml (паз — свойство сечения вала), вход проработки её не содержит, читает egm/ptk_design.keys_table() | решён (Д-109) |
===== END FILE =====

===== FILE: specs/CODE_PLAN.md (строки 81–81) =====
| CP-91 | Д-107/Д-108: номенклатура входных валов как продукт SH. Этап 1 — egm/shafts.py: чтение specs/shafts.yaml, проверка ID `SH-<d>-<link>` (регулярка, неизвестный ID — ошибка прогона), слияние «переопределение проработки > поле номенклатуры > умолчание кода(DEFAULTS)» в словарь shaft для ptk_design.design(); таблица шпонок keys.table читается оттуда же — Д-109: перенесена из ptk_design_input.yaml, вход проработки ключ keys не принимает; products.yaml → SH + product: SH у .15, configs/application.yaml → products.SH. Этап 2 — ptk_design_input.yaml: designs[].shaft = {id: SH-08-KEY}; полный блок принимается как переходный формат с предупреждением (обратная совместимость). Этап 3 — SPEC-12_SHAFTS.md: egm/shaft_doc.py (наследник doc_yaml.Doc: GLOSSARY/PATTERNS/GENERIC, 100% комментариев) + templates/SPEC-12_SHAFTS.md.tmpl; разделы: таблица шпонок (Д-109), реестр конфигураций, применимость по продуктам и проработкам, проверки (τ, d_req, шпонка σсм, стенки эксцентрика, стенка полого вала), производные для .03/.10; новый ключ input.shaft_id в ptk_designs.yaml + комментарий в design_doc.GLOSSARY. Этап 4 — egm/cad/ptk_shaft.py: генератор .15 по конфигурации (Ø, паз keys.table, шейки .03/.10, длина по пакету), cad: ptk_shaft. Этап 5 — INS-40_SHAFTS.md + ссылки из README §3, INS-10 §2, INS-30 (Д-108). Этап 6 — проработка K20 на PTK-063 (rev13.1) с SH-20-KEY: прогон, проверка стенок эксцентрика и шпонки под Ø20. Критерий приёмки: main.py --publish rc=0; числа K8/K10 в ptk_designs.yaml не изменились, кроме input.shaft_id | specs/shafts.yaml, specs/products.yaml, configs/application.yaml, specs/ptk_design_input.yaml, egm/shafts.py, egm/ptk_design.py, egm/shaft_doc.py, egm/design_doc.py, egm/doc_yaml.py, templates/SPEC-12_SHAFTS.md.tmpl, egm/cad/ptk_shaft.py, instructions/INS-40_SHAFTS.md, instructions/README.md, instructions/INS-10_PTK_CALC.md, instructions/INS-30_CAD.md, main.py | Д-107, Д-108, Д-79, Д-105, Д-106, Д-48, OQ-32, OQ-35 (решён, Д-109) | CP-90 | открыт (этапы 1–2 — код; этап 3 — SPEC-12; этап 4 — CAD .15; этап 5 — инструкции; этап 6 — K20/Ø20) |
===== END FILE =====

===== FILE: instructions/README.md (строки 138–160) =====
## 3. Порядок работы с code-first спецификациями (Д-79)

Code-first спецификация — результат прогона `main.py`, руками она не правится.
Чтобы изменить результат, меняют **входные файлы** и запускают прогон заново.
Инструкция описывает, какие входные файлы есть, что означает каждый параметр
и как читать результат.

| Инструкция | Спецификация / БД | Входные файлы |
|---|---|---|
| [INS-10_PTK_CALC.md](INS-10_PTK_CALC.md) | `specs/SPEC-10_PTK_CALC.md`, `specs/SPEC-11_PTK_DESIGN.md`, `specs/ptk_configs.yaml`, `specs/ptk_designs.json` | `specs/ptk_input.yaml`, `specs/ptk_design_input.yaml`, `specs/vendor_prices.yaml` → `rollers`, `bearings` |
| [INS-20_CATALOG.md](INS-20_CATALOG.md) | `specs/catalog_hiwin_hg.yaml`, `specs/catalog_hiwin_hg_pairs.json`, `reports/catalog_report.md` | `docs/HG-Series-Catalog_opt.md`, `specs/vendor_prices.json` |

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
- `egm/ptk_layout.py` — целиком; в задаче не участвует, но layout читает `d["output"]` и может конфликтовать по ключам `shaft`.
- `specs/ptk_designs.yaml` — текущее опубликованное состояние (эталон чисел для проверки «не сломали»); 89 КБ, выдаётся отдельным файлом.
- `docs/HG-Series-Catalog_opt.md` — каталог (нужен только для `.10`/`.09`).
