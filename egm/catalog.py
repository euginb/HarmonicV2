"""Парсер каталога HIWIN HG (CAT-01) -> БД JSON, пары рельс+каретка (Д-10), проверки.

Все числа берутся из docs/HG-Series-Catalog_opt.md. В коде — только правила
разбора таблиц и формула раскладки отверстий рельса L = (n-1)*P + 2*E (Eq. 2.1).
"""
import json
import re

BLOCK_RE = re.compile(r"^HG([HWL])(\d{2})([CH])([ABC])$")
RAIL_T_RE = re.compile(r"^HGR(\d{2})T$")
SIZE_RE = re.compile(r"^HG(\d{2})$")
RAIL_COLS = ("WR", "HR", "D", "h", "d", "P", "E", "rail_bolt")
KEYS = {"Масса блока": "mass_block_kg", "Масса рельса": "mass_rail_kg_m",
        "Масса": "mass_rail_kg_m", "Mxl": "M", "M (Ø)": "M", "Болт для рельса": "rail_bolt"}
DASH = {"–", "—", "-", ""}
PN_FMT = "EGC-HG-{type}{size}{load}{mount}-{cls}-{pre}{bottom}"  # Д-10


def _key(h):
    k = h.split(",")[0].strip()
    return KEYS.get(k, k.split(" (")[0])


def _val(s):
    s = s.strip()
    if s in DASH:
        return None
    t = s.replace(",", "")
    return float(t) if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", t) else s


def _lengths(cell):
    return [[float(a.replace(",", "")), int(b)]
            for a, b in re.findall(r"([\d,.]+)\s*\((\d+)\)", cell)]


def _tables(text):
    """Markdown-таблицы: {'title', 'header', 'rows'}; title — последний заголовок/жирная строка."""
    title, cur = "", None
    for ln in text.split("\n"):
        s = ln.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if cur is None:
                cur = {"title": title, "header": cells, "rows": []}
            elif all(c and set(c) <= set("-: ") for c in cells):
                continue
            else:
                cur["rows"].append(cells)
            continue
        if cur is not None:
            yield cur
            cur = None
        if s.startswith("#"):
            title = s.lstrip("#").strip()
        elif s.startswith("**"):
            title = s
    if cur is not None:
        yield cur


def _size(db, size):
    return db["sizes"].setdefault(str(size), {})


def _row_size(cell):
    m = SIZE_RE.match(cell.strip())
    return int(m[1]) if m else None


def _set_rail(db, rid, size, mount, data):
    r = db["rails"].setdefault(rid, {"size": size, "mount": mount, "dims": {}})
    for k, v in data.items():
        if v is None:
            continue
        old = r["dims"].get(k)
        if old is not None and old != v:
            db["conflicts"].append(f"{rid}.{k}: {old} ≠ {v}")
        else:
            r["dims"][k] = v


def _model_table(db, hdr, rows):
    for row in rows:
        model = row[0].strip()
        cells = {k: _val(c) for k, c in zip(hdr[1:], row[1:])}
        mt = RAIL_T_RE.match(model)
        if mt:
            _set_rail(db, model, int(mt[1]), "T", cells)
            continue
        mb = BLOCK_RE.match(model)
        if not mb:
            db["unparsed"].append(f"модель {model}")
            continue
        size = int(mb[2])
        b = db["blocks"].setdefault(model, {"type": mb[1], "size": size, "load": mb[3],
                                            "mount": mb[4], "dims": {}, "loads": {}})
        if "C0" in cells:
            rail_mass = cells.pop("mass_rail_kg_m", None)
            b["loads"].update(cells)
            _set_rail(db, f"HGR{size}R", size, "R", {"mass_rail_kg_m": rail_mass})
        else:
            rail = {k: cells.pop(k) for k in RAIL_COLS if k in cells}
            b["dims"].update(cells)
            _set_rail(db, f"HGR{size}R", size, "R", rail)


