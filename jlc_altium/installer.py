"""`setup`: everything a new user needs, in one command.

1. Installs the 64-bit SQLite3 ODBC driver if it is missing (Windows).
2. Downloads the parts data and builds the database + DbLib.
3. Writes the one-time Altium script that creates the symbol and footprint
   libraries and installs everything in Altium.
4. Registers the daily update task (Windows).

Each step checks whether it is already done, so setup can be re-run any time.
"""

from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from pathlib import Path

from . import altium_script, download
from .config import REPO_ROOT, Config

ODBC_DRIVER_KEY = r"SOFTWARE\ODBC\ODBCINST.INI\SQLite3 ODBC Driver"
IS_WINDOWS = sys.platform == "win32"


def step(n: int, total: int, text: str) -> None:
    print(f"\n[{n}/{total}] {text}")


def odbc_driver_installed() -> bool:
    import winreg
    try:
        winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, ODBC_DRIVER_KEY, 0,
                       winreg.KEY_READ | winreg.KEY_WOW64_64KEY).Close()
        return True
    except OSError:
        return False


def _run_elevated(exe: Path, args: str) -> None:
    """Run exe as administrator (UAC prompt) and wait for it."""
    quoted = str(exe).replace("'", "''")
    ps = f"Start-Process -FilePath '{quoted}' -ArgumentList '{args}' -Verb RunAs -Wait"
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)


def ensure_odbc_driver(cfg: Config, assume_yes: bool) -> bool:
    if odbc_driver_installed():
        print("  SQLite3 ODBC Driver (64-bit) is installed.")
        return True
    s = cfg.section("setup")
    url = s.get("odbc_url", "")
    page = s.get("odbc_page", "http://www.ch-werner.de/sqliteodbc/")
    print("  The 64-bit SQLite3 ODBC Driver is not installed; Altium needs it to read the database.")
    if not assume_yes and input("  Download and install it now? [Y/n] ").strip().lower() in ("n", "no"):
        return False

    installer = cfg.cache_dir / Path(url).name if url else None
    try:
        if not installer:
            raise OSError("no download URL configured")
        download.fetch(url, installer)
        print("  Running the installer; approve the Windows administrator prompt.")
        _run_elevated(installer, "/S")
    except (OSError, subprocess.CalledProcessError) as e:
        # Only ever fetch the installer over HTTPS. If that is not possible,
        # hand over to the user rather than run an unverified download as admin.
        print(f"  Automatic install did not work ({e}).")
        print(f"  Opening {page} - download and run sqliteodbc_w64.exe (the 64-bit one).")
        webbrowser.open(page)
        input("  Press Enter once it is installed... ")

    if odbc_driver_installed():
        print("  SQLite3 ODBC Driver installed.")
        return True
    print("  Still not found. Install it from the page above, then run setup again.")
    return False


def register_task(cfg: Config) -> bool:
    at = cfg.section("setup").get("update_time", "07:45")
    script = REPO_ROOT / "scripts" / "install-scheduled-task.ps1"
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-File", str(script), "-At", at, "-Python", sys.executable])
    return r.returncode == 0


def run(cfg: Config, args, update) -> int:
    """update: callable that performs `update` (from the CLI module)."""
    total = 4
    problems = []

    step(1, total, "SQLite ODBC driver")
    if not IS_WINDOWS:
        print("  Skipped (not Windows).")
    elif not ensure_odbc_driver(cfg, args.yes):
        problems.append("SQLite3 ODBC Driver (64-bit) is not installed")

    step(2, total, "Parts database")
    update(cfg, args)

    step(3, total, "Altium setup script")
    prj = altium_script.write(cfg)
    print(f"  Wrote {prj}")

    step(4, total, "Daily automatic update")
    if not IS_WINDOWS:
        print("  Skipped (not Windows). Schedule `python -m jlc_altium update` with cron instead.")
    elif args.no_task:
        print("  Skipped (--no-task).")
    elif not register_task(cfg):
        problems.append("the daily update task could not be registered")

    print("\n" + "=" * 70)
    if problems:
        print("Setup finished with problems:\n  - " + "\n  - ".join(problems))
    else:
        print("Setup complete.")
    print(f"""
Last step, once, inside Altium Designer:

  1. File > Run Script... > Browse...
  2. Select  {prj}
  3. Pick  JLC_Setup.pas > Setup  and click OK.

That creates the symbol and footprint libraries and installs the JLCPCB
library in the Components panel. After that, the library updates itself.

For one-click JLCPCB files, run JLC_Tools.pas > GenerateJLCPCBFiles from the
same script project (or add it to a toolbar). See README "JLCPCB Tools".
""")
    if IS_WINDOWS and not args.yes and sys.stdin.isatty():
        if input("Open the folder with the script now? [Y/n] ").strip().lower() not in ("n", "no"):
            os.startfile(prj.parent)  # noqa: S606 - Windows Explorer
    return 1 if problems else 0
