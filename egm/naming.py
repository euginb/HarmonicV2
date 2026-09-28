"""Маркировка станков (SPEC-01, Д-02, Д-09): код S<T>-<N>-<L> и производные имена.

Компоновка L входит в код станка и во все производные имена, поэтому варианты
HMC (основной) и VMC (сравнение) одной машины не конфликтуют.
"""
import re

CODE_RE = re.compile(r"^S([A-Z])-(\d+)-([A-Z]{3})$")
TYPES = {"M": "фрезерный (milling)",
         "E": "прошивочный электроэрозионный (erosion, ЭЭС)"}
LAYOUTS = {"HMC": "горизонтальная компоновка (шпиндель/электрод и ось Z горизонтальны)",
           "VMC": "вертикальная компоновка (шпиндель/электрод и ось Z вертикальны)"}
PRIMARY_LAYOUT = "HMC"  # Д-09
MACHINES = ("SM-1-HMC", "SE-1-HMC", "SM-1-VMC", "SE-1-VMC")
GROUPS = ("FR", "EM", "AX-X", "AX-Y", "AX-Z", "AX-C", "SP", "TK", "FX", "AC")


def parse(code):
    m = CODE_RE.match(code)
    if not m or m[1] not in TYPES or m[3] not in LAYOUTS:
        raise ValueError(f"неверный код станка {code!r} (SPEC-01)")
    return {"code": code, "type": m[1], "n": int(m[2]), "layout": m[3],
            "base": f"S{m[1]}-{m[2]}", "primary": m[3] == PRIMARY_LAYOUT,
            "title": f"{TYPES[m[1]]}, вариант {m[2]}, {LAYOUTS[m[3]]}"}


def variants(base):
    """'SM-1' -> ['SM-1-HMC', 'SM-1-VMC'] — все компоновки для сравнения."""
    return [f"{base}-{lay}" for lay in LAYOUTS]


def spec_path(code):
    return f"machines/{parse(code)['code']}.md"


def tree_path(code):
    return f"machines/{parse(code)['code']}.json"


def cad_dir(code):
    return f"cad/{parse(code)['code']}"


def node_id(code, group, *nums):
    parse(code)
    if group not in GROUPS:
        raise ValueError(f"неизвестная группа {group!r} (SPEC-01)")
    return ".".join([code, group] + [f"{n:02d}" for n in nums])


def owner(node):
    return parse(node.split(".")[0])


def self_test():
    p = parse("SM-1-HMC")
    assert p["primary"] and p["base"] == "SM-1"
    assert not parse("SE-1-VMC")["primary"]
    assert variants("SE-1") == ["SE-1-HMC", "SE-1-VMC"]
    assert node_id("SE-1-HMC", "AX-X", 2) == "SE-1-HMC.AX-X.02"
    assert owner("SE-1-HMC.AX-X.02")["layout"] == "HMC"
    assert spec_path("SM-1-HMC") != spec_path("SM-1-VMC")
    for c in MACHINES:
        parse(c)
    for bad in ("SM-1", "SX-1-HMC", "SM-1-XYZ"):
        try:
            parse(bad)
            raise AssertionError(f"принят неверный код {bad}")
        except ValueError:
            pass
    return True
