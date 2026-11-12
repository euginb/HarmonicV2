"""SPEC-12_SHAFTS.md — номенклатура входных валов (продукт SH, Д-107…Д-110; CP-91 этап 3).

Источник — specs/shafts.yaml (реестр, keys.table) и записи ptk_design.run (shaft, link, ecc,
layout, input.shaft_id). md() -> поля шаблона templates/SPEC-12_SHAFTS.md.tmpl; машинный
вид реестра — комментированный YAML на общем эмиттере doc_yaml.Doc (Д-105, Д-106), раздел 7.
"""
import yaml

from egm import doc_yaml, shafts

HEADER = "# Реестр конфигураций входных валов (SPEC-12, Д-107) — генерируется прогоном, не править"
GLOSSARY = {
    "id": "ID конфигурации SH-<d>-<link> — стабильный ключ (Д-107).",
    "name": "Наименование для спецификации и чертежа.",
    "d": "Ø вала, мм.",
    "bore": "Ø отверстия полого вала, мм; 0 — сплошной.",
    "link": "Соединение эксцентрик–вал: key | flat | integral | spline | press.",
    "applies_to": "Продукты, где конфигурация применяется.",
    "designs": "Проработки, выбравшие конфигурацию (input.shaft_id).",
    "key": "Шпонка b×h по keys.table (Д-109); null — без шпонки.",
    "grades": "Марки .15, подобранные в применяющих проработках (Д-110).",
    "note": "Примечание записи номенклатуры.",
}
BASIS = {"fatigue": "усталость", "static": "статика", "override": "переопределение",
         "default": "по умолчанию", "shaft": "вал", "ecc": "эксцентрик .03", "key": "шпонка"}
DESCR = {"bore": "Ø отверстия по умолчанию, мм", "link": "соединение по умолчанию",
         "wall_min": "мин. стенка полого вала у паза, мм (технологический)",
         "K_tau": "K_τ по типу соединения", "S": "запас по усталости (покрывает неучтённый изгиб)",
         "S_t": "запас по текучести", "S_crush": "запас по смятию",
         "m1_k": "σ₋₁ ≈ m1_k·σв, если нет sigma_m1", "tau_k": "τ = tau_k·σ",
         "bar_allow": "припуск на сторону пруток → вал, мм", "key_grade": "марка шпонки",
         "tau_allow": "[τ] без материала, МПа", "sigma_crush": "[σсм] без материала, МПа"}
THEORY = (
    "Допуски вала — расчёт из материала (Д-110): [τ] = min(τ₋₁/(K_τ·S), 0.58·σт/S_т), "
    "τ₋₁ = 0.58·σ₋₁, σ₋₁ ≈ 0.43·σв при отсутствии sigma_m1 в materials.yaml; определяющий "
    "критерий — меньший из двух (усталость или статика). [σсм] = min(σт вала, σт .03, σт "
    "шпонки)/S_см; лимитирующая деталь указана. Запас S берёт на себя неучтённый изгиб — "
    "роль прежнего заниженного [τ] = 25 МПа.\n\n"
    "Марка .15 — первая из products.yaml → PTK.parts.15.material, у которой есть σв/σт, "
    "пруток Ø ≥ d + 2·припуск в stock.yaml (в пределах d_range) и проходят τ и σсм; отказы — "
    "раздел 5. bore_max — наибольшее отверстие, при котором τ ≤ [τ] и стенка у паза ≥ "
    "wall_min. Ручной допуск — переопределением в проработке (designs[].shaft.tau_allow), "
    "критерий «переопределение».")


class _Shafts(doc_yaml.Doc):
    """Реестр валов: шапка и таблица комментариев."""
    HEADER = HEADER
    GLOSSARY = GLOSSARY


_DOC = _Shafts()


def dump(recs):
    """Записи реестра -> комментированный YAML."""
    return _DOC.dump(recs)


def _f(x, fmt="g"):
    return "—" if x is None else format(x, fmt)


