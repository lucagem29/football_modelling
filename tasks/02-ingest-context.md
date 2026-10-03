# 02 Ingest context data

Goal: results, odds and Elo available as context tables.

- International results (martj42): results.csv, shootouts.csv, goalscorers.csv.
- football-data.co.uk: one CSV per league and season; script must re-download only the
  current season (updated weekly).
- Club Elo: ratings history per club from the API.
- Write `data/processed/context/{results,odds,elo}/source=<source>/`.
- Done when: smoke test passes, row counts in docs/data-sources.md.
