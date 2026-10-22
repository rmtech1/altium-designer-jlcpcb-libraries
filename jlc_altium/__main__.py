"""jlc-altium: keep a JLCPCB parts library for Altium Designer up to date.

    python -m jlc_altium setup             first-time setup (or just run setup.cmd)
    python -m jlc_altium update            download latest data, rebuild the database
    python -m jlc_altium status            show when the database was last built
    python -m jlc_altium search LDO 3.3V   search the downloaded JLCPCB data
    python -m jlc_altium fetch C6186       download symbol/footprint/3D for a part
    python -m jlc_altium link C6186 SYM FP link a part to your own symbol/footprint
    python -m jlc_altium check BOM.csv     check stock / basic status of a BOM
    python -m jlc_altium fab BOM.csv PnP.csv   write JLCPCB BOM + CPL files
    python -m jlc_altium rotations --download  fetch the rotation-correction list
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from . import build, dblib, download, fab, installer, lookup, parts, source
from .config import Config, load


def raw_source(cfg: Config, kind: str | None = None) -> tuple[Path, str | None]:
    """(local path of the raw data, URL to refresh it from or None)."""
    src = cfg.section("source")
    kind = kind or src.get("kind", "basic")
    if kind == "file":
        if not src.get("path"):
            raise SystemExit("source.kind = 'file' needs source.path")
        return cfg.path(src["path"]), None
    if kind == "full":
        return cfg.cache_dir / "jlcpcb-components.sqlite3", src.get("full_url")
    if kind == "basic":
        return cfg.cache_dir / "jlcpcb-components-basic-preferred.csv", src.get("basic_url")
    raise SystemExit(f"unknown source kind: {kind}")


def _require(path: Path) -> Path:
    if not path.exists():
        raise SystemExit(f"{path} not found; run `python -m jlc_altium update` first")
    return path


def cmd_update(cfg: Config, args) -> None:
    raw, url = raw_source(cfg, args.source)
    changed = False
    if url and not args.offline:
        print(f"Checking {url}")
        changed = download.fetch(url, raw)
    _require(raw)
    db = cfg.database_path
    if not changed and db.exists() and not args.rebuild and db.stat().st_mtime >= max(
            raw.stat().st_mtime, cfg.overrides_path.stat().st_mtime if cfg.overrides_path.exists() else 0):
        print("Database already up to date.")
    else:
        print(f"Building {db} from {raw.name}")
        min_stock = int(cfg.section("filter").get("min_stock_extended", 0))
        counts = build.build(source.read(raw, min_stock), cfg)
        for table, n in counts.items():
            print(f"  {table:<14} {n:>7} parts")
    if args.write_dblib or not cfg.dblib_path.exists():
        dblib.write(cfg.dblib_path, db)
        print(f"Wrote {cfg.dblib_path}")


def cmd_setup(cfg: Config, args) -> None:
    args.source, args.offline, args.rebuild, args.write_dblib = None, False, False, True
    sys.exit(installer.run(cfg, args, cmd_update))


def cmd_status(cfg: Config, args) -> None:
    db = _require(cfg.database_path)
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    v = str(con.execute("PRAGMA user_version").fetchone()[0])
    updated = f"{v[:4]}-{v[4:6]}-{v[6:]}" if len(v) == 8 else "unknown date"
    print(f"{db}\n  built from data of {updated}")
    for table in list(build.TABLES.values()) + [build.CUSTOM_TABLE]:
        n = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        print(f"  {table:<14} {n:>7} parts")
    con.close()


def cmd_search(cfg: Config, args) -> None:
    raw, _ = raw_source(cfg)
    hits = lookup.search(_require(raw), args.terms, args.basic, args.limit)
    for p in hits:
        print(f"{p['lcsc']:<10} {build.jlc_type(p):<9} {p['stock']:>8}  {p['package']:<16} "
              f"{p['mfr']:<24} {p['description'][:70]}")
    if not hits:
        print("No matches.")


def cmd_fetch(cfg: Config, args) -> None:
    for code in args.lcsc:
        symbol, footprint, folder = parts.fetch(cfg, code)
        print(f"{code.upper()}: symbol '{symbol}', footprint '{footprint}'")
    print(f"\nKiCad files are in {folder}. Import them into Altium (File > Import Wizard > KiCad)\n"
          f"as {parts.CUSTOM_SCHLIB} / {parts.CUSTOM_PCBLIB} in {cfg.output_dir}, then run update.")


def cmd_link(cfg: Config, args) -> None:
    new = parts.link(cfg, args.lcsc, args.symbol, args.footprint,
                     args.symbol_lib, args.footprint_lib, args.comment)
    print(f"{'Added' if new else 'Updated'} {args.lcsc.upper()} in {cfg.overrides_path}; run update to apply.")


def cmd_check(cfg: Config, args) -> None:
    raw, _ = raw_source(cfg)
    report = lookup.check_bom(Path(args.bom), _require(raw), cfg.database_path, args.boards)
    problems = 0
    for r in report:
        flag = "" if r["status"] == "OK" and r["type"] != "Extended" else "!"
        problems += bool(flag)
        line = f"{flag:1} {r['lcsc']:<10} {r['type']:<9} need {r['need']:>5}  stock {r['stock']!s:>8}  {r['status']}  {r['designators']}"
        if r["alternatives"]:
            line += f"\n      basic/preferred alternatives: {r['alternatives']}"
        print(line)
    print(f"\n{len(report)} lines, {problems} need attention (extended parts carry a feeder fee).")
    if any(r["status"] != "OK" for r in report):
        sys.exit(1)


def cmd_fab(cfg: Config, args) -> None:
    rotations = cfg.path(cfg.section("fab").get("rotations", "rotations.csv"))
    out_dir = Path(args.out) if args.out else Path(args.bom).parent
    bom_out, cpl_out, missing = fab.run(Path(args.bom), Path(args.pnp), out_dir, rotations)
    print(f"Wrote {bom_out}\nWrote {cpl_out}")
    if missing:
        print(f"Not assembled (no LCSC code): {', '.join(missing)}")
    if not rotations.exists():
        print("No rotation corrections loaded; run `rotations --download` or create "
              f"{rotations}. Always check the placement preview on JLCPCB.")


def cmd_rotations(cfg: Config, args) -> None:
    sect = cfg.section("fab")
    path = cfg.path(sect.get("rotations", "rotations.csv"))
    if args.download:
        download.fetch(sect["rotations_url"], path)
        print("Note: this list is written for KiCad's standard footprints. Footprints from\n"
              "`fetch` (EasyEDA) already match JLCPCB's orientation and can be wrongly\n"
              "rotated by its regex rules (e.g. ^SOT-23); remove rules that do not apply.")
    rules = fab.load_rotations(path)
    print(f"{path}: {len(rules)} rules")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="jlc-altium", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", help="config file (default: config.local.toml or config.toml)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("setup", help="first-time setup: driver, database, Altium script, daily task")
    p.add_argument("-y", "--yes", action="store_true", help="don't ask questions")
    p.add_argument("--no-task", action="store_true", help="don't register the daily update task")
    p.set_defaults(func=cmd_setup)

    p = sub.add_parser("update", help="download latest JLCPCB data and rebuild the database")
    p.add_argument("--source", choices=("basic", "full", "file"), help="override source.kind")
    p.add_argument("--offline", action="store_true", help="rebuild from the cached download")
    p.add_argument("--rebuild", action="store_true", help="rebuild even if nothing changed")
    p.add_argument("--write-dblib", action="store_true", help="regenerate the .DbLib file")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("status", help="show the database build date and part counts")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("search", help="search the downloaded JLCPCB data")
    p.add_argument("terms", nargs="+")
    p.add_argument("--basic", action="store_true", help="basic and preferred parts only")
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("fetch", help="download EasyEDA symbol/footprint/3D for LCSC parts")
    p.add_argument("lcsc", nargs="+")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("link", help="link an LCSC part to an existing symbol and footprint")
    p.add_argument("lcsc")
    p.add_argument("symbol")
    p.add_argument("footprint")
    p.add_argument("--symbol-lib", default="", help="SchLib file name (default: search)")
    p.add_argument("--footprint-lib", default="", help="PcbLib file name (default: search)")
    p.add_argument("--comment", default="")
    p.set_defaults(func=cmd_link)

    p = sub.add_parser("check", help="check an Altium BOM against current JLCPCB stock")
    p.add_argument("bom")
    p.add_argument("--boards", type=int, default=1, help="number of boards to assemble")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("fab", help="convert Altium BOM + Pick & Place to JLCPCB format")
    p.add_argument("bom")
    p.add_argument("pnp")
    p.add_argument("--out", help="output folder (default: next to the BOM)")
    p.set_defaults(func=cmd_fab)

    p = sub.add_parser("rotations", help="show or download rotation corrections")
    p.add_argument("--download", action="store_true")
    p.set_defaults(func=cmd_rotations)

    args = ap.parse_args(argv)
    args.func(load(args.config), args)


if __name__ == "__main__":
    main()
