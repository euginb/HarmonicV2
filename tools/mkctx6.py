"""Сборка CTX-T для CP-98 + CP-95 (rev14.0).

Правила подачи материала модели (заказчик, 2026-11-16):
- машиночитаемые YAML — без комментариев (они пишутся для людей) и только по нужным позициям;
- SPEC-10 — одиночное исполнение PTK-063-R3X8-22M6P2-BDBB72 (весь файл не нужен).
"""
import io, re, subprocess, yaml
from pathlib import Path

ROOT = Path('/tmp/sync/i7/repo')
OUT = Path('/tmp/sync/i7/CTX-T-CP-98-r140.md')
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
    return '\n'.join([f'===== FILE: {p} (строки {lo}–{hi}) =====', '\n'.join(L[lo - 1:hi]), '===== END FILE ====='])


def whole(p):
    return block(p)


def strip_comments(p):
    """YAML без комментариев; кавычки не трогаем."""
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


def keep_sections(p, names):
    """YAML верхнего уровня: оставить перечисленные разделы (комментарии вырезаны)."""
    L = strip_comments(p)
    out, on = [], False
    for l in L:
        if re.match(r'^[A-Za-zА-Яа-я_][^:\s]*:\s*$', l) or re.match(r'^[A-Za-zА-Яа-я_][^:\s]*:\s*\S', l):
            on = l.split(':')[0] in names
        if on or l.startswith(' '):
            if on:
                out.append(l)
    return '\n'.join(out)


def yaml_block(p, names, note=''):
    txt = keep_sections(p, names)
    STATS.append((p, txt.count('\n') + 1))
    return '\n'.join([f'===== FILE: {p} (разделы {", ".join(names)}; без комментариев) ====='
                      + (f'\n{note}' if note else ''), txt, '===== END FILE ====='])


def table_one(p, needle, title):
    """Документ-таблица: шапка + строка, содержащая needle."""
    L = lines_of(p)
    hit = [i for i, l in enumerate(L) if needle in l and l.startswith('|')]
    if not hit:
        return f'({p}: строка {needle} не найдена)'
    i = hit[0]
    head = []
    k = i - 1
    while k >= 0 and (L[k].startswith('|') or L[k].startswith('|---')):
        head.insert(0, L[k]); k -= 1
    if not any(set(h) <= set('|- :') for h in head):
        head = []
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
    des = yaml.safe_load((ROOT / 'specs/ptk_designs.yaml').read_text(encoding='utf-8'))
    out = ['## Выжимка чисел K20 (сгенерировано)', '',
           '| Поле | Значение |', '|---|---|']
    k = next(r for r in rows if r.get('id') == 'PTK-063-R3X8-22M6P2-BDBB72')
    keys = ('u', 'z', 'R_sum', 'Dgen', 'Drol', 'd_out', 'width', 'M', 'M_by', 'M_H', 'M_B', 'M_sep',
            't_hold', 'safety', 'ok', 'errors')
    for kk in keys:
        out.append(f'| `{kk}` | {k.get(kk)} |')
    c = k.get('sep_chk') or {}
    out += ['| `sep_chk` | ' + ', '.join(f'{a} {b}' for a, b in c.items()) + ' |', '']
    out.append('| Проработка | ok | R_Σ | t сепаратора | web | окна | M | .09 |')
    out.append('|---|---|---|---|---|---|---|---|')
    for d in des:
        lay = d.get('layout') or {}
        s = lay.get('sep') or {}
        out.append(f"| {d.get('name')} | {d.get('ok')} | {s.get('R_sum') or lay.get('R_sum')} | "
                   f"{(s.get('r_out', 0) - s.get('r_in', 0)):.2f} | {s.get('web')} | {s.get('w')}×{s.get('h')} | "
                   f"{lay.get('M')} | {(lay.get('b09') or {}).get('id')} |")
    return '\n'.join(out)


