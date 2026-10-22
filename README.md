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
| 📚 **Native Altium library** | Search and sort in the Components panel by value, package, tolerance or voltage. Ready-made **Basic** lists show only parts with no feeder fee. |
| 🔁 **Refresh placed parts** | *Tools » Update Parameters From Database* updates stock, price and type on parts already in your schematic. |
| 🧩 **Any LCSC part** | `fetch C6186` downloads the part's EasyEDA symbol, footprint and 3D model. After one import into Altium, the part updates daily like the rest. |
| 🔎 **Part search** | `search LDO 3.3V SOT-23 --basic` searches the whole JLCPCB catalogue from the terminal. |
| ✅ **BOM check** | `check` flags out-of-stock, low-stock and Extended parts (which carry a feeder fee). It also suggests Basic parts with the same value and size. |
| 🏭 **One-click JLCPCB files** | The **JLCPCB Tools** script writes JLCPCB's BOM and CPL files straight from your open project, like kicad-jlcpcb-tools' Generate button, with rotation corrections. |
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

Setup takes **two steps**:

1. **Download** this project ([ZIP](https://github.com/rmtech1/altium-designer-jlcpcb-libraries/archive/refs/heads/main.zip) or `git clone`), then **double-click `setup.cmd`**.
2. **In Altium:** *File » Run Script » Browse*, pick `library\Altium\JLC_Setup.PrjScr`, then run **Setup**.

After that, the library updates itself every day. 🎉

## 📦 Installation

### What you need

- **Windows** with **Altium Designer** (any version with Database Library support; the 64-bit releases from AD18 onward).
- That's it. Setup installs the rest (Python and the SQLite ODBC driver) for you if it's missing.
- *Optional:* [Git for Windows](https://git-scm.com/download/win), to download with `git clone` and update with `git pull`. Without Git, use the ZIP.

### Step 1: Download

Choose a **permanent folder**, such as `C:\Altium\`. The daily update and Altium will point at it.

**Option A: ZIP (no Git needed)**

1. Click **Code » Download ZIP** on the [repository page](https://github.com/rmtech1/altium-designer-jlcpcb-libraries), or use [this direct link](https://github.com/rmtech1/altium-designer-jlcpcb-libraries/archive/refs/heads/main.zip).
2. Right-click the ZIP, choose **Extract All…**, and extract it to your folder. The extracted folder is named `altium-designer-jlcpcb-libraries-main`; you can rename it.

**Option B: Git**

```bat
cd C:\Altium
git clone https://github.com/rmtech1/altium-designer-jlcpcb-libraries
```

### Step 2: Run `setup.cmd`

Double-click **`setup.cmd`** in the project folder. Setup goes through these
steps, skipping any that are already done:

| | What setup does |
|---|---|
| 🐍 | Checks for Python 3.11+. If it's missing, offers to install it with `winget`. Afterwards, double-click `setup.cmd` again. |
| 🔌 | Installs the **64-bit SQLite3 ODBC driver** that Altium uses to read the database. Approve the Windows administrator prompt. |
| 📥 | Downloads today's JLCPCB parts data and builds `library\JLCPCB.sqlite` and `library\JLCPCB.DbLib`. |
| 📝 | Writes the one-time Altium script `library\Altium\JLC_Setup.PrjScr` with your folder paths filled in. |
| ⏰ | Registers a **daily update task** in Windows Task Scheduler, at 07:45 by default. |

You can run `setup.cmd` again at any time, for example after moving the
folder. It only redoes what's needed.

> If the driver can't be downloaded automatically, setup opens the
> [driver page](http://www.ch-werner.de/sqliteodbc/). Install
> `sqliteodbc_w64.exe` from there and press Enter in the setup window.

### Step 3: Run the setup script in Altium (once)

1. In Altium Designer: **File » Run Script… » Browse…**
2. Select `library\Altium\JLC_Setup.PrjScr`.
3. Choose **`JLC_Setup.pas` » `Setup`**, then click **OK**.

The script:

- Creates `library\Symbols\JLC_Generic.SchLib` with the `Resistor`, `Capacitor`, `Inductor` and `Ferrite Bead` symbols.
- Creates `library\Footprints\JLC_Generic.PcbLib` with `RES-`, `CAP-`, `IND-` and `FB-` footprints for sizes **0201, 0402, 0603, 0805, 1206 and 1210**.
- **Installs** the JLCPCB DbLib and the footprint library in the Components panel.
- Shows a summary of what it did.

It never overwrites library files that already exist, so your own edits are
safe.

🎉 **Done.** Open the **Components** panel, pick **JLCPCB**, and start placing parts.

> 📐 The generated footprints use IPC-7351 nominal land sizes. Review them
> against your own standards. Parts in other sizes (01005, 1812, 2010, 2512…)
> need a footprint of that name in any installed PcbLib.

### Updating the tool itself

- **Git:** run `git pull` in the project folder.
- **ZIP:** download the new ZIP and extract it over the old folder. The ZIP's
  empty `overrides/parts.csv` overwrites yours, so back it up first.

Then double-click `setup.cmd` again.

<details>
<summary><b>Manual setup</b> (if you'd rather not use <code>setup.cmd</code> or the Altium script)</summary>

1. Install [Python 3.11+](https://www.python.org/downloads/) (tick *Add python.exe to PATH*) and the 64-bit [SQLite3 ODBC Driver](http://www.ch-werner.de/sqliteodbc/) (`sqliteodbc_w64.exe`).
2. Run `python -m jlc_altium update` in the project folder.
3. Create `library\Symbols\JLC_Generic.SchLib` with symbols named `Resistor`, `Capacitor`, `Inductor` and `Ferrite Bead`. You can import `library\Symbols\JLC_Generic.kicad_sym` with *File » Import Wizard » KiCad*, or copy symbols from *Miscellaneous Devices.IntLib*.
4. Make footprints named `RES-0603`, `CAP-0402` and so on in any installed PcbLib. *Tools » IPC Compliant Footprints Batch Generator* helps here, and gsuberland's footprints already use these names.
5. Install `library\JLCPCB.DbLib`: in the Components panel, go to *⋮ » File-based Libraries Preferences » Installed » Install*.
6. Schedule the daily update: `powershell -ExecutionPolicy Bypass -File scripts\install-scheduled-task.ps1` (add `-At 09:00` to change the time, or `-Remove` to delete the task).

</details>

## 🛠 Usage

### Placing passives

In the **Components** panel, open the library list and pick a JLCPCB
library:

- **JLCPCB.DbLib - Resistors**, **Capacitors**, **Inductors**, **Ferrite
  Beads**: every part, with Basic parts listed first.
- **… - Basic** versions of each: Basic and Preferred parts only, so there's
  no feeder fee.
- **Custom**: the parts you added with `fetch` or `link`.

Type in the search box to narrow the list (e.g. `10k 0603`), or click a
column header to sort by it.

> ℹ️ The filter pane with checkboxes only appears for Altium 365 cloud
> Workspace libraries. File-based libraries like this one get the search box
> and sortable columns, which is why the Basic lists are built in.

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

### JLCPCB Tools: one-click files from inside Altium

Setup also creates a **JLCPCB Tools** script, `library\Altium\JLC_Tools.pas`,
in the same script project as the setup script. With your PCB project open
and focused, go to *File » Run Script…* and run one of these:

| Procedure | What it does |
|---|---|
| **`GenerateJLCPCBFiles`** | Reads every component from the PCB (position, rotation, side, footprint) and its LCSC code from the schematic. Writes `<Project>_JLCPCB_BOM.csv` and `<Project>_JLCPCB_CPL.csv` to `Project Outputs\JLCPCB\`, then shows a summary. |
| **`CheckJLCPCBStock`** | Asks how many boards you're ordering, then checks every part's stock and Basic/Extended status. It suggests Basic alternatives for Extended passives. |
| **`UpdateJLCPCBDatabase`** | Downloads today's data now, without waiting for the daily task. |

Some details:

- **LCSC codes:** Parts placed from the JLCPCB library already have their
  `LCSC` parameter. For any other part, add a parameter named `LCSC` with
  its code, such as `C6186`. Parts without one (mounting holes, test points,
  DNP parts) are left out and listed.
- **Placement position:** each part's position is the centre of its pads,
  which is how JLCPCB places parts.
- **Gerbers:** make them as usual with your OutJob or *File » Fabrication
  Outputs*. JLCPCB Tools covers the assembly files.

> 💡 **Make it a button:** right-click a toolbar, choose *Customize…* and
> add a new command whose process is `ScriptingSystem:RunScript` with the
> parameters
> `ProjectName=<full path to>\JLC_Setup.PrjScr|ProcName=JLC_Tools.pas>GenerateJLCPCBFiles`.
> Then it really is one click.

### Generating JLCPCB files from exported outputs (alternative)

If you'd rather work from Altium's own outputs:

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
| `setup [--yes] [--no-task]` | First-time setup, run by `setup.cmd`: ODBC driver, database, Altium script, daily task. Safe to re-run. |
| `update` | Downloads the latest data if it changed and rebuilds the database. Flags: `--source basic\|full\|file`, `--offline`, `--rebuild`, `--write-dblib` |
| `status` | Shows when the database was built and the part count per table |
| `search TERMS… [--basic] [--limit N]` | Searches the JLCPCB catalogue |
| `fetch LCSC…` | Downloads the EasyEDA symbol, footprint and 3D model, and links the part |
| `link LCSC SYMBOL FOOTPRINT` | Links a part to an existing symbol and footprint (`--symbol-lib`, `--footprint-lib`, `--comment`) |
| `check BOM.csv [--boards N]` | Checks stock and Basic status for a BOM |
| `fab BOM.csv [PNP.csv] [--out DIR]` | Writes JLCPCB BOM and CPL files |
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
| `setup.update_time` | `07:45` | Time of the daily update task. Run `setup.cmd` again after changing it. |
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
<summary><b>Why can't I filter with checkboxes like in my Workspace libraries?</b></summary>

In current Altium versions, the Components panel's filter pane only works on
Altium 365 cloud Workspace libraries. File-based libraries, including
database libraries like this one, only get the search box and sortable
columns. That's normal.

To make up for it, every family also comes as a **Basic** list. Uploading
the parts into your Workspace would add filtering, but they would then stop
updating automatically.
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
| *"Data source name not found"* when opening the DbLib | The 64-bit SQLite3 ODBC driver is missing. Run `setup.cmd` again, or check *ODBC Data Sources (64-bit) » Drivers*. |
| The Altium setup script stops with an error | Send the error message in an [issue](https://github.com/rmtech1/altium-designer-jlcpcb-libraries/issues) with your Altium version. Meanwhile, finish with the *Manual setup* steps; the database and daily update from `setup.cmd` still work. |
| `setup.cmd` says Python was not found right after installing it | Close the window and double-click `setup.cmd` again so it picks up the new PATH. |
| Tables or parameters look wrong | Run `update --write-dblib`, open the DbLib in Altium, check the field mappings, and save. |
| *Symbol not found* when placing | The names in `[symbols]` must match the SchLib exactly. The SchLib must be in `library\` or a subfolder. |
| Footprint missing on PCB | Make sure a PcbLib containing e.g. `RES-0603` is installed or in the project. |
| Custom part shows *"(not in current JLCPCB data)"* | The part is out of stock, discontinued, or Extended while `source.kind = "basic"`. Its last known details are kept. |
| Scheduled task doesn't run | Check `library\update.log`, and make sure `python` is on PATH for your user. |

## 🗺 Roadmap

- [ ] Prebuilt nightly database as a GitHub release (no 1 GB download)
- [x] In-Altium scripts: one-click JLCPCB files, stock check, database update
- [ ] In-Altium part picker: search JLCPCB and assign an LCSC code to the selected component
- [x] Generated footprints for standard chip sizes (0201–1210)
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
