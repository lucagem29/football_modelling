# 01 Ingest StatsBomb Open Data

Goal: all StatsBomb open data in raw, standardized to the unified schema.

- Download https://github.com/hudl/open-data to `data/raw/statsbomb/` (idempotent; skip files
  already present). Prefer a sparse/shallow clone or the raw files over statsbombpy's API calls.
- Standardize: matches, lineups, players, teams, events (SPADL via socceraction + `sb_` columns),
  freeze_frames (shot freeze frames and 360 frames).
- Process match by match; one Parquet file per match for events and freeze frames.
- Done when: smoke test passes, row counts and status in docs/data-sources.md.

## Progress
- 2026-10-06: converter `standardize/statsbomb.py` done; WC 2022 (64 matches) standardized and
  checked (scores, shootouts, direction, freeze-frame alignment); tests in tests/test_statsbomb.py.
- Next: PFF for the same final (task 06), crosswalk + sync on that match, then all 64, then
  the remaining StatsBomb competitions (~2 GB of Parquet expected for all 4,235 matches).