def _size_table(db, t):
    title, h, rows = t["title"], t["header"], t["rows"]
    if any("Стандартные длины" in c for c in h):
        for row in rows:
            size = _row_size(row[0])
            if size is None:
                continue
            mx = _lengths(row[4])
            _size(db, size).update({"lengths": _lengths(row[1]), "P": _val(row[2]),
                                    "Es": _val(row[3]),
                                    "max_std": mx[0][0] if mx else _val(row[4]),
                                    "max_len": _val(row[5])})
    elif len(h) > 1 and all(re.fullmatch(r"Z[0A-Z]", c) for c in h[1:]):
        key = ("parallel_um" if "2-1-21" in title else
               "height_um" if "2-1-22" in title else None)
        if key is None:
            db["unparsed"].append(title[:70])
            return
        for p in h[1:]:
            if p not in db["preloads"]:
                db["preloads"].append(p)
        for row in rows:
            size = _row_size(row[0])
            if size is not None:
                _size(db, size)[key] = {p: _val(v) for p, v in zip(h[1:], row[1:])}
    elif "2-1-23" in title:
        cols = [(re.search(r"\b(r1|r2|E1|E2|H1)\b", c) or [None])[0] for c in h]
        for row in rows:
            size = _row_size(row[0])
            if size is not None:
                _size(db, size)["mounting"] = {c: _val(v) for c, v in zip(cols[1:], row[1:]) if c}
    else:
        db["unparsed"].append(f"{title[:70]} | Типоразмер")


def _accuracy_table(db, t):
    cls = [re.search(r"\(([A-Z]{1,2})\)", c) for c in t["header"][1:]]
    cls = [m[1] if m else None for m in cls]
    for c in cls:
        if c and c not in db["classes"]:
            db["classes"].append(c)
    db["accuracy"][t["title"][:80]] = {
        r[0]: {c: _val(v) for c, v in zip(cls, r[1:]) if c} for r in t["rows"]}


def parse_md(text, source=""):
    m = re.search(r"G\d{2}TE\d+-\d+", text)
    db = {"source": source, "catalog": m[0] if m else None, "classes": [], "preloads": [],
          "blocks": {}, "rails": {}, "sizes": {}, "accuracy": {}, "unparsed": [],
          "conflicts": []}
    for t in _tables(text):
        if not t["rows"]:
            continue
        first = t["header"][0]
        if first == "Модель":
            _model_table(db, [_key(h) for h in t["header"]], t["rows"])
        elif first == "Типоразмер":
            _size_table(db, t)
        elif first.startswith("Параметр") and re.search(r"\([A-Z]{1,2}\)", " ".join(t["header"])):
            _accuracy_table(db, t)
        else:
            db["unparsed"].append(f"{t['title'][:70]} | {first}")
    return db


def build_pairs(db):
    pairs = {}
    for model, b in sorted(db["blocks"].items()):
        avail = db["sizes"].get(str(b["size"]), {}).get("parallel_um") or {}
        for cls in db["classes"]:
            for pre in db["preloads"]:
                if avail and avail.get(pre) is None:
                    continue  # натяг не поставляется для типоразмера (прочерк в 2-1-21)
                for mount in ("R", "T"):
                    rail = f"HGR{b['size']}{mount}"
                    if rail not in db["rails"]:
                        continue
                    pn = PN_FMT.format(type=b["type"], size=b["size"], load=b["load"],
                                       mount=b["mount"], cls=cls, pre=pre,
                                       bottom="-T" if mount == "T" else "")
                    pairs[pn] = {"block": model, "rail": rail, "class": cls,
                                 "preload": pre, "order_block": f"{model}{pre}{cls}"}
    return {"format": "EGC-HG-<тип><размер><нагр><крепл>-<класс>-<натяг>[-T] (Д-10)",
            "pairs": pairs}


