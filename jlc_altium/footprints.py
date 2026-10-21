"""Land patterns for the generic chip footprints (RES-0603, CAP-0402, ...).

Two rectangular SMD pads per footprint, sized like the IPC-7351 nominal
patterns KiCad ships for the same packages. One table serves every family
since resistor, capacitor, inductor and ferrite chips in a given size use
near-identical lands at JLCPCB. Review them against your own standards
before high-volume or fine-pitch work.
"""

from __future__ import annotations

# size: (pad length along X, pad width along Y, pad centre-to-centre), mm
# Body: (length, width), mm, drawn as the assembly outline and courtyard base.
CHIP_LANDS = {
    "0201": ((0.46, 0.40, 0.64), (0.6, 0.3)),
    "0402": ((0.54, 0.64, 1.02), (1.0, 0.5)),
    "0603": ((0.80, 0.95, 1.65), (1.6, 0.8)),
    "0805": ((1.025, 1.40, 1.825), (2.0, 1.25)),
    "1206": ((1.125, 1.75, 2.925), (3.2, 1.6)),
    "1210": ((1.125, 2.65, 2.925), (3.2, 2.5)),
}

COURTYARD_MARGIN = 0.25


def footprint_names(prefixes: list[str]) -> list[str]:
    return [f"{p}-{size}" for p in prefixes for size in CHIP_LANDS]


def courtyard(size: str) -> tuple[float, float]:
    """Half-extents (x, y) of the courtyard rectangle."""
    (pad_l, pad_w, pitch), (body_l, body_w) = CHIP_LANDS[size]
    x = max(pitch / 2 + pad_l / 2, body_l / 2) + COURTYARD_MARGIN
    y = max(pad_w / 2, body_w / 2) + COURTYARD_MARGIN
    return round(x, 3), round(y, 3)
