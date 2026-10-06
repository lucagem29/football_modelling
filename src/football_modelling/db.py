"""DuckDB query layer: views over the Parquet files, nothing stored in DuckDB itself.

    from football_modelling.db import connect
    con = connect()
    con.sql("select * from events where match_id = '2022-12-18_argentina_france' limit 5")

Every folder under data/processed/ and data/crosswalk/ becomes a view of the same name.
``source`` (and ``match_id`` for tracking) come from the hive-style folder names.
Tables that collect one row per provider entity per match (teams, players) are
de-duplicated in the view.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from football_modelling.paths import CROSSWALK, PROCESSED

DISTINCT_TABLES = {"teams", "players", "team_crosswalk"}


def _glob(folder: Path) -> str | None:
    files = next(folder.rglob("*.parquet"), None)
    if files is None:
        return None
    return (folder / "**" / "*.parquet").as_posix()


def connect(database: str = ":memory:") -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(database)
    con.execute("SET memory_limit = '2GB'")  # the laptop has ~8 GB; leave room for the rest
    for base in (PROCESSED, CROSSWALK):
        if not base.exists():
            continue
        for folder in sorted(p for p in base.iterdir() if p.is_dir()):
            pattern = _glob(folder)
            if pattern is None:
                continue
            select = "SELECT DISTINCT *" if folder.name in DISTINCT_TABLES else "SELECT *"
            con.execute(
                f"CREATE OR REPLACE VIEW {folder.name} AS {select} FROM read_parquet("
                f"'{pattern}', hive_partitioning = true, union_by_name = true)"
            )
    return con


def views(con: duckdb.DuckDBPyConnection) -> list[str]:
    rows = con.execute("SELECT view_name FROM duckdb_views() WHERE NOT internal").fetchall()
    return [r[0] for r in rows]
