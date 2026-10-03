# football_modelling

Long-term football data foundation, independent of any single project. Collect the major open
football datasets, convert them to one schema, and build crosswalk tables so later projects
(analyses, models, simulation, offline RL, content) query everything from one place.
Modelling style: hand-engineered features, gradient boosting, simulation. No deep learning focus.

## Folder map

```
data/                  never versioned
  raw/<source>/        layer 1: untouched downloads, one folder per source
  processed/<table>/   layer 2: unified Parquet tables, partitioned source=<source>/
  crosswalk/           layer 3: mapping tables across providers
src/football_modelling/
  ingest/<source>.py       download / locate raw files (idempotent)
  standardize/<source>.py  raw -> unified schema -> Parquet
  sync/                    match, player, team and event matching across providers
  db.py                    DuckDB views over the Parquet files
tests/                 smoke tests per source
notebooks/             exploration only, never imported by src/
docs/                  data-sources.md, schema.md, decisions.md
tasks/                 one file per planned step (01-... to 08-...)
```

## How to run

```
uv sync                                   # install / update the env
uv run python -m football_modelling.ingest.<source>
uv run python -m football_modelling.standardize.<source>
uv run pytest                             # smoke tests
uv run ruff check . && uv run ruff format .
uv add <pkg>    /  uv add --dev <pkg>     # never pip install
```

## Hard constraints

- Machine has ~8 GB RAM. Never load a full dataset into memory. Process file by file or
  match by match, write Parquet, free memory, continue. Use polars lazy / DuckDB for queries.
- Never commit data. `data/`, `*.parquet`, `*.duckdb` are gitignored; check `git status`
  before every commit.
- Raw files are never modified. Re-running any script must give the same output and skip work
  that is already done.
- pandas is capped below 3.0 because socceraction 1.5.x requires it.

## Unified schema conventions (full tables in docs/schema.md)

- Coordinates in meters on a 105 x 68 pitch, origin bottom-left corner, attacking left to right.
- Time in seconds since the start of each period; `period` 1-2, 3-4 extra time, 5 shootout.
- Own unified `match_id`; every row also keeps `source` and the provider's `source_id`.
- Events in SPADL (socceraction) plus provider-specific columns prefixed with the source.
- Tracking partitioned per match.
- DuckDB is a query layer (views over Parquet), not storage.

## Conventions

- Code, comments and docstrings in English.
- ruff for lint and format (config in pyproject.toml).
- One loader per source; shared helpers go in the package, not in notebooks.
- Write down non-obvious design decisions in docs/decisions.md (date, decision, why).

## Pointers

- docs/data-sources.md: every source, URL, licence, status, row counts, sync level.
- docs/schema.md: unified tables and crosswalk tables, columns and types, ID rules.
- .claude/skills/add-data-source: the fixed workflow for adding a source.
- docs/decisions.md: design decisions log.
- tasks/: the planned steps, in order.
