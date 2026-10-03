# 04 Ingest small tracking sets (IDSSE, SkillCorner, Metrica)

Goal: the three small tracking sources standardized; test the tracking pipeline before PFF.

- Download each to `data/raw/<source>/`. Load with kloppy where possible.
- Standardize matches, lineups, events where present, tracking (one Parquet file per match).
- Check that the "home team attacks left to right" rule holds in every period.
- Done when: smoke tests pass for all three, row counts in docs/data-sources.md.
