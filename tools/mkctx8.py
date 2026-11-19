"""Сборка CTX-T для CP-96 (gen_type: rim) — Д-116, ветка rev14.2.

Правила подачи (заказчик): машиночитаемые YAML — без комментариев и только нужными разделами;
SPEC-10 — шапка и строка исполнения K20.
"""
import re
import subprocess
import yaml
from pathlib import Path

ROOT = Path('/tmp/sync/i7/repo')
OUT = Path('/tmp/sync/i7/CTX-T-CP-96-r142.md')
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


def block_of(p, L):
    STATS.append((p, len(L)))
    return '\n'.join([f'===== FILE: {p} =====', '\n'.join(L), '===== END FILE ====='])


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
    STATS.append((p, len(out)))
    return '\n'.join([f'===== FILE: {p} (разделы {", ".join(names)}; без комментариев) ====='
                      + (f'\n{note}' if note else ''), '\n'.join(out), '===== END FILE ====='])


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


def func(p, name):
    """Тело функции верхнего уровня по её def."""
    L = lines_of(p)
    i = next((k for k, l in enumerate(L) if l.startswith(f'def {name}(')), None)
    if i is None:
        return f'({p}: def {name} не найдена)'
    j = next((k for k in range(i + 1, len(L)) if L[k] and not L[k][0].isspace()
              and not L[k].startswith(')')), len(L))
    return block(p, i + 1, j)


def numbers():
    vp = yaml.safe_load((ROOT / 'specs/vendor_prices.yaml').read_text(encoding='utf-8'))
    rows = yaml.safe_load((ROOT / 'specs/ptk_configs.yaml').read_text(encoding='utf-8'))
    rows = rows if isinstance(rows, list) else rows.get('rows') or rows.get('configs') or []
    out = ['## Каталог подшипников генератора (сгенерировано из vendor_prices.yaml)', '',
           '| Ключ | d | D | B | C | C0 | supplier |', '|---|---|---|---|---|---|---|']
    for k, v in (vp.get('bearings') or {}).items():
        out.append(f"| `{k}` | {v.get('d')} | {v.get('D')} | {v.get('B')} | {v.get('C')} | "
                   f"{v.get('C0')} | {v.get('supplier') or '—'} |")
    ids = {r['id']: r for r in rows}
    cand = [i for i in ids if i.startswith('PTK-063-R3X8')]
    out += ['', '### Исполнения K20 (u = 63, R_D3x8)', '',
            '| ID | Генератор | D_г | D | B | M | Ограничение |', '|---|---|---|---|---|---|---|']
    for i in cand:
        r = ids[i]
        out.append(f"| `{i}` | {r.get('bearing') or 'эксцентрик'} | {r.get('Dgen')} | {r.get('d_out')} | "
                   f"{r.get('width')} | {r.get('M')} | {r.get('M_by')} |")
    out += ['', 'Замечание: в spec-таблице нет ни одного исполнения с ободом — `gen_type: rim` пока не',
            'существует, и все строки K20 опираются на каталог подшипников (D_г = D подшипника) либо',
            'на эксцентрик (скольжение, Д-42/Т4).']
    return '\n'.join(out)


