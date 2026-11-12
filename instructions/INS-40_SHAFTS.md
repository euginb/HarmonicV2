# INS-40 — номенклатура входных валов (продукт SH)

Спецификация: `specs/SPEC-12_SHAFTS.md` (code-first, Д-79). Решения: Д-107…Д-110, OQ-36.
Связь: [README §3](README.md), [INS-10 §2](INS-10_PTK_CALC.md), [INS-30 §9](INS-30_CAD.md).

## 1. Что это

Входной вал .15 задаётся не в проработке, а в номенклатуре `specs/shafts.yaml` — одна
запись на типоразмер и тип соединения, ID `SH-<d>-<link>` (например `SH-10-KEY`).
Проработка ссылается на неё: `designs[].shaft = {id: SH-10-KEY}`.

## 2. Как добавить конфигурацию

1. В `specs/shafts.yaml → shafts` добавить запись: `name`, `d`, `bore`, `link`,
   `applies_to`, `note`. ID должен совпадать с `d` и `link`; полый вал — суффикс `-B<bore>`.
2. Сослаться из проработки: `shaft: {id: SH-20-KEY}` или списком `[SH-10-KEY, SH-20-KEY]`.
3. `python main.py design --publish`, проверить `out/reports/checks.md`.

## 3. Параметры

Поля записи — в комментариях `specs/shafts.yaml` (первоисточник). Допуски не вводятся:
[τ] = min(τ₋₁/(K_τ·S), 0.58·σт/S_т), [σсм] = min(σт вала, .03, шпонки)/S_см. Свойства
марок — `specs/materials.yaml` (sigma_v, sigma_t, sigma_m1, state, d_range), коэффициенты —
`DEFAULTS` в `egm/shafts.py`. Ручной допуск — только переопределением в проработке
(`{id: …, tau_allow: 25.0}`) с обоснованием в `note`; в SPEC-12 критерий «переопределение».

## 4. Подбор материала .15

Марки — `specs/products.yaml → PTK.parts.15.material` по порядку. Марка отклоняется, если её
нет в справочнике, нет σв/σт, нет прутка Ø ≥ d + 2·припуск в `specs/stock.yaml` или пруток вне
d_range, либо не проходят τ/σсм. Берётся первая проходящая; отказы — SPEC-12 §5.

## 5. Как читать SPEC-12

§1 шпонки (Д-109); §2 реестр; §3 применимость; §4 проверки — τ/[τ] с критерием
(усталость/статика) и маркой, d_req, σсм с лимитирующей деталью, стенки .03, bore_max;
§5 материал, заготовка, отказы, умолчания; §6 производные для .03/.10; §7 машинный вид;
§8 расчёт допусков ([τ] с критерием, [σсм] с лимитирующей деталью, коэффициенты DEFAULTS).

## 6. CAD

Генератор .15 — `egm/cad/ptk_shaft.py` (CP-91 этап 4): хвостовик Ø min(d, d.10) с пазом
keys.table, шейки .10 в .07A и в ступице, тело Ø d под .03 с пазом по пакету. Длина — по
пакету и конструктиву (поле length номенклатуры не читается); константы — DEFAULTS
(tail_l, key_run, slot_over — сверить). CAD не строится, если ID не разрешён или марка .15
не подобрана; отказ τ/σсм вал не останавливает (статус — в SPEC-11/SPEC-12). Деталь —
`<ID>.15-<проработка>`, слой `15_SHAFT`; без проработки — предварительный цилиндр шага 1.
Регистрация генератора — [INS-30 §9](INS-30_CAD.md).

Journal 'specs/CODE_PLAN.md': Входные валы — продукт SH
| CP-91 | Д-107/Д-108/Д-109/Д-110: номенклатура входных валов как продукт SH. Этапы 1–3, 5 — патч rev13.3: egm/shafts.py (ID, resolve, DEFAULTS, подбор марки .15, допуски из материала, bore_max), egm/shaft_doc.py + templates/SPEC-12_SHAFTS.md.tmpl, ptk_design (shaft_id, список ID, поля shaft.*), materials.py props, materials.yaml σв/σт 40Х и 45 (предв., OQ-36), shafts.yaml без переходных полей, вход по ID, INS-40 + ссылки README §3/INS-10 §2/INS-30 §9. Этап 4 — CAD .15; этап 6 — K20/Ø20. Приёмка: (а) с переопределениями tau_allow 25 / sigma_crush 100 числа K8/K10 прежние; (б) штатно — изменения объяснены в SPEC-12, K8/K10 «нет» | egm/shafts.py, egm/shaft_doc.py, templates/SPEC-12_SHAFTS.md.tmpl, egm/ptk_design.py, egm/design_doc.py, egm/materials.py, main.py, specs/shafts.yaml, specs/ptk_design_input.yaml, specs/materials.yaml, instructions/INS-40_SHAFTS.md, instructions/README.md, instructions/INS-10_PTK_CALC.md, instructions/INS-30_CAD.md | Д-107, Д-108, Д-109, Д-110, OQ-36 | CP-90 | этапы 1–3, 5 — ждут прогона; этап 4, 6 — открыты |
