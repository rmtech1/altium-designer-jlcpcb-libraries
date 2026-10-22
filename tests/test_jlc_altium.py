import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from jlc_altium import altium_script, build, categorize, dblib, fab, footprints, lookup, parts, source
from jlc_altium.config import Config, load

PRICE = json.dumps([{"qFrom": 1, "qTo": 99, "price": 0.0012}, {"qFrom": 100, "qTo": None, "price": 0.0008}])

# (lcsc, category, subcategory, mfr, package, description, stock, basic, preferred, extra)
PARTS = [
    (25804, "Resistors", "Chip Resistor - Surface Mount", "0603WAF1002T5E", "0603",
     "100mW Thick Film Resistors 75V ±1% ±100ppm/℃ 10kΩ 0603 Chip Resistor - Surface Mount ROHS",
     5_000_000, 1, 0, {"attributes": {"Resistance": "10kΩ", "Tolerance": "±1%", "Power(Watts)": "100mW"}}),
    (99999, "Resistors", "Chip Resistor - Surface Mount", "RC0603FR-0710KL", "0603",
     "10kΩ ±1% 100mW Thick Film Resistor 0603", 200, 0, 0, None),
    (14663, "Capacitors", "Multilayer Ceramic Capacitors MLCC - SMD/SMT", "CL10B104KB8NNNC", "0603",
     "50V 100nF X7R ±10% 0603 Multilayer Ceramic Capacitors MLCC - SMD/SMT ROHS", 9_000_000, 1, 0, None),
    (1015, "Inductors & Chokes & Transformers", "Ferrite Beads", "GZ1608D601TF", "0603",
     "600Ω@100MHz 500mA 300mΩ 0603 Ferrite Beads ROHS", 100_000, 1, 0, None),
    (6186, "Power Management ICs", "Linear Voltage Regulators (LDO)", "AMS1117-3.3", "SOT-223",
     "1A 3.3V Fixed LDO SOT-223", 300_000, 0, 1, None),
    (7777, "Resistors", "Chip Resistor - Surface Mount", "LOWSTOCK", "0402",
     "1kΩ ±1% 62.5mW 0402 Thick Film Resistor", 3, 0, 0, None),
]


