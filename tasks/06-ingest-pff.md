# 06 Ingest PFF FC World Cup 2022

Goal: all 64 PFF matches standardized, events and tracking.

- Raw is already in `data/raw/pff/` (unzipped). Use top-level `Event Data/` (see decisions.md).
- Tracking: stream each `.jsonl.bz2` line by line, map shirt numbers to player ids via Rosters,
  flip coordinates so the home team attacks left to right, write one Parquet file per match.
  Decide raw vs smoothed positions (write both or document the choice).
- Events: to SPADL + `pff_` columns. Match/teams/lineups from Metadata and Rosters.
- Watch memory: one match at a time, check peak RAM on the largest match.
- Done when: smoke test passes for all 64 matches, row counts in docs/data-sources.md.