def _key(keys, d):
    return next((k for k in keys if d <= k["d_max"] + 1e-9), None)


def md(res, nomen=None):
    """Записи проработок + номенклатура -> поля шаблона SPEC-12."""
    nomen = shafts.load() if nomen is None else (nomen or {})
    reg = nomen.get("shafts") or {}
    keys = sorted(((nomen.get("keys") or {}).get("table")) or [], key=lambda k: k["d_max"])
    des = [r for r in res if r.get("shaft")]
    by = {}
    for r in des:
        by.setdefault((r.get("input") or {}).get("shaft_id") or "", []).append(r)

    K = ["| d_max, мм | b | h | t1 | t2 |", "|---|---|---|---|---|"]
    K += [f"| {k['d_max']:g} | {k['b']:g} | {k['h']:g} | {k['t1']:g} | {k['t2']:g} |" for k in keys]
    R = ["| ID | Наименование | d, мм | bore, мм | Соединение | Примечание |", "|---|---|---|---|---|---|"]
    A = ["| ID | Продукты | Проработки | Исполнения ПТК |", "|---|---|---|---|"]
    recs = []
    for sid, rec in reg.items():
        rec, rs = rec or {}, by.get(sid, [])
        d, link = float(rec.get("d", 0.0)), rec.get("link", "key")
        R.append(f"| {sid} | {rec.get('name', '')} | {d:g} | {_f(rec.get('bore', 0.0))} | {link} | "
                 f"{rec.get('note', '')} |")
        A.append(f"| {sid} | {', '.join(rec.get('applies_to') or []) or '—'} | "
                 f"{', '.join(r['name'] for r in rs) or '—'} | "
                 f"{', '.join(sorted({r['id'] for r in rs})) or '—'} |")
        k = _key(keys, d) if link == "key" else None
        recs.append({"id": sid, "name": rec.get("name", ""), "d": d,
                     "bore": float(rec.get("bore", 0.0)), "link": link,
                     "applies_to": list(rec.get("applies_to") or []),
                     "designs": [r["name"] for r in rs],
                     "key": f"{k['b']:g}×{k['h']:g}" if k else None,
                     "grades": sorted({r["shaft"]["grade"] for r in rs if r["shaft"].get("grade")}),
                     "note": rec.get("note", "")})
    if by.get(""):
        A.append(f"| блок (устар., Д-107) | PTK | {', '.join(r['name'] for r in by[''])} | "
                 f"{', '.join(sorted({r['id'] for r in by['']}))} |")

    C = ["| Проработка | Вал | τ / [τ], МПа | [τ]: критерий, марка | d_req, мм | Шпонка | "
         "σсм / [σсм], МПа | [σсм]: деталь | Стенки .03 (эксц. / паз), мм | bore_max, мм | Итог |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    M = ["| Проработка | Марка .15 | Состояние | Свойства | Заготовка | Отказы марок |",
         "|---|---|---|---|---|---|"]
    Dv = ["| Проработка | Вал | Шпонка b×h | Паз вала t1 | Паз .03 t2 | Ø отв. .03, мм | Подшипник .10 |",
          "|---|---|---|---|---|---|---|"]
    stub = shafts.DEFAULTS["tau_allow"]
    for r in des:
        s, k, e = r["shaft"], r.get("link") or {}, r.get("ecc") or {}
        sid = (r.get("input") or {}).get("shaft_id") or "блок"
        tb = s.get("tau_basis", "default")
        crit = f"{BASIS.get(tb, tb)}, {s.get('grade') or '—'}"
        if tb in ("fatigue", "static"):
            crit += f" (было {stub:g} — заглушка до Д-110)"
        sg = (f"{k['sigma']:g} / {k.get('sigma_allow', s.get('sigma_crush')):g}"
              if k.get("sigma") is not None else "—")
        kb = f"{k['b']:g}×{k['h']:g}" if k.get("b") else "—"
        walls = "—"
        if e.get("De") is not None:
            kw = min((x["key_wall"] for x in e.get("rows", [])), default=None)
            walls = f"{e['De'] / 2 - e['a'] - s['d'] / 2:.2f} / {_f(kw, '.2f')}"
        C.append(f"| {r['name']} | {sid} | {s['tau']:g} / {s['tau_allow']:g} | {crit} | "
                 f"{s['d_req']:g} | {kb} | {sg} | {BASIS.get(s.get('crush_basis'), '—')} | "
                 f"{walls} | {_f(s.get('bore_max'))} | {'✓' if r['ok'] else '✗'} |")
        rj = "; ".join(f"{x['grade']}: {x['why']}" for x in s.get("rejected") or []) or "—"
        M.append(f"| {r['name']} | {s.get('grade') or '—'} | {s.get('state') or '—'} | "
                 f"{s.get('props', '—')} | {s.get('blank') or '—'} | {rj} |")
        b10 = ((r.get("layout") or {}).get("b10")) or {}
        Dv.append(f"| {r['name']} | {sid} | {kb} | {_f(k.get('t1'))} | {_f(k.get('t2'))} | "
                  f"{s['d']:g} | {b10.get('id', '—')} (d {_f(b10.get('d'))}) |")

    DF = ["| Параметр | Значение | Смысл |", "|---|---|---|"]
    for name, v in shafts.DEFAULTS.items():
        v = ", ".join(f"{a} {b:g}" for a, b in v.items()) if isinstance(v, dict) else v
        DF.append(f"| {name} | {v} | {DESCR.get(name, '')} |")
    return {"n_cfg": len(reg), "n_des": len(des), "keys": "\n".join(K),
            "registry": "\n".join(R), "apply": "\n".join(A),
            "checks": "\n".join(C) if len(C) > 2 else "нет проработок",
            "material": "\n".join(M) if len(M) > 2 else "нет проработок",
            "derived": "\n".join(Dv) if len(Dv) > 2 else "нет проработок",
            "defaults": "\n".join(DF), "yaml": dump(recs).rstrip("\n"), "theory": THEORY}


