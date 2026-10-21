<div align="center">

# ⚡ Altium Designer JLCPCB Libraries

**A JLCPCB parts library for Altium Designer that keeps itself up to date.**

Live stock, prices and Basic/Extended status in Altium's Components panel, rebuilt every day from JLCPCB's parts list.

[![CI](https://github.com/rmtech1/altium-designer-jlcpcb-libraries/actions/workflows/ci.yml/badge.svg)](https://github.com/rmtech1/altium-designer-jlcpcb-libraries/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Altium Designer](https://img.shields.io/badge/Altium%20Designer-DbLib-A5915F.svg)](https://www.altium.com/documentation/altium-designer/creating-defining-database-library)
[![GitHub stars](https://img.shields.io/github/stars/rmtech1/altium-designer-jlcpcb-libraries?style=social)](https://github.com/rmtech1/altium-designer-jlcpcb-libraries/stargazers)

### ⭐ If this saves you time, please [star the repo](https://github.com/rmtech1/altium-designer-jlcpcb-libraries) and [follow @rmtech1](https://github.com/rmtech1) for updates!

[Quick start](#-quick-start) •
[Features](#-features) •
[Installation](#-installation) •
[Usage](#-usage) •
[Commands](#-command-reference) •
[FAQ](#-faq) •
[Contributing](#-contributing)

</div>

---

## 🤔 Why?

[gsuberland/altium_jlcpcb_libraries](https://github.com/gsuberland/altium_jlcpcb_libraries)
is great, but it ships **static snapshots**. When JLCPCB changes stock,
prices or which parts are Basic, you wait for the next release.

KiCad users have [Bouni/kicad-jlcpcb-tools](https://github.com/Bouni/kicad-jlcpcb-tools),
which pulls a fresh parts database every day. Altium had no equivalent, and
this project fills that gap.

It uses Altium's own **Database Library (DbLib)** feature: Altium reads part
data live from a local SQLite file, and a daily job rebuilds that file from
JLCPCB's latest data. Symbols and footprints rarely change, so they stay
fixed. Stock, price, Basic/Preferred status and new parts are refreshed
daily.

## ✨ Features

| | |
|---|---|
| 🔄 **Daily auto-update** | A Windows scheduled task downloads the latest JLCPCB data. The download is skipped when nothing changed. |
| 📚 **Native Altium library** | Search and filter in the Components panel by value, package, tolerance, voltage, or **Basic / Preferred / Extended**. |
| 🔁 **Refresh placed parts** | *Tools » Update Parameters From Database* updates stock, price and type on parts already in your schematic. |
| 🧩 **Any LCSC part** | `fetch C6186` downloads the part's EasyEDA symbol, footprint and 3D model. After one import into Altium, the part updates daily like the rest. |
| 🔎 **Part search** | `search LDO 3.3V SOT-23 --basic` searches the whole JLCPCB catalogue from the terminal. |
| ✅ **BOM check** | `check` flags out-of-stock, low-stock and Extended parts (which carry a feeder fee). It also suggests Basic parts with the same value and size. |
| 🏭 **JLCPCB assembly files** | `fab` converts Altium's BOM and Pick & Place outputs into JLCPCB's BOM and CPL formats, with rotation corrections. |
| 🔒 **Safe while Altium is open** | Updates swap the database atomically, or write into it in a single transaction if Altium has the file locked. |
| 🪶 **No dependencies** | Pure Python standard library. (`fetch` optionally uses `easyeda2kicad`.) |

## 🧠 How it works

```
 JLCPCB parts list ──daily──► yaqwsx/jlcparts ──► CDFER/jlcpcb-parts-database
                                                       │  CSV 3 MB / SQLite 1 GB, ~06:00 UTC daily
                                                       ▼
 Task Scheduler ─► python -m jlc_altium update ─► library/JLCPCB.sqlite ◄─ ODBC ─ library/JLCPCB.DbLib
                         ▲                          ├─ Resistors                         │
   overrides/parts.csv ──┘                          ├─ Capacitors (MLCC)                 ▼
   (your ICs, connectors…)                          ├─ Inductors              Altium Components panel
                                                    ├─ Ferrite Beads
                                                    └─ Custom
```

- **Generic tables:** Chip resistors, MLCCs, inductors and ferrite beads in
  sizes 01005–2920. Each family uses one generic symbol plus a size-named
  footprint (`RES-0603`, `CAP-0402`, `IND-0805`, `FB-0603`). These are the same
  names gsuberland's libraries use, so existing footprints work.
- **Custom table:** Parts with part-specific pinouts (ICs, diodes,
  transistors, connectors, polarised caps) never get a generic symbol,
  because a wrong pinout is worse than no part. Link each one once with
  `fetch` or `link`. After that it refreshes daily like everything else.
- **Columns in every table:** `Part Number` (the LCSC code, used as the key),
  `LCSC`, `Manufacturer`, `Manufacturer Part Number`, `JLCPCB Type`, `Stock`,
  `Price`, `Price @100`, `Datasheet`, `JLCPCB URL`, `Updated`. Each table
  also has its own value columns, such as Resistance, Tolerance, Voltage
  Rating and Dielectric.

## 🚀 Quick start

```bat
git clone https://github.com/rmtech1/altium-designer-jlcpcb-libraries
cd altium-designer-jlcpcb-libraries
python -m jlc_altium update
powershell -ExecutionPolicy Bypass -File scripts\install-scheduled-task.ps1
```

Next, install `library\JLCPCB.DbLib` in Altium. The full walkthrough is below.

## 📦 Installation

### Requirements

- **Windows** with **Altium Designer** (any version with Database Library support; the 64-bit releases from AD18 onward).
- **Python 3.11 or newer**: [python.org/downloads](https://www.python.org/downloads/). Tick **"Add python.exe to PATH"** during install.
- **SQLite3 ODBC Driver, 64-bit**: [ch-werner.de/sqliteodbc](http://www.ch-werner.de/sqliteodbc/) (`sqliteodbc_w64.exe`). Altium is 64-bit, so the 32-bit driver will not work.
- *Optional:* `pip install easyeda2kicad`, which the `fetch` command needs.

### Step 1: Get the code and build the database

```bat
git clone https://github.com/rmtech1/altium-designer-jlcpcb-libraries
cd altium-designer-jlcpcb-libraries
python -m jlc_altium update
```

This creates:

- `library\JLCPCB.sqlite`: the parts database.
- `library\JLCPCB.DbLib`: the Altium library that connects to it. It holds an absolute path, so it is generated on your machine rather than committed.

### Step 2: Create the generic symbols

Create `library\Symbols\JLC_Generic.SchLib` with four symbols named exactly
**`Resistor`**, **`Capacitor`**, **`Inductor`** and **`Ferrite Bead`**. Pick
one of these ways:

- **Import the ones provided:** In Altium, go to *File » Import Wizard »
  KiCad* and import `library\Symbols\JLC_Generic.kicad_sym`. Save the result
  as `library\Symbols\JLC_Generic.SchLib`.
- **Use your own:** Copy symbols you like (for example from *Miscellaneous
  Devices.IntLib*) into a new SchLib and rename them.

> The names can be changed under `[symbols]` in `config.toml`.

### Step 3: Create the footprints

Any PcbLib that is installed or added to your project needs footprints named
`RES-<size>`, `CAP-<size>`, `IND-<size>` and `FB-<size>`, for example
`RES-0603`.

- *Tools » IPC Compliant Footprints Batch Generator* makes these quickly.
- **0402, 0603 and 0805** cover every Basic passive and most Extended ones.
- If you already use gsuberland's libraries, your footprints already match.

### Step 4: Install the library in Altium

1. Open the **Components** panel, then go to **⋮ » File-based Libraries
   Preferences » Installed » Install** and choose `library\JLCPCB.DbLib`.
2. Open the DbLib once. Confirm the five tables are listed and that
   **Part Number** is the key field, then **save**.

### Step 5: Turn on daily updates

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-scheduled-task.ps1
```

This runs every day at 07:45 by default. Options:

- `-At 09:00` changes the time.
- `-Remove` uninstalls the task.

The log goes to `library\update.log`. To update by hand, double-click
`scripts\update.cmd`.

🎉 **Done.** Your JLCPCB library now refreshes itself every day.

## 🛠 Usage

### Placing passives

In the **Components** panel, choose **JLCPCB** and filter on any column, for
example `JLCPCB Type = Basic`, `Package = 0603`, `Value = 10kΩ`. Basic parts
are listed first.

### Keeping a schematic current

Before ordering, run **Tools » Update Parameters From Database** in your
schematic. It pulls today's stock, price and Basic/Extended status into every
placed part, matched by LCSC code.

### Adding ICs and other parts

```bat
python -m jlc_altium search LDO 3.3V SOT-23 --basic
python -m jlc_altium fetch C6186 C46749
```

`fetch` saves EasyEDA models to `library\Custom\KiCad\`. Import that folder
once with *File » Import Wizard » KiCad*. Save the results as
`library\JLC_Custom.SchLib` and `library\JLC_Custom.PcbLib`, then run
`update`. The parts appear in the **Custom** table.

To use a symbol and footprint you already have, link them instead:

```bat
python -m jlc_altium link C6186 AMS1117-3.3 SOT-223-3 --symbol-lib MyParts.SchLib
```

Links are stored in `overrides/parts.csv`. Commit it to share linked parts
with your team.

### Checking a BOM before ordering

Add an `LCSC` column to your BomDoc and export it as CSV. Then run:

```bat
python -m jlc_altium check Project.csv --boards 10
```

Example output:

```
! C99999     Extended  need   300  stock      200  LOW STOCK  R1,R2
      basic/preferred alternatives: C25804(Basic)
  C6186      Preferred need   150  stock   300000  OK  U1
! C123456              need   150  stock           NOT FOUND (out of stock, discontinued, or not in this data source)  Y1
```

The command exits with code 1 when something needs attention, so you can use
it in scripts.

### Generating JLCPCB assembly files

1. Export the BOM as CSV.
2. Export the Pick & Place file (*File » Assembly Outputs » Generates pick
   and place files*, CSV format, any units).
3. Run:

```bat
python -m jlc_altium fab Project.csv "Pick Place for Project.csv"
```

This writes `Project_JLCPCB_BOM.csv` and `Project_JLCPCB_CPL.csv`, ready to
upload. Parts without an LCSC code are left out and listed.

#### Rotation corrections

Rules live in `rotations.csv`, one `pattern,degrees` per line. A pattern is
either an exact LCSC code (`C6186,180`) or a regex matched against the
footprint name (`^SOT-89,90`). The first matching rule wins.

- Footprints from `fetch` come from EasyEDA, which JLCPCB uses itself, so
  they usually need **no** correction.
- `rotations --download` fetches matthewlai's community list. That list is
  written for **KiCad** footprint names, so review it before use.
- Always check the placement preview on JLCPCB's order page.

## 📖 Command reference

| Command | What it does |
|---|---|
| `update` | Downloads the latest data if it changed and rebuilds the database. Flags: `--source basic\|full\|file`, `--offline`, `--rebuild`, `--write-dblib` |
| `status` | Shows when the database was built and the part count per table |
| `search TERMS… [--basic] [--limit N]` | Searches the JLCPCB catalogue |
| `fetch LCSC…` | Downloads the EasyEDA symbol, footprint and 3D model, and links the part |
| `link LCSC SYMBOL FOOTPRINT` | Links a part to an existing symbol and footprint (`--symbol-lib`, `--footprint-lib`, `--comment`) |
| `check BOM.csv [--boards N]` | Checks stock and Basic status for a BOM |
| `fab BOM.csv PNP.csv [--out DIR]` | Writes JLCPCB BOM and CPL files |
| `rotations [--download]` | Shows or downloads rotation corrections |

Run every command as `python -m jlc_altium <command>`. Add `--help` to any of
them for details.

## ⚙️ Configuration

Settings live in `config.toml`. Copy it to **`config.local.toml`** for
personal changes; git ignores that file, and it takes priority.

| Setting | Default | Meaning |
|---|---|---|
| `source.kind` | `basic` | `basic`: Basic and Preferred parts (3 MB). `full`: every part with 5 or more in stock (about 1 GB, downloaded only when it changes). `file`: your own jlcparts-format SQLite or CSV. |
| `filter.min_stock_extended` | `100` | The minimum stock for an Extended part to be listed. |
| `filter.include_extended` | `true` | Whether Extended passives are listed at all. |
| `[symbols]` | `Resistor`, … | Symbol names in `JLC_Generic.SchLib`. |
| `[footprints]` | `RES`, `CAP`, … | Footprint name prefixes, plus an optional pinned PcbLib. |

> 💡 Use `full` if you want Extended passives, or `check`/`search` coverage of Extended ICs.

## ❓ FAQ

<details>
<summary><b>Does Altium have plugins like KiCad?</b></summary>

Not in the same way. KiCad has an open Python plugin API, so
kicad-jlcpcb-tools can run a whole UI inside the editor. Altium offers:

- **Database Libraries:** components defined by rows in an external
  database. This is the best fit, and it is what this project uses.
- **Scripting (DelphiScript / VBScript / JScript):** fine for small helpers,
  fragile for a full UI.
- **Extensions SDK:** compiled add-ons. Distributing third-party extensions
  is restricted.
- **Manufacturer Part Search / Altium 365:** supplier data from Octopart,
  but it doesn't know JLCPCB's Basic/Extended library or assembly stock.

So the KiCad plugin's jobs are split between native Altium features and a
small command-line tool.
</details>

<details>
<summary><b>Why aren't diodes, transistors and ICs in the generic tables?</b></summary>

Their pinouts depend on the part. For example, SOT-23 pin 1 is the base on
one transistor and the gate on another. A generic symbol would silently
produce wrong boards. Use `fetch` for these, which gives you the
manufacturer-correct EasyEDA model.
</details>

<details>
<summary><b>Can I update while Altium is open?</b></summary>

Yes. If Altium has the database locked, the update writes into it in a single
transaction. Altium sees either the old data or the new data, never a mix.
</details>

<details>
<summary><b>Does this work with Altium 365 / Workspaces?</b></summary>

The DbLib is a file-based library, which works alongside a connected
Workspace. Migrating these parts into managed Workspace components is not
automated (yet). PRs are welcome!
</details>

<details>
<summary><b>Where does the data come from? Is it official?</b></summary>

It comes from JLCPCB's public parts list, collected daily by
[yaqwsx/jlcparts](https://github.com/yaqwsx/jlcparts) and repackaged by
[CDFER/jlcpcb-parts-database](https://github.com/CDFER/jlcpcb-parts-database).
It is a community project and is not affiliated with JLCPCB or Altium.
</details>

## 🩺 Troubleshooting

| Problem | Fix |
|---|---|
| *"Data source name not found"* when opening the DbLib | The 64-bit SQLite3 ODBC driver is missing. Check *ODBC Data Sources (64-bit) » Drivers*. |
| Tables or parameters look wrong | Run `update --write-dblib`, open the DbLib in Altium, check the field mappings, and save. |
| *Symbol not found* when placing | The names in `[symbols]` must match the SchLib exactly. The SchLib must be in `library\` or a subfolder. |
| Footprint missing on PCB | Make sure a PcbLib containing e.g. `RES-0603` is installed or in the project. |
| Custom part shows *"(not in current JLCPCB data)"* | The part is out of stock, discontinued, or Extended while `source.kind = "basic"`. Its last known details are kept. |
| Scheduled task doesn't run | Check `library\update.log`, and make sure `python` is on PATH for your user. |

## 🗺 Roadmap

- [ ] Prebuilt nightly database as a GitHub release (no 1 GB download)
- [ ] In-Altium script to run updates and open the JLCPCB page of a selected part
- [ ] Generated footprints for standard chip sizes
- [ ] More generic families (e.g. chip LEDs with verified polarity)
- [ ] Altium 365 Workspace component export

Have an idea? [Open an issue](https://github.com/rmtech1/altium-designer-jlcpcb-libraries/issues)!

## 🤝 Contributing

**Want to help? I'd love that!** 🙌 Whether it's code, testing on your Altium
version, footprints, docs, or just reporting a bug, please **let me know**:

- 💬 [Open an issue](https://github.com/rmtech1/altium-designer-jlcpcb-libraries/issues) to say hi or propose an idea.
- 🍴 Fork the repo and send a pull request.
- 📖 Read [CONTRIBUTING.md](CONTRIBUTING.md) to get started.

Even just telling me *"it works on AD 24"* or *"it broke on my setup"* helps a lot.

## ⭐ Support the project

If this project helps you ship boards faster:

- ⭐ **[Star this repo](https://github.com/rmtech1/altium-designer-jlcpcb-libraries)** so others can find it.
- 👤 **[Follow @rmtech1](https://github.com/rmtech1)** for updates and new tools.
- 📣 Share it with your team or on your favourite electronics forum.

## 🙏 Credits

- Parts data: [yaqwsx/jlcparts](https://github.com/yaqwsx/jlcparts) and [CDFER/jlcpcb-parts-database](https://github.com/CDFER/jlcpcb-parts-database)
- Inspiration: [Bouni/kicad-jlcpcb-tools](https://github.com/Bouni/kicad-jlcpcb-tools) and [gsuberland/altium_jlcpcb_libraries](https://github.com/gsuberland/altium_jlcpcb_libraries)
- Part models: [uPesy/easyeda2kicad.py](https://github.com/uPesy/easyeda2kicad.py)
- Rotation list: [matthewlai/JLCKicadTools](https://github.com/matthewlai/JLCKicadTools)

## 📄 License

[MIT](LICENSE) © 2026 Roger Mendoza

Data downloaded at runtime is subject to its sources' terms. *JLCPCB*,
*LCSC*, *EasyEDA* and *Altium* are trademarks of their respective owners.
This project is not affiliated with or endorsed by any of them.

<div align="center">

**Made with ☕ for the Altium + JLCPCB community.** If it helped, a ⭐ means a lot!

</div>
