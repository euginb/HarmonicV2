"""Сборка CTX-T для CP-97 → CP-96 → CP-95 (rev14.1, Д-116).

Правила подачи (заказчик, 2026-11-16): машиночитаемые YAML — без комментариев и только нужными
разделами; таблицы SPEC — только по нужным исполнениям (PTK-063-R3X8-22M6P2-BDBB72).
"""
import re
import subprocess
import yaml
from pathlib import Path

ROOT = Path('/tmp/sync/i7/repo')
OUT = Path('/tmp/sync/i7/CTX-T-CP-97-96-95-r141.md')
SHA = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
STATS = []


def lines_of(p):
    L = (ROOT / p).read_text(encoding='utf-8').split('\n')
    return L[:-1] if L and L[-1] == '' else L


def block(p, a=None, b=None):
    L = lines_of(p)
    lo = 1 if a is None else max(1, a)
    hi = len(L) if b is None else min(len(L), b)
    STATS.append((p, hi - lo + 1))
    return '\n'.join([f'===== FILE: {p} (строки {lo}–{hi}) =====', '\n'.join(L[lo - 1:hi]),
                      '===== END FILE ====='])


def whole(p):
    return block(p)


def strip_comments(p):
    out = []
    for l in lines_of(p):
        if l.lstrip().startswith('#'):
            continue
        q, cut = None, None
        for i, ch in enumerate(l):
            if q:
                if ch == q:
                    q = None
            elif ch in '"\'':
                q = ch
            elif ch == '#' and i and l[i - 1] in ' \t':
                cut = i
                break
        out.append((l[:cut] if cut is not None else l).rstrip())
    return out


def yaml_block(p, names, note=''):
    L = strip_comments(p)
    out, on = [], False
    for l in L:
        if re.match(r'^[^\s:#][^:]*:', l):
            on = l.split(':')[0].strip() in names
        if on:
            out.append(l)
    txt = '\n'.join(out)
    STATS.append((p, txt.count('\n') + 1))
    return '\n'.join([f'===== FILE: {p} (разделы {", ".join(names)}; без комментариев) ====='
                      + (f'\n{note}' if note else ''), txt, '===== END FILE ====='])


def table_one(p, needle, title):
    L = lines_of(p)
    hit = [i for i, l in enumerate(L) if needle in l and l.startswith('|')]
    if not hit:
        return f'({p}: строка {needle} не найдена)'
    i = hit[0]
    head, k = [], i - 1
    while k >= 0 and L[k].startswith('|'):
        head.insert(0, L[k]); k -= 1
    head = [l for l in head if set(l) <= set('|- :')][:1] + [l for l in head if set(l) > set('|- :')]
    out = head + [L[i]]
    STATS.append((p, len(out)))
    return '\n'.join([f'===== FILE: {p} (шапка + строка {title}) =====', '\n'.join(out), '===== END FILE ====='])


def pick(p, pats, before=0, after=0):
    L = lines_of(p)
    idx = set()
    for pat in pats:
        for i, l in enumerate(L):
            if re.search(pat, l):
                idx.update(range(max(0, i - before), min(len(L), i + after + 1)))
    if not idx:
        return f'({p}: по шаблонам ничего не найдено)'
    idx = sorted(idx)
    parts, run = [], [idx[0]]
    for i in idx[1:]:
        if i == run[-1] + 1:
            run.append(i)
        else:
            parts.append((run[0], run[-1])); run = [i]
    parts.append((run[0], run[-1]))
    return '\n\n'.join(block(p, a + 1, b + 1) for a, b in parts)


def window(p, pat, before=6, after=40, nth=0):
    L = lines_of(p)
    hits = [i for i, l in enumerate(L) if re.search(pat, l)]
    if not hits:
        return f'({p}: /{pat}/ не найден)'
    i = hits[min(nth, len(hits) - 1)]
    return block(p, max(1, i + 1 - before), min(len(L), i + 1 + after))


def numbers():
    cfg = yaml.safe_load((ROOT / 'specs/ptk_configs.yaml').read_text(encoding='utf-8'))
    rows = cfg if isinstance(cfg, list) else cfg.get('rows') or cfg.get('configs') or []
    vp = yaml.safe_load((ROOT / 'specs/vendor_prices.yaml').read_text(encoding='utf-8'))
    out = ['## Текущее состояние: каталог тел и K20 (сгенерировано)', '',
           '| Тело | type | d | l |', '|---|---|---|---|']
    for k, v in (vp.get('rollers') or {}).items():
        out.append(f"| `{k}` | {v.get('type')} | {v.get('d')} | {v.get('l')} |")
    out += ['', '| Поле K20 | Значение |', '|---|---|']
    k = next(r for r in rows if r.get('id') == 'PTK-063-R3X8-22M6P2-BDBB72')
    for kk in ('u', 'z', 'R_sum', 'Dgen', 'Drol', 'd_out', 'width', 'M', 'M_by', 'M_H', 'M_B',
               'M_sep', 'M_body_g', 'M_body_v', 'M_body_win', 't_hold', 'ok'):
        if kk in k:
            out.append(f'| `{kk}` | {k.get(kk)} |')
    c = k.get('sep_chk') or {}
    out += ['| `sep_chk` | ' + ', '.join(f'{a} {b}' for a, b in c.items()) + ' |', '',
            'Замечание: тела D5…D8 сейчас не проходят по габариту при u 50/63 (`d_out_max` 200),',
            'поэтому в step 1 они дают M 0.0 — это и есть предмет CP-97: каталог без тел, которые',
            'проходят, и потолок `Drol_max` ≈ 4.02 мм при u 63.']
    return '\n'.join(out)