def self_test():
    """Разделы SPEC-12 из записи проработки; машинный вид — 100 % комментариев, round-trip."""
    nomen = {"keys": {"table": [{"d_max": 10, "b": 3, "h": 3, "t1": 1.8, "t2": 1.4}]},
             "shafts": {"SH-10-KEY": {"name": "Ø10", "d": 10.0, "bore": 0.0, "link": "key",
                                      "applies_to": ["PTK"], "note": "n"}}}
    res = [{"id": "PTK-T", "name": "K10", "ok": True, "input": {"shaft_id": "SH-10-KEY"},
            "shaft": {"d": 10.0, "tau": 23.1, "tau_allow": 39.2, "tau_basis": "fatigue",
                      "d_req": 9.1, "sigma_crush": 101.4, "crush_basis": "key", "grade": "40Х",
                      "state": "улучшение", "props": "materials.yaml", "blank": "пруток Ø12",
                      "bore_max": 3.4, "rejected": [{"grade": "45", "why": "нет прутка"}]},
            "link": {"type": "key", "b": 3, "h": 3, "t1": 1.8, "t2": 1.4, "sigma": 52.1,
                     "sigma_allow": 101.4},
            "ecc": {"De": 30.0, "a": 0.4, "rows": [{"key_wall": 3.0}]}, "layout": None}]
    m = md(res, nomen)
    assert "SH-10-KEY" in m["registry"] and "K10" in m["apply"] and "40Х" in m["material"], m
    assert "усталость" in m["checks"] and "45: нет прутка" in m["material"], m
    back = yaml.safe_load(m["yaml"])
    assert back[0]["id"] == "SH-10-KEY" and back[0]["key"] == "3×3", back
    for k in back[0]:
        assert _DOC.comment(k), k
    return True
