# 05 Ingest Impect

Goal: find out what Impect open data contains, then ingest it.

- Check scope (matches, event types, coordinates) and licence of
  https://github.com/ImpectAPI/open-data. Record findings in docs/data-sources.md.
- Check how many matches overlap with StatsBomb Bundesliga 2023/24 (Leverkusen only).
- Standardize events to the unified schema + `imp_` columns.
- Done when: smoke test passes, overlap with StatsBomb written down.
