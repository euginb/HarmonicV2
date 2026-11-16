"""Сборка CTX-T (CP-94, rev13.9). Машиночитаемые YAML для модели режутся: без комментариев и по нужным позициям —
комментарии в specs/*.yaml пишутся для людей (`strip_yaml`), а модель фокусируется на нескольких позициях (`only_rows`)."""
import re, subprocess
from pathlib import Path

ROOT = Path('/tmp/sync/i7/repo')
OUT = Path('/tmp/sync/i7/CTX-T-CP-94-sep-moment-r139.md')
SHA = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
STATS = []


def block(path, a=None, b=None):
    lines = (ROOT / path).read_text(encoding='utf-8').split('\n')
    if lines and lines[-1] == '':
        lines = lines[:-1]
    lo = 1 if a is None else max(1, a)
    hi = len(lines) if b is None else min(len(lines), b)
    STATS.append((path, hi - lo + 1))
    return "\n".join([f"===== FILE: {path} (строки {lo}–{hi}) =====",
                      "\n".join(lines[lo - 1:hi]), "===== END FILE ====="])


def whole(path):
    return block(path)


def lines_of(path):
    return (ROOT / path).read_text(encoding='utf-8').split('\n')


def pick(path, pats, before=1, after=3, dedupe=True):
    """Строки файла, попадающие в окно вокруг каждого шаблона (для табличных регистров)."""
    L = lines_of(path)
    idx = set()
    for p in pats:
        for i, l in enumerate(L):
            if re.search(p, l):
                idx.update(range(max(0, i - before), min(len(L), i + after + 1)))
    if not idx:
        return f'({path}: по шаблонам {pats} ничего не найдено)'
    out = sorted(idx)
    parts, run = [], [out[0]]
    for i in out[1:]:
        if i == run[-1] + 1:
            run.append(i)
        else:
            parts.append((run[0] + 1, run[-1] + 1)); run = [i]
    parts.append((run[0] + 1, run[-1] + 1))
    if dedupe:
        seen, uniq = set(), []
        for a, b in parts:
            key = '\n'.join(L[a - 1:b])
            if key not in seen:
                seen.add(key); uniq.append((a, b))
        parts = uniq
    return "\n\n".join(block(path, a, b) for a, b in parts)


def window(path, pat, before=8, after=45, nth=0):
    L = lines_of(path)
    hits = [i for i, l in enumerate(L) if re.search(pat, l)]
    if not hits:
        return f'({path}: раздел /{pat}/ не найден)'
    i = hits[min(nth, len(hits) - 1)]
    return block(path, i + 1 - before, i + 1 + after)