def make_jlcparts_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE manufacturers (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE categories (id INTEGER PRIMARY KEY, category TEXT, subcategory TEXT);
        CREATE TABLE components (lcsc INTEGER PRIMARY KEY, category_id INTEGER, mfr TEXT,
            package TEXT, joints INTEGER, manufacturer_id INTEGER, basic INTEGER,
            description TEXT, datasheet TEXT, stock INTEGER, price TEXT, last_update INTEGER,
            extra TEXT, flag INTEGER, last_on_stock INTEGER, preferred INTEGER);
    """)
    cats = {}
    for i, p in enumerate(PARTS):
        key = (p[1], p[2])
        if key not in cats:
            cats[key] = len(cats) + 1
            con.execute("INSERT INTO categories VALUES (?,?,?)", (cats[key], *key))
        con.execute("INSERT INTO manufacturers VALUES (?,?)", (i + 1, f"Maker{i}"))
        con.execute("INSERT INTO components (lcsc, category_id, mfr, package, manufacturer_id, basic, "
                    "description, datasheet, stock, price, extra, preferred) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (p[0], cats[(p[1], p[2])], p[3], p[4], i + 1, p[7], p[5], "https://x/ds.pdf",
                     p[6], PRICE, json.dumps(p[9]) if p[9] else None, p[8]))
    con.commit()
    con.close()


def make_config(base: Path, **filter_) -> Config:
    cfg = load(Path(__file__).resolve().parent.parent / "config.toml")
    cfg = Config(raw=json.loads(json.dumps(cfg.raw)), base=base)
    cfg.raw["filter"].update(filter_)
    return cfg


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.raw = self.tmp / "cache.sqlite3"
        make_jlcparts_db(self.raw)
        self.cfg = make_config(self.tmp, min_stock_extended=100)

    def rows(self, table):
        con = sqlite3.connect(self.cfg.database_path)
        con.row_factory = sqlite3.Row
        out = {r["LCSC"]: dict(r) for r in con.execute(f'SELECT * FROM "{table}"')}
        con.close()
        return out

    def test_generic_tables(self):
        counts = build.build(source.read(self.raw, 100), self.cfg, today="2026-10-21")
        self.assertEqual(counts, {"Resistors": 2, "Capacitors": 1, "Inductors": 0,
                                  "Ferrite Beads": 1, "Custom": 0})
        r = self.rows("Resistors")["C25804"]
        self.assertEqual(r["Library Ref"], "Resistor")
        self.assertEqual(r["Footprint Ref"], "RES-0603")
        self.assertEqual(r["Value"], "10kΩ")
        self.assertEqual(r["JLCPCB Type"], "Basic")
        self.assertEqual(r["Manufacturer"], "Maker0")
        self.assertEqual(r["Price"], "$0.0012")
        self.assertEqual(r["Price @100"], "$0.0008")
        # Extended part: value parsed from the description.
        self.assertEqual(self.rows("Resistors")["C99999"]["Resistance"], "10kΩ")
        c = self.rows("Capacitors")["C14663"]
        self.assertEqual((c["Capacitance"], c["Voltage Rating"], c["Dielectric"], c["Tolerance"]),
                         ("100nF", "50V", "X7R", "±10%"))
        self.assertEqual(self.rows("Ferrite Beads")["C1015"]["Value"], "600Ω@100MHz")

    def test_only_part_tables(self):
        # Altium shows every table as a library, so nothing else may exist.
        build.build(source.read(self.raw), self.cfg, today="2026-10-22")
        con = sqlite3.connect(self.cfg.database_path)
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertEqual(tables, set(build.TABLES.values()) | {build.CUSTOM_TABLE})
        self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0], 20261022)
        con.close()

    def test_low_stock_extended_dropped(self):
        build.build(source.read(self.raw, 100), self.cfg)
        self.assertNotIn("C7777", self.rows("Resistors"))

    def test_overrides_and_carry_over(self):
        parts.link(self.cfg, "c6186", "AMS1117-3.3", "SOT-223-3", "JLC_Custom.SchLib", "JLC_Custom.PcbLib")
        build.build(source.read(self.raw), self.cfg)
        row = self.rows("Custom")["C6186"]
        self.assertEqual(row["JLCPCB Type"], "Preferred")
        self.assertEqual(row["Library Ref"], "AMS1117-3.3")
        self.assertEqual(row["Stock"], 300000)
        # Part vanishes from the source: last known details are kept, stock is 0.
        build.build(iter([]), self.cfg)
        row = self.rows("Custom")["C6186"]
        self.assertEqual(row["Stock"], 0)
        self.assertEqual(row["Manufacturer Part Number"], "AMS1117-3.3")

    def test_copy_into_live_db(self):
        build.build(source.read(self.raw), self.cfg)
        other = self.tmp / "other.sqlite"
        con = sqlite3.connect(other)
        con.execute('CREATE TABLE "Resistors" ("LCSC" TEXT)')
        con.execute("INSERT INTO Resistors VALUES ('C1')")
        con.commit()
        con.close()
        con = sqlite3.connect(other)
        con.execute("PRAGMA user_version = 20261022")
        con.close()
        build._copy_into(other, self.cfg.database_path)
        self.assertEqual(list(self.rows("Resistors")), ["C1"])
        con = sqlite3.connect(self.cfg.database_path)
        self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0], 20261022)
        con.close()

    def test_csv_source(self):
        path = self.tmp / "basic.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["lcsc", "mfr", "package", "description", "stock", "price", "basic", "preferred"])
            w.writerow([25804, "0603WAF1002T5E", "0603", PARTS[0][5], 100, PRICE, "True", "False"])
            w.writerow([14663, "CL10B104KB8NNNC", "0603", PARTS[2][5], 100, PRICE, "1", "0"])
        counts = build.build(source.read(path), self.cfg)
        self.assertEqual((counts["Resistors"], counts["Capacitors"]), (1, 1))

    def test_dblib(self):
        text = dblib.render(Path(r"C:\lib\JLCPCB.sqlite"), Path(r"C:\lib"))
        self.assertIn("DRIVER=SQLite3 ODBC Driver;Database=C:\\lib\\JLCPCB.sqlite;", text)
        self.assertIn("TableName=Ferrite Beads", text)
        self.assertIn("TableName=Custom", text)


class CategorizeTest(unittest.TestCase):
    def part(self, desc, package="0603", category="", sub=""):
        return {"description": desc, "package": package, "category": category,
                "subcategory": sub, "attributes": {}}

    def test_sizes(self):
        self.assertEqual(categorize.chip_size("0603"), "0603")
        self.assertEqual(categorize.chip_size("R0402"), "0402")
        self.assertIsNone(categorize.chip_size("SOT-23"))
        self.assertIsNone(categorize.chip_size("06035"))

    def test_description_fallback(self):
        self.assertEqual(categorize.classify(self.part("10kΩ ±1% Thick Film Resistor")), ("resistor", "0603"))
        self.assertIsNone(categorize.classify(self.part("4 x 10kΩ Thick Film Resistor Array")))
        self.assertEqual(categorize.classify(self.part("Multilayer Ceramic Capacitors 1uF")), ("capacitor", "0603"))
        self.assertIsNone(categorize.classify(self.part("Common Mode Choke Inductor")))

    def test_category_wins(self):
        p = self.part("whatever", category="Diodes", sub="Switching Diodes")
        self.assertIsNone(categorize.classify(p))


class FabTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.bom = self.tmp / "board.csv"
        self.bom.write_text(
            '"Comment","Description","Designator","Footprint","LCSC","Quantity"\n'
            '"10kΩ","Resistor","R1, R2","RES-0603","C25804","2"\n'
            '"AMS1117-3.3","LDO","U1","SOT-223-3","C6186","1"\n'
            '"TP","Test point","TP1","TP-1MM","","1"\n', encoding="utf-8")
        self.pnp = self.tmp / "pnp.csv"
        self.pnp.write_text(
            "Altium Designer Pick and Place Locations\nUnits used:\tmil\n\n"
            '"Designator","Comment","Layer","Footprint","Center-X(mil)","Center-Y(mil)","Rotation","Description"\n'
            '"R1","10k","TopLayer","RES-0603","1000","500","90","R"\n'
            '"R2","10k","BottomLayer","RES-0603","1100mil","500mil","0","R"\n'
            '"U1","LDO","TopLayer","SOT-223-3","2000","2000","270","U"\n'
            '"TP1","TP","TopLayer","TP-1MM","0","0","0","TP"\n', encoding="utf-8")
        self.rot = self.tmp / "rot.csv"
        self.rot.write_text('"Footprint pattern","Correction"\n"C25804",90\n"^SOT-223",180\n', encoding="utf-8")

    def test_fab(self):
        bom_out, cpl_out, missing = fab.run(self.bom, self.pnp, self.tmp / "out", self.rot)
        self.assertEqual(missing, ["TP1"])
        bom = list(csv.DictReader(bom_out.read_text(encoding="utf-8").splitlines()))
        self.assertEqual(bom[0], {"Comment": "10kΩ", "Designator": "R1,R2",
                                  "Footprint": "RES-0603", "LCSC Part #": "C25804"})
        cpl = {r["Designator"]: r for r in csv.DictReader(cpl_out.read_text(encoding="utf-8").splitlines())}
        self.assertEqual(set(cpl), {"R1", "R2", "U1"})
        self.assertEqual(cpl["R1"]["Mid X"], "25.4000mm")
        self.assertEqual(cpl["R1"]["Rotation"], "180")
        self.assertEqual(cpl["R2"]["Layer"], "Bottom")
        self.assertEqual(cpl["U1"]["Rotation"], "90")

    def test_check(self):
        raw = self.tmp / "cache.sqlite3"
        make_jlcparts_db(raw)
        report = {r["lcsc"]: r for r in lookup.check_bom(self.bom, raw, self.tmp / "none.sqlite", boards=10)}
        self.assertEqual(report["C25804"]["status"], "OK")
        self.assertEqual(report["C25804"]["need"], 20)
        self.assertEqual(report["C6186"]["type"], "Preferred")
        self.assertEqual(report["-"]["status"], "NO LCSC CODE")

    def test_search(self):
        raw = self.tmp / "cache.sqlite3"
        make_jlcparts_db(raw)
        self.assertEqual([p["lcsc"] for p in lookup.search(raw, ["Maker4"])], ["C6186"])
        self.assertEqual([p["lcsc"] for p in lookup.search(raw, ["10kΩ", "0603"])], ["C25804", "C99999"])
        self.assertEqual([p["lcsc"] for p in lookup.search(raw, ["10kΩ"], basic_only=True)], ["C25804"])

    def test_alternatives(self):
        raw = self.tmp / "cache.sqlite3"
        make_jlcparts_db(raw)
        cfg = make_config(self.tmp)
        build.build(source.read(raw), cfg)
        ext = next(p for p in source.read(raw) if p["lcsc"] == "C99999")
        alts = lookup.alternatives(cfg.database_path, ext)
        self.assertEqual([a["LCSC"] for a in alts], ["C25804"])


class AltiumScriptTest(unittest.TestCase):
    def test_render(self):
        tmp = Path(tempfile.mkdtemp()) / "it's here"
        cfg = make_config(tmp)
        text = altium_script.render(cfg)
        # Paths are Pascal string literals with quotes doubled.
        self.assertIn("it''s here", text)
        self.assertIn("AddSymbol(Lib, 'Ferrite Bead', 'FB', 'DrawFerrite');", text)
        names = footprints.footprint_names(["RES", "CAP", "IND", "FB"])
        for name in names:
            self.assertIn(f"AddChip(Lib, '{name}',", text)
        self.assertEqual(text.count("AddChip(Lib, '"), len(names))
        self.assertNotIn("%(", text)

    def test_write(self):
        cfg = make_config(Path(tempfile.mkdtemp()))
        prj = altium_script.write(cfg)
        self.assertIn("DocumentPath=JLC_Setup.pas", prj.read_text())
        self.assertTrue((prj.parent / "JLC_Setup.pas").exists())

    def test_courtyard_covers_pads(self):
        for size, ((pad_l, pad_w, pitch), _) in footprints.CHIP_LANDS.items():
            cx, cy = footprints.courtyard(size)
            self.assertGreater(cx, pitch / 2 + pad_l / 2)
            self.assertGreater(cy, pad_w / 2)


class KicadSymTest(unittest.TestCase):
    def test_symbol_for(self):
        tmp = Path(tempfile.mkdtemp()) / "lib.kicad_sym"
        tmp.write_text('''(kicad_symbol_lib (version 20211014) (generator https://github.com/uPesy/easyeda2kicad.py)
  (symbol "NE555P" (in_bom yes) (on_board yes)
    (property "Reference" "U" (id 0) (at 0 0 0))
    (property "Footprint" "JLC_Custom:DIP-8_L9.6-W6.4-P2.54" (id 2) (at 0 0 0))
    (property "LCSC Part" "C46749" (id 5) (at 0 0 0))
    (symbol "NE555P_0_1" (rectangle (start 0 0) (end 1 1)))
  )
  (symbol "AMS1117-3.3 \\"x\\"" (in_bom yes)
    (property "Footprint" "JLC_Custom:SOT-223-3" (id 2) (at 0 0 0))
    (property "LCSC Part" "C6186" (id 5) (at 0 0 0))
  )
)
''', encoding="utf-8")
        self.assertEqual(parts.symbol_for(tmp, "C46749"), ("NE555P", "DIP-8_L9.6-W6.4-P2.54"))
        self.assertEqual(parts.symbol_for(tmp, "C6186"), ('AMS1117-3.3 \\"x\\"', "SOT-223-3"))


if __name__ == "__main__":
    unittest.main()
