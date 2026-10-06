# 02 Ingest context data

Goal: results, odds and Elo available as context tables.

- International results (martj42): results.csv, shootouts.csv, goalscorers.csv.
- football-data.co.uk: one CSV per league and season; script must re-download only the
  current season (updated weekly).
- Elo: Club Elo's API is closed (login only, registration closed). Compute our own Elo instead:
  club Elo from world_results (1888-2025) + football-data.co.uk (current seasons), national-team
  Elo from international results (1872 onwards). One documented formula (K factor, home
  advantage, goal-difference weight), validated against published ratings where available.
  Process chronologically in one pass with a dict of current ratings; output one row per team
  per match (rating before/after), a few hundred MB at most.
- World results, openfootball World Cups: standardize into context/results.
- Write `data/processed/context/{results,odds,elo}/source=<source>/` (elo has source=computed).
- Done when: smoke test passes, row counts in docs/data-sources.md.
