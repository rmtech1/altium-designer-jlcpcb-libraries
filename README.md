# Altium Designer JLCPCB Libraries (self-updating)

A JLCPCB parts library for Altium Designer that **updates itself every day**,
in the spirit of [Bouni/kicad-jlcpcb-tools](https://github.com/Bouni/kicad-jlcpcb-tools).

[gsuberland/altium_jlcpcb_libraries](https://github.com/gsuberland/altium_jlcpcb_libraries)
ships pre-built `.SchLib` snapshots: when JLCPCB changes stock, prices or
basic/extended status, you wait for the next release. This project uses
Altium's own **Database Library (DbLib)** mechanism instead. Altium reads part
data live from a SQLite file, and a scheduled job rebuilds that file from
JLCPCB's daily parts dump. Symbols and footprints stay static, because they
never change. All the data that does change (stock, price, basic/preferred
status, new parts) is refreshed every day.

## Does Altium have plugins like KiCad?

Not in the same way. KiCad has an open Python plugin API, which
kicad-jlcpcb-tools uses to run a whole GUI inside the PCB editor. Altium has:

| Mechanism | What it is | Fit for JLCPCB data |
|---|---|---|
| **Database Libraries (DbLib)** | Components defined by rows in an external database (Access, SQL Server, or any ODBC source). Each row names a symbol, a footprint and parameters. | **Best fit, and used here.** Altium is built to read part data that changes outside Altium. It supports search in the Components panel and *Update Parameters From Database*. |
| Scripting (DelphiScript / VBScript / JScript) | Scripts run from *File » Run Script*, with access to the document API and COM. | Possible for small helpers. A full search GUI would be fragile and hard to share. |
| Extensions SDK | Compiled .NET/Delphi add-ons. | Distributing third-party extensions is restricted, so this is not a practical route for a community tool. |
| Manufacturer Part Search / Altium 365 | Built-in supplier data, sourced from Octopart. | Useful for sourcing, but it doesn't know JLCPCB's basic/extended library or assembly stock. |
| Vendor plugins (SamacSys, Ultra Librarian) | Download symbols/footprints per part. | These are per-part model sources, not a JLCPCB catalogue. |

So the KiCad plugin's jobs are split across native Altium features plus a
small command-line tool:

| kicad-jlcpcb-tools feature | Here |
|---|---|
| Downloads a daily parts database | `update`, run daily by Windows Task Scheduler |
| Search parts and assign LCSC numbers | Altium **Components panel** on the DbLib, plus `search` for any JLCPCB part |
| Parts keep current data | DbLib + *Tools » Update Parameters From Database* |
| Footprints/symbols for any LCSC part | `fetch C12345` (EasyEDA models via easyeda2kicad), then a one-time Altium import |
| Generate BOM + CPL for JLCPCB | `fab` converts Altium's BOM and Pick & Place outputs, with rotation corrections |
| Warn about stock / extended parts | `check` checks the BOM against today's stock and suggests basic alternatives |

## How it works

```
 JLCPCB parts list ──daily──► yaqwsx/jlcparts ──► CDFER/jlcpcb-parts-database
                                                       │ (CSV 3 MB / SQLite 1 GB, daily ~06:00 UTC)
                                                       ▼
 Task Scheduler ─► python -m jlc_altium update ─► library/JLCPCB.sqlite ◄─ ODBC ─ library/JLCPCB.DbLib
                         ▲                          Resistors | Capacitors |          │
     overrides/parts.csv ┘  (your ICs etc.)         Inductors | Ferrite Beads |      ▼
                                                    Custom                 Altium Components panel
```

* **Generic tables:** Resistors, Capacitors (MLCC), Inductors and Ferrite Beads
  in standard chip sizes (01005–2920). Every part uses one generic symbol and a
  size-named footprint (`RES-0603`, `CAP-0402`, `IND-0805`, `FB-0603`). These
  are the same names gsuberland's libraries use, so the same footprints work
  for both. Values, tolerance, voltage, dielectric and so on are parsed into
  columns you can filter on.
* **Custom table:** Anything with a part-specific pinout (ICs, diodes,
  transistors, connectors, polarised caps) is deliberately *not* given a
  generic symbol, because a wrong pinout is worse than no part. Link these
  parts once with `fetch` or `link`. After that their stock, price and type
  are refreshed on every update like everything else.
* **Columns:** Every table has these columns: `Part Number` (the LCSC code,
  used as the DbLib key), `LCSC`, `Manufacturer`, `Manufacturer Part Number`,
  `JLCPCB Type` (Basic / Preferred / Extended), `Stock`, `Price`, `Price @100`,
  `Datasheet`, `JLCPCB URL`, `Updated`.
* **Altium stays open:** Updates are safe while Altium is open. Normally the
  database file is swapped atomically. If Altium has it locked, the new data
  is written into it in one transaction instead.

## Setup (Windows, once)

1. **Install Python 3.11+** from python.org (tick *Add to PATH*). The tool
   needs nothing beyond the standard library. For `fetch`, you also need
   `pip install easyeda2kicad`.
2. **Install the 64-bit SQLite ODBC driver** ("SQLite3 ODBC Driver",
   `sqliteodbc_w64.exe` from <http://www.ch-werner.de/sqliteodbc/>). Altium
   is 64-bit, so the 32-bit driver will not work.
3. **Clone this repo and build the database:**
   ```bat
   git clone https://github.com/rmtech1/altium-designer-jlcpcb-libraries
   cd altium-designer-jlcpcb-libraries
   python -m jlc_altium update
   ```
   This writes `library\JLCPCB.sqlite` and `library\JLCPCB.DbLib`. The DbLib
   holds the absolute path to the database, so it is generated on your
   machine rather than committed.
4. **Create the generic symbols:** `library\Symbols\JLC_Generic.SchLib` must
   contain symbols named `Resistor`, `Capacitor`, `Inductor` and
   `Ferrite Bead`. You can do either of these:
   * Import `library\Symbols\JLC_Generic.kicad_sym` with *File » Import
     Wizard » KiCad* and save the result as `JLC_Generic.SchLib`.
   * Copy symbols you already like (for example from *Miscellaneous
     Devices.IntLib*) into a new SchLib and rename them.

   The names are set in `config.toml` under `[symbols]`.
5. **Create the footprints:** Put footprints named `RES-0402`, `CAP-0603`,
   `IND-0805`, `FB-0603` and so on in any PcbLib that is installed or added
   to your project. Altium's *Tools » IPC Compliant Footprints Batch
   Generator* makes these quickly. 0402/0603/0805 cover all basic passives and
   most extended ones. If you already use gsuberland's libraries, your
   footprints already match.
6. **Install the library in Altium:** Open the *Components* panel, then
   *⋮ » File-based Libraries Preferences » Installed » Install*, and pick
   `library\JLCPCB.DbLib`. Open the DbLib once and check that all five tables
   show and `Part Number` is the key field. Then save it.
7. **Schedule the daily update:**
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\install-scheduled-task.ps1
   ```
   This adds a daily task, 07:45 by default (`-At 09:00` to change, `-Remove`
   to delete). Output goes to `library\update.log`. You can also run
   `scripts\update.cmd` at any time.

## Day-to-day use

**Place passives:** In the Components panel, choose the JLCPCB library and
filter by `JLCPCB Type = Basic`, `Package = 0603`, `Value = 10kΩ`. Tables
list basic parts first.

**Keep placed parts current:** In a schematic, run *Tools » Update
Parameters From Database*. It pulls today's stock, price and type into every
placed part, matched by LCSC code. Do this before ordering.

**Add an IC or other part-specific component:**
```bat
python -m jlc_altium search LDO 3.3V SOT-23 --basic
python -m jlc_altium fetch C6186 C46749
```
`fetch` downloads the EasyEDA symbol, footprint and 3D model into
`library\Custom\KiCad\`. Import that folder once with the Import Wizard
(KiCad) and save the results as `library\JLC_Custom.SchLib` /
`JLC_Custom.PcbLib`. Then run `update`, and the part appears in the
**Custom** table. To use a symbol and footprint you already have, run this
instead:
```bat
python -m jlc_altium link C6186 AMS1117-3.3 SOT-223-3 --symbol-lib MyParts.SchLib
```
Links live in `overrides/parts.csv`. Commit that file to share your linked
parts with your team.

**Before ordering, check the BOM:** Add the `LCSC` parameter as a column in
your BomDoc and export it as CSV. Then run:
```bat
python -m jlc_altium check Project.csv --boards 10
```
It flags parts that are out of stock, low on stock for that many boards,
extended (feeder fee), or missing an LCSC code. For extended passives it
suggests basic or preferred parts with the same value and size.

**Make the JLCPCB assembly files:** Export the BOM (CSV) and the Pick & Place
file (*File » Assembly Outputs » Generates pick and place files*, CSV, any
units). Then run:
```bat
python -m jlc_altium fab Project.csv "Pick Place for Project.csv"
```
It writes `Project_JLCPCB_BOM.csv` and `Project_JLCPCB_CPL.csv`. Parts
without an LCSC code are left out of both files and listed.

**Rotation corrections:** Put rules in `rotations.csv` as
`pattern,degrees`. A pattern can be an exact LCSC code (`C6186,180`) or a
regex on the footprint name (`^SOT-89,90`). The first match wins. Footprints
from `fetch` come from EasyEDA, which JLCPCB uses itself, so they usually
need no correction. `rotations --download` fetches matthewlai's community
list, but that list is written for KiCad footprint names. Review it before
use. In every case, check the placement preview on JLCPCB's order page.

## Configuration

`config.toml` (copy it to `config.local.toml` for personal changes):

* `source.kind`:
  * `basic` (default): basic and preferred parts only, 3 MB.
  * `full`: every part with stock of 5 or more, about 1 GB, re-downloaded
    only when upstream changes.
  * `file`: your own jlcparts-format SQLite or CSV.

  Use `full` if you want extended passives or `check`/`search` coverage of
  extended ICs.
* `filter.min_stock_extended`: The minimum stock for an extended part to be
  listed. The default is 100.
* `[symbols]` and `[footprints]`: Symbol names, footprint prefixes and
  optional pinned libraries.

## Troubleshooting

* **"Data source name not found" when opening the DbLib:** The 64-bit
  SQLite3 ODBC driver is missing. Check *ODBC Data Sources (64-bit) »
  Drivers*.
* **Tables or parameters look wrong:** Run `python -m jlc_altium update
  --write-dblib` to regenerate the DbLib. Then open it in Altium, check the
  field mappings and save. Altium maps `Library Ref`, `Library Path`,
  `Footprint Ref` and `Footprint Path` by name, and every other column
  becomes a parameter.
* **Symbol not found when placing:** The name in `[symbols]` must match the
  SchLib exactly. The SchLib must also be in the `library` folder or a
  subfolder, because the DbLib search path covers `library` and its
  subfolders.
* **A Custom part shows "(not in current JLCPCB data)":** The part is out of
  stock, discontinued, or extended while `source.kind = "basic"`. Its last
  known details are kept.

## Development

```bash
python -m unittest discover -s tests -v
```

## Credits

* Parts data: [yaqwsx/jlcparts](https://github.com/yaqwsx/jlcparts) and
  [CDFER/jlcpcb-parts-database](https://github.com/CDFER/jlcpcb-parts-database).
* Inspiration: [Bouni/kicad-jlcpcb-tools](https://github.com/Bouni/kicad-jlcpcb-tools)
  and [gsuberland/altium_jlcpcb_libraries](https://github.com/gsuberland/altium_jlcpcb_libraries).
* Part models: [uPesy/easyeda2kicad.py](https://github.com/uPesy/easyeda2kicad.py).
* Rotation list: [matthewlai/JLCKicadTools](https://github.com/matthewlai/JLCKicadTools).