def pairs_json(p):
    """Одна пара — одна строка, чтобы файл оставался читаемым в diff."""
    body = ",\n".join(f"  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}"
                      for k, v in p["pairs"].items())
    return ('{\n "format": ' + json.dumps(p["format"], ensure_ascii=False)
            + ',\n "pairs": {\n' + body + "\n }\n}\n")


def resolve(pn, pairs, db):
    """Каталожный номер -> каретка + рельс; KeyError = несовместимость/неизвестный номер."""
    if pn not in pairs["pairs"]:
        raise KeyError(f"{pn}: нет в catalog_hiwin_hg_pairs.json "
                       f"(несовместимая или неизвестная комбинация)")
    p = pairs["pairs"][pn]
    return {**p, "block_data": db["blocks"][p["block"]], "rail_data": db["rails"][p["rail"]]}


def rail_holes(db, size, length, e_min=None):
    """Раскладка отверстий рельса: L = (n-1)*P + 2*E; E >= e_min (по умолчанию Es)."""
    s = db["sizes"][str(size)]
    P, Es = s["P"], s["Es"]
    e_min = Es if e_min is None else e_min
    n = int((length - 2 * e_min) // P) + 1
    E = (length - (n - 1) * P) / 2
    w = []
    if n < 2:
        w.append(f"L={length:g}: меньше двух отверстий")
    if s.get("max_len") and length > s["max_len"]:
        w.append(f"L={length:g} > макс. {s['max_len']:g}: нужен составной рельс")
    if E > P / 2:
        w.append(f"E={E:.1f} > P/2: рекомендуется L={(n - 1) * P + 2 * Es:g}")
    return {"L": length, "n": n, "E": round(E, 2), "P": P, "warnings": w}


def validate(db, pairs, prices):
    err, warn = list(db["conflicts"]), []
    if not db["blocks"]:
        err.append("не распознано ни одной каретки")
    if not db["classes"]:
        err.append("не распознаны классы точности")
    if not db["preloads"]:
        err.append("не распознаны классы натяга")
    for m, b in db["blocks"].items():
        if not b["dims"]:
            err.append(f"{m}: нет размеров")
        if not b["loads"]:
            err.append(f"{m}: нет грузоподъёмности")
    for size in sorted({b["size"] for b in db["blocks"].values()}):
        s = db["sizes"].get(str(size), {})
        r = db["rails"].get(f"HGR{size}R", {}).get("dims", {})
        if not s.get("lengths") or not s.get("P") or not s.get("Es"):
            warn.append(f"HG{size}: нет данных стандартных длин рельса (2-1-25)")
            continue
        if r.get("P") != s["P"]:
            err.append(f"HG{size}: шаг P в таблице размеров {r.get('P')} ≠ {s['P']} в 2-1-25")
        for L, n in s["lengths"]:
            h = rail_holes(db, size, L)
            if h["n"] != n:
                err.append(f"HG{size}: L={L:g} — формула 2.1 даёт n={h['n']}, в каталоге {n}")
        t = db["rails"].get(f"HGR{size}T")
        if t is None:
            warn.append(f"HG{size}: нет рельса HGR{size}T")
            continue
        for k in ("WR", "HR", "P", "E"):
            if t["dims"].get(k) is not None and t["dims"][k] != r.get(k):
                err.append(f"HGR{size}T.{k}={t['dims'][k]} ≠ HGR{size}R.{k}={r.get(k)}")
    known = (set(db["blocks"]) | set(db["rails"]) | set(pairs["pairs"])
             | set(prices.get("rollers", {})))
    no_price = 0
    for k, v in prices.get("items", {}).items():
        if k.startswith("_"):
            continue
        if k not in known:
            warn.append(f"vendor_prices: позиция {k} не найдена в каталогах")
        if v.get("price") is None:
            no_price += 1
    stats = {"blocks": len(db["blocks"]), "rails": len(db["rails"]),
             "sizes": len(db["sizes"]), "pairs": len(pairs["pairs"]), "no_price": no_price}
    return {"errors": err, "warnings": warn, "stats": stats}


def report_md(db, pairs, rep):
    st = rep["stats"]
    L = ["# Отчёт разбора каталога HIWIN HG (code-first, НЕ ПРАВИТЬ РУКАМИ)", "",
         f"Источник: `docs/{db['source']}`, каталог {db['catalog']}. "
         f"Генерирует `egm/catalog.py` (CP-02).", "",
         f"Кареток: {st['blocks']}, рельсов: {st['rails']}, типоразмеров: {st['sizes']}, "
         f"пар (Д-10): {st['pairs']}.",
         f"Классы точности: {', '.join(db['classes'])}; натяг: {', '.join(db['preloads'])}.",
         f"Позиций vendor_prices без цены: {st['no_price']}.", "",
         "## Каретки", "", "| Модель | H | W | L | C, кН | C0, кН | Масса, кг |",
         "|---|---|---|---|---|---|---|"]
    for m, b in sorted(db["blocks"].items()):
        d, ld = b["dims"], b["loads"]
        L.append(f"| {m} | {d.get('H')} | {d.get('W')} | {d.get('L')} | {ld.get('C')} | "
                 f"{ld.get('C0')} | {ld.get('mass_block_kg')} |")
    L += ["", "## Рельсы", "", "| Рельс | WR | HR | P | E | Болт | Масса, кг/м |",
          "|---|---|---|---|---|---|---|"]
    for rid, r in sorted(db["rails"].items()):
        d = r["dims"]
        L.append(f"| {rid} | {d.get('WR')} | {d.get('HR')} | {d.get('P')} | {d.get('E')} | "
                 f"{d.get('rail_bolt', d.get('S'))} | {d.get('mass_rail_kg_m')} |")
    L += ["", "## Типоразмеры", "",
          "| HG | P | Es | Макс. станд. L | Макс. L | Параллельность по натягу, µm |",
          "|---|---|---|---|---|---|"]
    for k, s in sorted(db["sizes"].items(), key=lambda kv: int(kv[0])):
        L.append(f"| {k} | {s.get('P')} | {s.get('Es')} | {s.get('max_std')} | "
                 f"{s.get('max_len')} | {s.get('parallel_um')} |")
    ex = [pn for pn in pairs["pairs"] if "H20CA" in pn][:6]
    L += ["", "## Примеры каталожных номеров", ""]
    L += [f"- `{pn}` = {pairs['pairs'][pn]['order_block']} + {pairs['pairs'][pn]['rail']}"
          for pn in ex] or ["нет"]
    L += ["", "## Ошибки", ""] + ([f"- {e}" for e in rep["errors"]] or ["нет"])
    L += ["", "## Предупреждения", ""] + ([f"- {w}" for w in rep["warnings"]] or ["нет"])
    L += ["", "## Нераспознанные таблицы (информационно)", ""]
    L += [f"- {u}" for u in db["unparsed"]] or ["нет"]
    return "\n".join(L) + "\n"


SAMPLE = """**Table 2-1-25 Rail Standard Length**

| Типоразмер | Стандартные длины L(n), мм | Pitch P, мм | Distance to End Es, мм | Макс. стандартная длина, мм | Макс. длина, мм |
|---|---|---|---|---|---|
| HG15 | 160 (3), 1,960 (33) | 60 | 20 | 1,960 (33) | 2,000 |
"""


def self_test():
    db = parse_md(SAMPLE)
    s = db["sizes"]["15"]
    assert s["lengths"] == [[160.0, 3], [1960.0, 33]] and s["max_len"] == 2000.0, s
    assert rail_holes(db, 15, 160)["n"] == 3 and rail_holes(db, 15, 1960)["n"] == 33
    assert _val("–") is None and _val("M4x16") == "M4x16" and _val("1,960") == 1960.0
    assert BLOCK_RE.match("HGW20CC") and not BLOCK_RE.match("HGR20R")
    return True