HEAD = f"""# CTX-T — CP-96: `gen_type: rim` (подшипник + обод), rev14.2 (Д-116)

База: `{SHA}` (ветка `rev14.2`, от `main` = merge PR #35; включает CP-99 — диапазон `u` из `u_list`).
Продукт `euginb/HarmonicV2`, ПТК. Язык ответа — русский; комментарии в коде — русский, с Д-##/CP-##.

## Правила вывода (INS-91B §6)

1. Ответ — `p.diff` + `upd.md`. Счётчики `@@` считать обязательно: два предыдущих диффа не применились
   («patch fragment without header», неверные длины ханков). При сомнении — меньше контекста, но верные числа.
2. Маркеры `===== FILE: … =====` — только в этом CTX.
3. Одна задача — CP-96. CP-95 (инверсия постановки) следующим шагом, его не делать.
4. Правки минимальные; числа, посчитанные вручную, помечать как оценку.

## Задача CP-96

Сейчас два типа генератора (`GEN_TYPES = ("bearing", "eccentric")`):

- `bearing` — тела катаются по наружному кольцу покупного подшипника: `D_г` жёстко равен `D`
  подшипника (`R = (brg["D"] + D)/2`), контактная длина `min(l, B)`, `M_B` по `C0` этого подшипника,
  скольжения нет. Цена — `R_Σ` привязан к каталогу: нужен подшипник с `D ≥ 2R_Σ − D_ш`, а с ростом `u`
  `R_Σ` растёт, и подшипник становится главным ограничителем габарита.
- `eccentric` — геометрия свободна (`D_г` = расчётный с шагом `dgen_step`), но тела катаются по
  эксцентрику без подшипника: скольжение ≈ ω·D_г/2, `M_B` нет, технологическое ограничение Т4.

Нужен третий тип **`rim`** — свободная геометрия как у `eccentric`, качение как у `bearing`:
на эксцентрик садится малый подшипник, на нём — закалённый обод, по ободу катаются тела.

Почему это важно (Д-116 п. 3): момент по контакту тел почти не зависит от `R_Σ`
(`M ≈ R_max·u·a_ω·Σsin²φ`), но окружная сила на сепаратор `F_t = M/R_Σ` падает с ростом `R_Σ`.
Значит увеличивать `R_Σ` выгодно (разгружается сепаратор — сейчас он ограничивает в 22 раза раньше
контакта), но у `bearing` для этого нужен подшипник всё большего `D`. Обод отвязывает `R_Σ` от каталога:
подшипник остаётся малым (по `need_d` от вала), а `D_г` задаётся ободом.

### Что должно получиться

1. `GEN_TYPES = ("bearing", "eccentric", "rim")`; тип входит в хэш геометрии и в ID (Д-80), поэтому
   `GEOM_REV` → 7 и все ID меняются — это ожидаемо, так и указать в `upd.md`.
2. В `calc()` ветка `rim`:
   - `R_Σ` считается как у `eccentric`: `R = (ceil(max(2R−D, need_d), dgen_step) + D)/2`, где
     `need_d = shaft_d_min + 2(a + ecc_wall_min)` — подшипник садится на **минимальный** радиус
     эксцентрика, а не на расчётный;
   - подшипник подбирается по `need_d` (и по `C0`, если вариантов несколько) — новый помощник или
     параметр `bearing()`; `D` подшипника на `R_Σ` **не влияет** (в отличие от `bearing`);
   - контактная длина дорожки обода — ровно `l` (не `min(l, B)`); `pitch` пакета — `max(l, B)`;
   - `M_B` — по `C0` малого подшипника, как у `bearing`;
   - обод — деталь: наружный Ø `D_г`, внутренний Ø по посадке на подшипник (натяг), ширина `≥ l`,
     закалка как дорожки под ролик (твёрдость/материал — как у тел, ШХ15 или закалка ТВЧ).
3. Проверки, которых сейчас нет:
   - **жёсткость обода на изгиб.** Тела нагружают половину окружности; тонкий обод сплющивается в овал,
     нагрузка по телам перераспределяется (расчётный `M_H` перестаёт быть достижимым). Оценка прогиба
     кольца под радиальной нагрузкой на диаметре — момент инерции сечения `b·t³/12`, `t` — радиальная
     толщина обода; предел по деформации задать в `ptk_input.yaml` (например, доля от `a_ω` или
     допускаемый прогиб в мм) с ключом в `GLOSSARY`;
   - **овализация** как отдельный отказ, а не молчаливое снижение `M_H`: если прогиб больше допуска —
     строка в SPEC-10 с причиной, как сейчас делают `errors`/`M_by`;
   - посадка обода на наружное кольцо подшипника с натягом (проверить, что стенка обода это позволяет);
   - масса и инерция обода входят в момент инерции входа (шаг 1 их использует для разгона?);
   - `C0` малого подшипника может стать первым ограничением — это допустимо и должно быть видно в `M_by`.
4. Затрагивает: `GEN_TYPES`, `calc`, `geom_params`/`config_id` (тип в хэше), `ptk_input.yaml → gen_types`
   и новые ключи обода, `ptk_force.torque` (передать `B` обода вместо `B` подшипника для `min(l,·)`),
   `ptk_parts.eccentric` (посадка обода, деталь в спецификации), `ptk_doc.GLOSSARY` (каждый новый ключ
   машинного YAML обязан быть в глоссарии), шаблон SPEC-10 (если появляется столбец обода).

## Действующие ограничения проекта

- `specs/*.yaml` руками не править после публикации (Д-79): `ptk_configs.yaml` и `SPEC-10` пишет машина.
- После правок YAML — `yaml.safe_load`, затем `python main.py --self-test`; публикация — `calc --publish`.
- Без новых зависимостей; комментарии с номерами Д-##/CP-##.
- `M = min(M_H, M_B, t_hold/safety, M_sep)` (Д-116 п. 1), `M_sep` — пакет и ряд (CP-98), не переделывать.
- `u_min`/`u_max` — свойства от `u_list` (Д-119), отдельных ключей в YAML нет.

"""

