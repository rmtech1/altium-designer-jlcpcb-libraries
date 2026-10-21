"""Linking non-generic parts (ICs, diodes, connectors...) to the database.

`link` records an LCSC code against a symbol and footprint you already have.
`fetch` downloads the part's EasyEDA symbol, footprint and 3D model with
easyeda2kicad (pip install easyeda2kicad) into library/Custom/KiCad. Import
that folder once with Altium's Import Wizard (KiCad format) into
JLC_Custom.SchLib / JLC_Custom.PcbLib; the symbol and footprint names are
kept by the import, so the overrides row written here resolves.
"""

from __future__ import annotations

import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .build import OVERRIDE_COLUMNS, read_overrides
from .config import Config

CUSTOM_SCHLIB = "JLC_Custom.SchLib"
CUSTOM_PCBLIB = "JLC_Custom.PcbLib"
KICAD_LIB_NAME = "JLC_Custom"


def link(cfg: Config, lcsc: str, symbol: str, footprint: str,
         symbol_lib: str = "", footprint_lib: str = "", comment: str = "") -> bool:
    """Add or replace an overrides row. Returns True if it was new."""
    lcsc = lcsc.strip().upper()
    if not re.match(r"^C\d+$", lcsc):
        raise SystemExit(f"not an LCSC code: {lcsc}")
    path = cfg.overrides_path
    rows = read_overrides(path)
    new = not any(r["LCSC"] == lcsc for r in rows)
    rows = [r for r in rows if r["LCSC"] != lcsc]
    rows.append({"LCSC": lcsc, "Library Ref": symbol, "Library Path": symbol_lib,
                 "Footprint Ref": footprint, "Footprint Path": footprint_lib,
                 "Comment": comment, "Value": ""})
    rows.sort(key=lambda r: int(r["LCSC"][1:]))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OVERRIDE_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return new


def _top_level_symbols(text: str) -> list[str]:
    """Top-level (symbol ...) blocks of a .kicad_sym file."""
    blocks, depth, start = [], 0, None
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '"':
            i += 1
            while i < len(text) and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
        elif ch == "(":
            depth += 1
            if depth == 2 and text.startswith("(symbol ", i):
                start = i
        elif ch == ")":
            if depth == 2 and start is not None:
                blocks.append(text[start:i + 1])
                start = None
            depth -= 1
        i += 1
    return blocks


def _prop(block: str, name: str) -> str | None:
    m = re.search(r'\(property\s+"%s"\s+"((?:[^"\\]|\\.)*)"' % re.escape(name), block)
    return m.group(1) if m else None


def _symbols(kicad_sym: Path) -> dict[str, str]:
    """Top-level symbol name -> block."""
    if not kicad_sym.exists():
        return {}
    out = {}
    for block in _top_level_symbols(kicad_sym.read_text(encoding="utf-8")):
        out[re.match(r'\(symbol\s+"((?:[^"\\]|\\.)*)"', block).group(1)] = block
    return out


def symbol_for(kicad_sym: Path, lcsc: str, before: set[str] = frozenset()) -> tuple[str, str]:
    """(symbol name, footprint name) of the symbol easyeda2kicad wrote for lcsc.

    Matches the symbol's LCSC property; failing that, the one symbol that
    was not in the library before the download.
    """
    symbols = _symbols(kicad_sym)
    match = [n for n, b in symbols.items()
             if (_prop(b, "LCSC Part") or _prop(b, "LCSC") or "").upper() == lcsc]
    if not match:
        match = [n for n in symbols if n not in before]
    if len(match) != 1:
        raise SystemExit(f"could not tell which symbol in {kicad_sym} is {lcsc}; "
                         f"link it by hand with: jlc-altium link {lcsc} SYMBOL FOOTPRINT")
    footprint = (_prop(symbols[match[0]], "Footprint") or "").split(":")[-1]
    return match[0], footprint


def fetch(cfg: Config, lcsc: str) -> tuple[str, str, Path]:
    lcsc = lcsc.strip().upper()
    out_dir = cfg.output_dir / "Custom" / "KiCad"
    out_dir.mkdir(parents=True, exist_ok=True)
    exe = shutil.which("easyeda2kicad")
    cmd = [exe] if exe else [sys.executable, "-m", "easyeda2kicad"]
    sym_file = out_dir / f"{KICAD_LIB_NAME}.kicad_sym"
    before = set(_symbols(sym_file))
    cmd += ["--full", f"--lcsc_id={lcsc}", f"--output={out_dir / KICAD_LIB_NAME}", "--overwrite"]
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        raise SystemExit("easyeda2kicad is not installed: pip install easyeda2kicad")
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"easyeda2kicad failed for {lcsc} (exit {e.returncode})")
    symbol, footprint = symbol_for(sym_file, lcsc, before)
    link(cfg, lcsc, symbol, footprint, CUSTOM_SCHLIB, CUSTOM_PCBLIB)
    return symbol, footprint, out_dir
