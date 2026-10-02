"""Реестр изделий и номенклатура деталей (Д-24, SPEC-03)."""
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
        raise KeyError(f"{part_id}: позиции {p['prod']}.{p['nn']} нет в products.json")
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


def self_test():
    p = parse("PTK-063-R5X8-8M4P2-3F9A1C.01B")
    assert p == {"cfg": "PTK-063-R5X8-8M4P2-3F9A1C", "prod": "PTK", "nn": "01", "var": "B"}, p
    prods = {"PTK": {"parts": {"01": {"variant": "ring_phase"}}}}
    assert not check(prods, [{"parts": [{"id": "PTK-1-X.01A"}]}])
    assert check(prods, [{"parts": [{"id": "PTK-1-X.09"}]}])
    assert check(prods, [{"parts": [{"id": "bad"}]}])
    return True