BODY = [HEAD, '---\n\n# Исходники\n', '## Ядро расчёта (целиком)\n',
        whole('egm/ptk.py'),
        '\n## Силовой расчёт\n', whole('egm/ptk_force.py'),
        '\n## Детали: сепаратор, эксцентрик, шайбы\n', whole('egm/ptk_parts.py'),
        '\n## Профиль\n', whole('egm/ptk_profile.py'),
        '\n## Глоссарий (только релевантные ключи)\n',
        pick('egm/ptk_doc.py', [r'^GLOSSARY = \{', r'"gen"', r'"Dgen"', r'"M_B"', r'"bearing"',
                                r'"roller"', r'"dgen_step"', r'"s0_brg"', r'"sep_chk"'], before=0, after=0),
        '\n## Вход и каталог (без комментариев)\n',
        yaml_block('specs/ptk_input.yaml', ['limits'],
                   'limits — gen_types, dgen_step, s0_brg, shaft_d_min, ecc_wall_min, u_list, sep_*.'),
        yaml_block('specs/vendor_prices.yaml', ['bearings', 'rollers'],
                   'bearings — каталог генератора (поле supplier с прогона 2026-11-19); rollers — тела.'),
        '\n## Публикуемый результат\n',
        table_one('specs/SPEC-10_PTK_CALC.md', 'PTK-063-R3X8-22M6P2', 'K20'),
        '\n## Регистры\n',
        pick('specs/DECISIONS.md', [r'^- Д-40:', r'^- Д-42:', r'^- Д-45:', r'^- Д-48:', r'^- Д-80:',
                                    r'^- Д-116:', r'^- Д-118:', r'^\| OQ-10 ', r'^\| OQ-44 '],
             before=0, after=0),
        pick('specs/CODE_PLAN.md', [r'^\| CP-96 ', r'^\| CP-95 ', r'^\| CP-98 '], before=0, after=0),
        '\n## Записка: генератор и геометрия\n',
        pick('docs/Силовой расчет ПТК/Силовой расчет ПТК.md',
             [r'R_?Σ|R_sum', r'подшипник', r'эксцентрик'], before=4, after=16)]

txt = '\n'.join(BODY) + '\n\n' + numbers() + '\n'
OUT.write_text(txt, encoding='utf-8')
print('файл:', OUT.name, '|', len(txt.encode('utf-8')), 'Б |', txt.count('\n'), 'строк |',
      txt.count('===== FILE:'), 'блоков')
print('крупнейшие:', sorted(STATS, key=lambda x: -x[1])[:6])