def numbers():
    """Выжимка чисел из опубликованных файлов (не FILE-блок, сгенерировано)."""
    import yaml, io
    cfg = yaml.safe_load(io.open(ROOT / 'specs/ptk_configs.yaml', encoding='utf-8'))
    rows = cfg if isinstance(cfg, list) else cfg.get('rows') or cfg.get('configs') or []
    des = yaml.safe_load(io.open(ROOT / 'specs/ptk_designs.yaml', encoding='utf-8'))
    out = ["## Выжимка чисел (сгенерировано из specs/ptk_configs.yaml и specs/ptk_designs.yaml)", ""]
    out.append("| Проработка | M шага 1, Н·м | M_by | D, мм | M трения венца / запас | d_bc |")
    out.append("|---|---|---|---|---|---|")
    for r in rows:
        if r.get('id', '').startswith(('PTK-063-R3X8', 'PTK-063-R2X4', 'PTK-063-R5X5', 'PTK-050-R3X8', 'PTK-050-R5X5')):
            out.append(f"| `{r.get('id')}` | {r.get('M')} | {r.get('M_by')} | {r.get('d_out')} | "
                       f"{r.get('t_hold')} / {r.get('safety')} | {r.get('d_bc')} |")
    out += ["", "### YAML-дамп строк шага 1 (K10/K20; файл целиком — 56 тыс. строк, в CTX не влезает)", "",
            "```yaml"]
    for r in rows:
        if r.get('id', '').startswith(('PTK-063-R3X8-22M6P2-BDBB72', 'PTK-063-R2X4_2-10M5P2-03CF7D')):
            out.append(yaml.safe_dump([r], allow_unicode=True, sort_keys=False, width=200).rstrip())
    out += ["```", ""]
    out += ["", "| Проработка | ok | u | R_Σ | Dш | окна n | стенка t | d_req | τ | σсм | .09 |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    for d in des:
        lay = d.get('layout') or {}
        us = lay.get('u') or (d.get('calc') or {}).get('u')
        out.append(f"| {d.get('name')} | {d.get('ok')} | {us} | {lay.get('R_sum') or lay.get('r_sum')} | "
                   f"{lay.get('body') or lay.get('rol')} | {lay.get('n_sep') or lay.get('n')} | "
                   f"{lay.get('t_sep') or lay.get('t')} | {(lay.get('shaft') or {}).get('d_req')} | "
                   f"{(lay.get('shaft') or {}).get('tau')} | {(lay.get('key') or {}).get('sigma')} | "
                   f"{(lay.get('b09') or {}).get('id')} |")
    return "\n".join(out)


HEAD = f"""# CTX-T — CP-94: предел по переносу момента через ряд окон (M_sep), rev13.9

База: `{SHA}` (ветка `rev13.9`; содержит rev13.7 с CP-93…CP-97 и rev13.8 с новыми телами качения).
Продукт `euginb/HarmonicV2`, ПТК. Язык ответа — русский, комментарии в коде — русский, с номерами Д-##/CP-##.

## Правила вывода (INS-91B §6)

1. Ответ — два блока: `p.diff` (unified diff от указанной базы) и `upd.md` (что сделано, что проверено, что осталось).
2. Маркеры `===== FILE: … =====` / `===== END FILE =====` — только в этом CTX, в ответе их быть не должно.
3. Правки — минимальные; стиль и структура кода — как в приложенных файлах.

## Задача

Добавить в шаг 1 проверку сепаратора и учесть её в моменте исполнения. Сейчас
`M = min(M_H, M_B, t_hold/safety)` (`egm/ptk.py`), сепаратор в минимум не входит, поэтому K20
(`PTK-063-R3X8-22M6P2-BDBB72`) проходит с «✓» при M 1160.5 Н·м, а ручная оценка модели даёт предел
сепаратора 250…500 Н·м. Требуется:

1. `M_sep` — предел по трём механизмам: перенос момента через ряд окон (рама Виренделя), изгиб
   перемычки нагрузкой своего ряда, контакт тела со стороной окна (Герц + кромочный контакт).
2. Допускаемое — многоцикловая усталость (нагружение на каждый оборот входа): `[σ] = σ₋₁/(K·S)`,
   `K ≈ 2` в углах окон.
3. `M_sep` входит в `min(...)`, `M_by` получает значение «сепаратор», причина — `sep_why`.
4. Коэффициенты (K_окн, S_sep, k_edge и т. п.) — в `specs/ptk_input.yaml` с комментарием-глоссарием
   в `egm/ptk_doc.py`; в коде — без магических чисел.
5. Пересчитать K10/K20: ожидается падение M до 250…500 Н·м и смена `M_by`.
6. `self_test` фиксирует K20: σ в перемычке ≤ [σ], M_sep < M_H.

Стенка `t = 2.2·a_ω` задана кинематикой (запас по `sep_web_min` 0.06 мм) — поднимать её нельзя.

## Новое в этой ветке (важно для задачи)

- `specs/vendor_prices.yaml` → `rollers`: пользователь добавил тела **D5×5, D5×8, D6×6, D7×20, D8×8, D8×16**
  (было только 2 и 3 мм). Каталог приложен целиком ниже.
- После пересчёта шага 1 с новым каталогом тела D5…D8 дают `M = 0.0` и габарит 198…364 мм — то есть
  для u 50/63 они не проходят по габариту; рабочее тело по-прежнему `R3X8`. Это ожидаемо (CP-95/CP-97),
  но при реализации `M_sep` перебор тел уже включает новые.
- Ветка `rev13.8` (влита в `rev13.9`) содержит пользовательские правки схем ПТК и новые ролики.

"""

BODY = []
BODY.append(HEAD)
BODY.append("---\n\n# Исходники\n")
BODY.append("## Расчёт шага 1 и профиль\n")
BODY.append(whole('egm/ptk.py'))
BODY.append(whole('egm/ptk_force.py'))
BODY.append(whole('egm/ptk_profile.py'))
BODY.append(pick('egm/ptk_doc.py', [r'GLOSSARY', r'^\s*"limits"', r'^\s*"rollers"', r'M_H', r'M_B',
                                    r't_hold', r'safety'], before=1, after=2))
BODY.append("\n## Вход и каталоги\n")
BODY.append(whole('specs/ptk_input.yaml'))
BODY.append("### Каталог тел качения (файл, который просил добавить заказчик)\n")
BODY.append(whole('specs/vendor_prices.yaml'))
BODY.append("\n## Расчётная записка и спецификации\n")
BODY.append(whole('specs/SPEC-10_PTK_CALC.md'))
BODY.append(pick('specs/SPEC-11_PTK_DESIGN.md', [r'K20', r'K10', r'перемычк', r'сепаратор'], before=1, after=2))
BODY.append("\n## Регистры\n")
BODY.append(pick('specs/DECISIONS.md', [r'^- Д-41:', r'^- Д-42:', r'^- Д-116:', r'^- Д-117:',
                                        r'^\| OQ-08 ', r'^\| OQ-44 ', r'^\| OQ-10 '], before=0, after=0))
BODY.append(pick('specs/CODE_PLAN.md', [r'^\| CP-32 ', r'^\| CP-94 ', r'^\| CP-95 ', r'^\| CP-96 ', r'^\| CP-97 '],
                 before=0, after=0))
BODY.append("\n## Силовой расчёт: окна и сепаратор\n")
DOC = 'docs/Силовой расчет ПТК/Силовой расчет ПТК.md'
BODY.append(window(DOC, r'перемычк', before=10, after=40, nth=0))
BODY.append(window(DOC, r'сепаратор', before=6, after=30, nth=2))
BODY.append("\n## Точка регистрации self_test\n")
BODY.append(window('main.py', r'\("tech_proc"', before=4, after=6))

txt = "\n".join(BODY) + "\n\n" + numbers() + "\n"
OUT.write_text(txt, encoding='utf-8')
print('файл:', OUT.name)
print('размер:', len(txt.encode('utf-8')), 'Б |', txt.count('\n'), 'строк')
print('FILE-блоков:', txt.count('===== FILE:'))
big = sorted(STATS, key=lambda x: -x[1])[:8]
print('крупнейшие блоки:', big)