HEAD = f"""# CTX-T — CP-98 (доработка предела сепаратора) и CP-95 (инверсия постановки), rev14.0

База: `{SHA}` (ветка `rev14.0`; содержит CP-94 — предел сепаратора `M_sep`, прогон принят 2026-11-16).
Продукт `euginb/HarmonicV2`, ПТК. Язык ответа — русский; комментарии в коде — русский, с номерами Д-##/CP-##.

## Правила вывода (INS-91B §6)

1. Ответ — два блока: `p.diff` (unified diff от указанной базы, корректные счётчики `@@`) и `upd.md`.
2. Маркеры `===== FILE: … =====` — только в этом CTX.
3. Правки минимальные; стиль — как в приложенных файлах. Числа, полученные вручную, помечать как оценку.

## Состав контекста (по просьбе заказчика)

Машиночитаемые YAML поданы **без комментариев** (они пишутся для людей) и только по нужным разделам;
SPEC-10 ограничен одним исполнением `PTK-063-R3X8-22M6P2-BDBB72`. Полные файлы есть в репозитории.

## Задача 1 — CP-98 (Д-118): доработка M_sep. Приоритет — первая

Прогон CP-94 принят, но результат показал перекос: у K20 `M_sep` 188.1 Н·м, `M_H` 4124.9 Н·м —
сепаратор ограничивает в 22 раза раньше контакта тел. Значит поднимать надо несущую способность
сепаратора, а не перебирать тела. Требуется:

1. **Момент по одному ряду как референс.** Кроме `M_sep` для пакета (`M_pack`) выводить `M_row` —
   предел по одному ряду окон без переноса момента через дальние ряды (только изгиб своим рядом).
   В `sep_chk` — `M_row`, `M_pack`, `n_row_lim` (какой ряд первым достигает `[σ]`). Смысл: разница
   `M_pack`/`M_row` показывает, сколько «съедает» перенос через ряд, то есть и потенциал межрядного усиления.
2. **Межрядное усиление.** Кольца-пояса между рядами сейчас — жёсткая заделка. Рассмотреть усиление
   межрядных зон (буртики/утолщения между рядами окон, бандаж, накатка): тогда момент идёт не изгибом
   перемычки, а срезом пояса. Стенку ряда `t = 2.2·a_ω` поднимать нельзя (кинематика, запас 0.06 мм), а
   межрядные зоны в кинематике не участвуют. Нужны проверки: жёсткость пояса `EI`, `σ_см`/`τ` в поясе,
   влияние на массу и балансировку. Критерий — рост `M_sep` при сохранении габарита.
3. **Ограничения по моменту для тел качения.** Отдельный выход `M_body_*` для трёх контактов тела:
   с генератором, с венцом, со стороной окна сепаратора; плюс `M_by_body` — какой контакт первый.
   Сейчас `M_H` — общий минимум (генератор+венец), а окно видно только как `sep_chk.sig_H`.
4. Приёмка: `self_test` фиксирует `M_row < M_sep`, рост `M_sep` при усилении пояса, три `M_body_*` > 0
   и `M = min(...)`; пересчёт SPEC-10/11; K10 (Ø10) должен снова стать осмысленным (после роста `M_sep`).

## Задача 2 — CP-95 (Д-116 п. 2): инверсия постановки. После CP-98

Сейчас: задаётся `u`, перебираются тела и крепления, минимизируется габарит `D`, а `M` получается
следствием. Нужно: на входе требуемый `M_req`, на выходе — `Dш`, `R_Σ` (через обод), тип генератора и
крепление при минимальном `D`, с отбором по **всем** пределам (`M_H`, `M_B`, `M_крепл`, `M_sep`,
`M_body_*`). Крепление подбирается по моменту, а не «первое наименьшее» (сейчас у K20 `М` диктовало
наименьшее крепление). Таблица SPEC-10 получает колонку `M_req`; ID исполнений меняются (Д-80).
`gen_type: rim` и каталог тел 4–6 мм (CP-96, CP-97) — отдельные пункты, здесь только постановка.

## Формулы, действующие сейчас (CP-94, Д-116)

`V = M(rows−½)/(rows·n·R_Σ)`, `M_изг = V·L/2`; `F = k_sep·M/rows`, `F·L/12`; `σ = (V·L/2 + F·L/12)/W`,
`W = t·b²/6`; `[σ] = σ₋₁/(K·S)`; контакт — Герц тело/плоскость на `min(l, L)`, `× sep_k_edge`.

"""

BODY = [HEAD, '---\n\n# Исходники\n', '## Расчётное ядро\n',
        whole('egm/ptk_force.py'), whole('egm/ptk.py'), whole('egm/ptk_parts.py'),
        pick('egm/ptk_doc.py', [r'GLOSSARY = \{', r'"M_sep"', r'"sep_chk"', r'"sep_chk\.by"'], before=0, after=0),
        '\n## Вход и каталоги (без комментариев)\n',
        yaml_block('specs/ptk_input.yaml', ['limits'], 'limits — все пределы шага 1, включая sep_*.'),
        yaml_block('specs/vendor_prices.yaml', ['rollers', 'bearings', 'screws'],
                   'rollers — тела качения (8 позиций: 3/5/6/7/8 мм), bearings — 61800…, screws — M3…M12.'),
        '\n## Публикуемые результаты\n',
        table_one('specs/SPEC-10_PTK_CALC.md', 'PTK-063-R3X8-22M6P2-BDBB72', 'PTK-063-R3X8-22M6P2-BDBB72'),
        '\n## Регистры\n',
        pick('specs/DECISIONS.md', [r'^- Д-41:', r'^- Д-116:', r'^- Д-118:', r'^\| OQ-44 ', r'^\| OQ-45 ',
                                    r'^\| OQ-46 '], before=0, after=0),
        pick('specs/CODE_PLAN.md', [r'^\| CP-94 ', r'^\| CP-95 ', r'^\| CP-96 ', r'^\| CP-97 ', r'^\| CP-98 '],
             before=0, after=0),
        '\n## Силовой расчёт: сепаратор\n',
        window('docs/Силовой расчет ПТК/Силовой расчет ПТК.md', r'перемычк', before=8, after=30),
        '\n## Точка регистрации self_test\n',
        window('main.py', r'\("tech_proc"', before=3, after=5)]

txt = '\n'.join(BODY) + '\n\n' + numbers() + '\n'
OUT.write_text(txt, encoding='utf-8')
print('файл:', OUT.name, '|', len(txt.encode('utf-8')), 'Б |', txt.count(chr(10)), 'строк |', txt.count('===== FILE:'), 'блоков')
print('крупнейшие:', sorted(STATS, key=lambda x: -x[1])[:6])
