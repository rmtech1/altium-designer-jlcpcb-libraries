"""Decides which generic Altium table a part belongs to and extracts its values.

Only two-terminal, non-polarised chip parts get a generic symbol: resistors,
MLCCs, inductors and ferrite beads in standard chip sizes. For those, a
generic symbol plus a size-named footprint is always correct. Everything
else (ICs, diodes, transistors, polarised caps...) has part-specific pinouts
and goes through `jlc-altium fetch` and the overrides file instead.
"""

from __future__ import annotations

import re

CHIP_SIZES = ("01005", "0201", "0402", "0603", "0805", "1008", "1206",
              "1210", "1806", "1812", "2010", "2512", "2920")
_SIZE_RE = re.compile(r"^[A-Z]?(%s)(?![0-9])" % "|".join(CHIP_SIZES), re.I)

FAMILIES = ("resistor", "capacitor", "inductor", "ferrite")

# Extra columns per family: (column name, attribute keys to try, description regex)
_NUM = r"(\d+(?:\.\d+)?)"
FIELDS = {
    "resistor": [
        ("Resistance", ("Resistance",), _NUM + r"\s*([mkKMG]?)\s*(?:Ω|Ohm|ohm)"),
        ("Tolerance", ("Tolerance",), r"(±\s*\d+(?:\.\d+)?%)"),
        ("Power Rating", ("Power(Watts)", "Power", "Power Rating"), _NUM + r"\s*([mk]?W)\b"),
        ("Temperature Coefficient", ("Temperature Coefficient",), r"(±\s*\d+\s*ppm/[°℃]?C?)"),
    ],
    "capacitor": [
        ("Capacitance", ("Capacitance",), _NUM + r"\s*([pnuµμm]?F)\b"),
        ("Tolerance", ("Tolerance",), r"(±\s*\d+(?:\.\d+)?%|±\s*\d+(?:\.\d+)?pF)"),
        ("Voltage Rating", ("Voltage Rated", "Rated Voltage", "Voltage - Rated"), _NUM + r"\s*(k?V)\b"),
        ("Dielectric", ("Temperature Coefficient", "Dielectric"), r"\b(C0G|NP0|X5R|X6S|X7R|X7S|X7T|X8R|Y5V|Z5U)\b"),
    ],
    "inductor": [
        ("Inductance", ("Inductance",), _NUM + r"\s*([nuµμm]?H)\b"),
        ("Tolerance", ("Tolerance",), r"(±\s*\d+(?:\.\d+)?%|±\s*\d+(?:\.\d+)?nH)"),
        ("Rated Current", ("Rated Current", "Current Rating"), _NUM + r"\s*(m?A)\b"),
        ("DC Resistance", ("DC Resistance(DCR)", "DC Resistance"), _NUM + r"\s*(m?Ω)\b"),
    ],
    "ferrite": [
        ("Impedance @ Frequency", ("Impedance @ Frequency",), r"(\d+(?:\.\d+)?\s*[kK]?Ω\s*@\s*\d+(?:\.\d+)?\s*[kMG]?Hz)"),
        ("Rated Current", ("Current Rating", "Rated Current"), _NUM + r"\s*(m?A)\b"),
        ("DC Resistance", ("DC Resistance(DCR)", "DC Resistance"), _NUM + r"\s*(m?Ω)\b"),
    ],
}

# The column whose value becomes Value/Comment on the schematic.
VALUE_FIELD = {
    "resistor": "Resistance",
    "capacitor": "Capacitance",
    "inductor": "Inductance",
    "ferrite": "Impedance @ Frequency",
}


def chip_size(package: str) -> str | None:
    m = _SIZE_RE.match(package.strip())
    return m.group(1) if m else None


def family(part: dict) -> str | None:
    cat = f"{part['category']} / {part['subcategory']}".lower()
    desc = part["description"].lower()

    if cat.strip(" /"):
        if "ferrite" in cat:
            return "ferrite"
        if "chip resistor" in cat:
            return "resistor"
        if "mlcc" in cat or "multilayer ceramic" in cat:
            return "capacitor"
        if "inductor" in cat and not any(w in cat for w in ("choke", "transformer", "coupled", "array")):
            return "inductor"
        return None

    # No category (e.g. CSV without the categories table): use the description.
    if "ferrite bead" in desc:
        return "ferrite"
    if re.search(r"\b(thick|thin) film\b.*resistor|chip resistor", desc) and "array" not in desc:
        return "resistor"
    if "multilayer ceramic" in desc or "mlcc" in desc:
        return "capacitor"
    if re.search(r"\binductor\b", desc) and not any(w in desc for w in ("choke", "transformer", "coupled", "array")):
        return "inductor"
    return None


def _clean(value: str) -> str:
    return re.sub(r"\s+", "", value).replace("μ", "µ")


def fields(fam: str, part: dict) -> dict:
    out = {}
    attrs = part["attributes"]
    for column, keys, pattern in FIELDS[fam]:
        value = next((attrs[k] for k in keys if attrs.get(k)), None)
        if value is None:
            m = re.search(pattern, part["description"])
            if m:
                value = "".join(g for g in m.groups() if g)
                if column == "Resistance":
                    value += "Ω"
        out[column] = _clean(value) if value else ""
    return out


def classify(part: dict) -> tuple[str, str] | None:
    """Return (family, chip size) when the part fits a generic table."""
    size = chip_size(part["package"])
    if not size:
        return None
    fam = family(part)
    return (fam, size) if fam else None
