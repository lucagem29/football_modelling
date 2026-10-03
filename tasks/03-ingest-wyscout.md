# 03 Ingest Wyscout (Pappalardo et al.)

Goal: Wyscout public dataset in raw and standardized.

- Download from figshare to `data/raw/wyscout/` (events, matches, players, teams, competitions).
- Standardize events to SPADL (socceraction has a Wyscout converter) + `wy_` columns.
- Note: Wyscout coordinates are percentages, y axis inverted. Convert to 105 x 68 meters.
- Done when: smoke test passes, row counts in docs/data-sources.md.