HEAD = f"""# CTX-T — CP-97 → CP-96 → CP-95, rev14.1 (Д-116)

База: `{SHA}` (ветка `rev14.1`, содержит rev14.0: CP-98 — `M_row`, пояса сепаратора, пределы по телам).
Продукт `euginb/HarmonicV2`, ПТК. Язык ответа — русский; комментарии в коде — русский, с Д-##/CP-##.

## Правила вывода (INS-91B §6)

1. Ответ — два блока: `p.diff` (unified diff от указанной базы, **корректные счётчики `@@`**) и `upd.md`.
   В прошлый раз `git apply` отверг дифф на «patch fragment without header» — считать `@@` обязательно.
2. Маркеры `===== FILE: … =====` — только в этом CTX.
3. Правки минимальные; числа, посчитанные вручную, помечать как оценку.
4. Три задачи делать **в указанном порядке**, каждую отдельным законченным изменением, чтобы её можно
   было принять независимо: CP-97 → CP-96 → CP-95.

## Состав контекста

Машиночитаемые YAML поданы без комментариев и только нужными разделами; SPEC-10 — шапка и одна строка
`PTK-063-R3X8-22M6P2-BDBB72`. Полные файлы — в репозитории.

## Порядок и содержание работ

### CP-97 — каталог тел качения (первый, без него остальное бессмысленно)

Сейчас в `vendor_prices.yaml → rollers` восемь тел: 3, 5, 6, 7, 8 мм. Но при `u` 50/63 по габариту
(`d_out_max` 200) проходят только 3 мм: `Drol_max` ≈ 4.02 мм при u 63, тела 5…8 мм дают `D` 198…364 мм
и `M = 0`. То есть выбор тела фактически один, и «увеличить Dш под момент» калькулятор не может.
Требуется:

1. Добавить/выправить тела в диапазоне **4…6 мм** так, чтобы шаг по диаметру был непрерывным
   (4; 4.5; 5; 6 и т. п.), с длинами `l`, дающими выбор по ширине окна; формат записи — как у
   существующих (`type`, `d`, `l`), цены — если есть, в том же виде, что у штифтов/винтов.
2. Пометить, какие позиции **подтверждены поставщиком**, а какие — кандидаты (как OQ-26 для штифтов):
   поле или комментарий в YAML — на ваше усмотрение, но так, чтобы `calc` это не сломал.
3. Проверить, что рост каталога не ломает `Drol_max`/`Dgen` и что перебор в `sweep()` действительно
   начинает пробовать новые тела (сейчас `rid.startswith("_")` — единственный фильтр).
4. Учесть ловушку: длинный ролик поднимает контактную способность, но удлиняет окно, а изгиб перемычки
   растёт ∝ l² (см. `_sep`). Для сепаратора лучше несколько коротких рядов, чем один длинный ролик.

### CP-96 — `gen_type: rim` (подшипник + обод), второй

Сейчас `GEN_TYPES = ("bearing", "eccentric")`: у `bearing` `D_г` жёстко равен `D` подшипника и контакт идёт
по `min(l, B)`, у `eccentric` геометрия свободна, но есть скольжение (OQ-10). Нужен третий тип:
**свободная геометрия как у `eccentric`, качение как у `bearing`**.

1. Обод: расчётный `D_г` с округлением `dgen_step`; подшипник садится на **минимальный** радиус
   эксцентрика (`need_d = shaft_d_min + 2(a + ecc_wall_min)` — как у `eccentric`); дорожка обода имеет
   длину ровно `l` (не `min(l, B)`); обод закаливается как дорожка под ролик.
2. Выбор подшипника — по `C0` (малый подшипник под ободом, `M_B` может стать главным ограничением;
   вариант — шире или игольчатый).
3. Проверки: жёсткость обода на изгиб (тела нагружают половину окружности — тонкий обод сплющивается
   в овал, распределение нагрузки по телам плывёт), посадка обода на наружное кольцо с натягом,
   масса и инерция входа, `pitch = max(l, B)` для ширины пакета.
4. Затрагивает: `GEN_TYPES`, `geom_params`/`config_id` (тип входит в геометрию и в ID), `calc`,
   `ptk_input.yaml → gen_types`, `ptk_doc` (глоссарий), шаблон SPEC-10, `ptk_profile` (если профиль
   контакта для обода отличается).

### CP-95 — инверсия постановки, третий

Сейчас: задаётся `u`, перебираются тела и крепления, минимизируется габарит, а `M` — следствие
(у K20 момент диктовало наименьшее крепление: 1740.7/1.5). Нужно наоборот.

1. Вход — требуемый момент `M_req` (в `ptk_input.yaml`, с глоссарием).
2. Перебор по (Dш, `R_Σ` через обод, `gen_type`, крепление) с отбором по **всем** пределам:
   `M_H` (уже разделён на `M_g`/`M_v`), `M_B`, `M_крепл = t_hold/safety`, `M_sep`, `M_body_*`.
3. Крепление подбирается по моменту, а не «первое наименьшее».
4. Выход — минимальный `D` при выполненном `M ≥ M_req`; таблица SPEC-10 получает колонку `M_req`;
   ID исполнений меняются (Д-80), старые ID не сохраняются.

## Что уже сделано в rev14.0 (не переделывать)

`M_sep` считается как `min` из пакета и ряда (`M_row` — референс), добавлены межрядные пояса
(`sep_band_t`, `sep_band_gap`), пределы по телам разделены: `M_g` (тело/генератор), `M_v` (тело/венец),
`M_body_win` (тело/окно), `M_by_body`. В `sep_chk` — `eta_pack`. Это опора для CP-95, менять не нужно.

## Действующие формулы

`V = M(rows−½)/(rows·n·R_Σ)`, `M_изг = V·L/2`; `F = k_sep·M/rows`, `F·L/12`;
`σ = (V·L/2 + F·L/12)/W`, `W = t·b²/6`; `[σ] = σ₋₁/(K·S)`; контакт — Герц тело/плоскость на `min(l, L)`, `× sep_k_edge`.
Момент по контакту тел почти не зависит от `R_Σ`: `M ≈ R_max·u·a_ω·Σsin²φ` — но окружная сила на
сепаратор `F_t = M/R_Σ` падает с ростом `R_Σ`, поэтому обод (CP-96) и есть способ разгрузить сепаратор.

"""

