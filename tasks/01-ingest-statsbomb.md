# 01 Ingest StatsBomb Open Data

Goal: all StatsBomb open data in raw, standardized to the unified schema.

- Download https://github.com/hudl/open-data to `data/raw/statsbomb/` (idempotent; skip files
  already present). Prefer a sparse/shallow clone or the raw files over statsbombpy's API calls.
- Standardize: matches, lineups, players, teams, events (SPADL via socceraction + `sb_` columns),
  freeze_frames (shot freeze frames and 360 frames).
- Process match by match; one Parquet file per match for events and freeze frames.
- Done when: smoke test passes, row counts and status in docs/data-sources.md.
