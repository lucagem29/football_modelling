---
name: add-data-source
description: Fixed workflow for adding a new football data source (download, standardize to the unified schema, Parquet, DuckDB views, smoke test, docs). Use whenever a new provider or dataset is ingested, or a task file in tasks/ says "ingest".
---

# Add a data source

Schema, coordinate and ID rules live in `docs/schema.md`. Read it first; do not restate it.
Memory rule: process file by file / match by match, never load the whole source.

1. **Download.** Create `data/raw/<source>/` and `src/football_modelling/ingest/<source>.py`.
   Idempotent: skips files that already exist, never edits raw files. Runnable as
   `uv run python -m football_modelling.ingest.<source>`.
2. **Standardize.** `src/football_modelling/standardize/<source>.py` converts raw to the unified
   schema: meters on 105 x 68, left to right, seconds per period, `source` + `source_id`
   columns, provider columns prefixed with the source tag, tracking one file per match.
   Map teams in `team_crosswalk` first, so `match_id` can be built.
3. **Write Parquet** to `data/processed/<table>/source=<source>/` (skip matches already written).
4. **Register DuckDB views** in `src/football_modelling/db.py` (create it if missing):
   `read_parquet(..., hive_partitioning = true, union_by_name = true)`.
5. **Smoke test** in `tests/test_<source>.py`: row counts > 0 and as expected,
   x in [0, 105], y in [0, 68], no null `match_id`. Skip the test if `data/processed/` for the
   source is missing. Run `uv run pytest` and `uv run ruff check .`.
6. **Docs.** Update `docs/data-sources.md` (status, licence, row counts). Add an entry to
   `docs/decisions.md` for anything non-obvious decided on the way.