BODY = [HEAD, '---\n\n# Исходники\n', '## Расчётное ядро\n',
        whole('egm/ptk.py'), whole('egm/ptk_force.py'), whole('egm/ptk_profile.py'),
        whole('egm/ptk_parts.py'),
        pick('egm/ptk_doc.py', [r'^GLOSSARY = \{', r'"M_sep"', r'"M_row"', r'"M_body', r'"sep_chk"',
                                r'"sep_band', r'"gen"'], before=0, after=0),
        '\n## Вход и каталоги (без комментариев)\n',
        yaml_block('specs/ptk_input.yaml', ['limits'],
                   'limits — все пределы шага 1: u_list, gen_types, dgen_step, d_out_max, sep_*, wall_min, a_k.'),
        yaml_block('specs/vendor_prices.yaml', ['rollers', 'bearings', 'screws'],
                   'rollers — тела качения; bearings — 61800…, screws — M3…M12 (F_M).'),
        '\n## Публикуемый результат\n',
        table_one('specs/SPEC-10_PTK_CALC.md', 'PTK-063-R3X8-22M6P2-BDBB72', 'PTK-063-R3X8-22M6P2-BDBB72'),
        '\n## Регистры\n',
        pick('specs/DECISIONS.md', [r'^- Д-40:', r'^- Д-41:', r'^- Д-42:', r'^- Д-116:', r'^- Д-118:',
                                    r'^\| OQ-05 ', r'^\| OQ-10 ', r'^\| OQ-44 ', r'^\| OQ-46 '], before=0, after=0),
        pick('specs/CODE_PLAN.md', [r'^\| CP-95 ', r'^\| CP-96 ', r'^\| CP-97 ', r'^\| CP-98 '],
             before=0, after=0),
        '\n## Расчётная записка: геометрия и генератор\n',
        window('docs/Силовой расчет ПТК/Силовой расчет ПТК.md', r'R_?Σ|R_sum|подрез', before=6, after=26),
        '\n## Точка регистрации self_test\n',
        window('main.py', r'\("tech_proc"', before=3, after=5)]

txt = '\n'.join(BODY) + '\n\n' + numbers() + '\n'
OUT.write_text(txt, encoding='utf-8')
print('файл:', OUT.name, '|', len(txt.encode('utf-8')), 'Б |', txt.count('\n'), 'строк |',
      txt.count('===== FILE:'), 'блоков')
print('крупнейшие:', sorted(STATS, key=lambda x: -x[1])[:8])
