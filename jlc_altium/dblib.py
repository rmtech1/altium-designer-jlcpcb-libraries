"""Writes the Altium .DbLib that connects to the SQLite database over ODBC.

The DbLib only names the connection, the tables and the library search
path. Altium maps columns to symbol/footprint/parameters by name, so the
generated database needs no per-field configuration. Opening the DbLib in
Altium and saving it lets Altium fill in any settings it adds by default.

Requires the 64-bit "SQLite3 ODBC Driver" (http://www.ch-werner.de/sqliteodbc/).
"""

from __future__ import annotations

from pathlib import Path

from .build import CUSTOM_TABLE, TABLES

ODBC_DRIVER = "SQLite3 ODBC Driver"


def connection_string(db: Path) -> str:
    props = f"DRIVER={ODBC_DRIVER};Database={db};LongNames=0;Timeout=10000;NoTXN=0;SyncPragma=NORMAL;StepAPI=0;"
    return f'Provider=MSDASQL.1;Persist Security Info=False;Extended Properties="{props}"'


def render(db: Path, search_path: Path) -> str:
    tables = list(TABLES.values()) + [CUSTOM_TABLE]
    lines = [
        "[OutputDatabaseLinkFile]",
        "Version=1.1",
        "[DatabaseLinks]",
        f"ConnectionString={connection_string(db)}",
        "AddMode=3",
        "RemoveMode=1",
        "UpdateMode=2",
        "ViewMode=0",
        "LeftQuote=[",
        "RightQuote=]",
        "QuoteTableNames=1",
        "UseTableSchemaName=0",
        "DefaultColumnType=VARCHAR(255)",
        "LibraryDatabaseType=",
        "LibraryDatabasePath=",
        "DatabasePathRelative=0",
        "TopPanelCollapsed=0",
        f"LibrarySearchPath={search_path}",
        "OrcadMultiValueDelimiter=,",
        "SearchSubDirectories=1",
        "SchemaName=",
        f"LastFocusedTable={tables[0]}",
    ]
    for i, name in enumerate(tables, 1):
        lines += [
            f"[Table{i}]",
            "SchemaName=",
            f"TableName={name}",
            "Enabled=True",
            "UserWhere=0",
            "UserWhereText=",
        ]
    return "\r\n".join(lines) + "\r\n"


def write(dblib: Path, db: Path) -> None:
    dblib.parent.mkdir(parents=True, exist_ok=True)
    dblib.write_text(render(db.resolve(), dblib.parent.resolve()), encoding="utf-8", newline="")
