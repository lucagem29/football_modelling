# Data sources

Status values: `planned`, `downloaded`, `standardized`, `synced`.
Row counts are filled in when a source is standardized. Download commands:
`uv run python -m football_modelling.ingest.<module>` (module named per source below).
Each run writes `data/raw/<source>/_manifest_*.json` with the upstream commit/article and
per-file status. Disk size is as stored (large JSON/XML gzip-compressed, see decisions.md).

## Event data

| Source | Module | Scope | Licence | Status | On disk |
|---|---|---|---|---|---|
| StatsBomb Open Data (Hudl) | `statsbomb` | 80 competition-seasons, 4,235 matches, 426 with 360 frames | StatsBomb terms: attribution + logo when publishing | downloaded | 1.6 GB (16 GB raw) |
| Wyscout (Pappalardo et al.) | `wyscout` | ~1,941 matches | CC BY 4.0 | downloaded | 77 MB (zips) |
| Impect | `impect` | Bundesliga 2023/24, all 306 matches | Impect terms (LICENSE.pdf): credit Impect + logo | downloaded | 126 MB (3.2 GB raw) |

**StatsBomb Open Data**: https://github.com/hudl/open-data
- Events, lineups, shot freeze frames. 360 frames (positions of all visible players at each
  event) for many recent competitions: WC 2022, Euro 2020/2024, Bundesliga 2023/24
  (Leverkusen matches only), Ligue 1 21/22 + 22/23, MLS 2023, AFCON 2023, Women's WC 2023,
  Women's Euro 2022/2025.
- Events and 360 frames link via `match_id` and the event uuid.
- Publishing anything built on it requires the StatsBomb attribution and logo.

**Wyscout (Pappalardo et al.)**: https://figshare.com/collections/Soccer_match_event_dataset/4415000
- ~1,941 matches: top-5 leagues 2017/18, WC 2018, Euro 2016. CC BY 4.0.

**Impect**: https://github.com/ImpectAPI/open-data
- Bundesliga 2023/24, 306 matches: events, event KPIs, player KPIs, lineups, matches,
  players, squads, KPI definitions. Logos in `img/` for attribution.
- Each match carries id mappings to DFL (`heim_spiel`) and SkillCorner match ids.

## Tracking data

| Source | Module | Scope | Licence | Status | On disk |
|---|---|---|---|---|---|
| PFF FC WC 2022 | (manual download) | 64 matches, tracking + events | check download terms | downloaded | 8.1 GB incl. zips |
| IDSSE | `idsse` | 7 Bundesliga / 2. Bundesliga matches | CC BY 4.0 | downloaded | 352 MB (2.6 GB raw) |
| SkillCorner | `skillcorner` | 20 A-League 2024/25 matches | MIT | downloaded | 241 MB (1.9 GB raw) |
| Metrica | `metrica` | 3 anonymized matches | no licence stated | downloaded | 175 MB |

**PFF FC World Cup 2022** (local, `data/raw/pff/`)
- All 64 matches. Original zips kept next to the unzipped folders.
- `Event Data/<gameId>.json`: one JSON list per match. Three versions ship in the download:
  top-level (newest, spec v2.5), `May 1, 2025/`, `March 14, 2025/`. Use the top-level version
  (see decisions.md).
- `Tracking Data/<gameId>.jsonl.bz2`: one frame per line, 29.97 fps, players identified by
  shirt number, raw and smoothed positions, ball. Read line by line.
- `Metadata/<gameId>.json`: teams, date, stadium, pitch, period start/end, `homeTeamStartLeft`.
- `Rosters/<gameId>.json`: player id, shirt number, position, team, started.
- `players.csv`, `competitions.csv`, spec PDFs, `PFF FC Change Log.docx`.

**IDSSE**: https://github.com/spoho-datascience/idsse-data, files from figshare article 28196177.
Per match: DFL match information, raw events, raw observed positions (XML). CC BY 4.0.

**SkillCorner**: https://github.com/SkillCorner/opendata. 20 A-League 2024/25 matches (the
catalog grew from 10). Per match: match.json, extrapolated tracking (JSONL, Git LFS upstream),
dynamic events and phases of play (CSV).

**Metrica**: https://github.com/metrica-sports/sample-data. 3 anonymized matches.

## Identity and player data

| Source | Module | Scope | Licence | Status | On disk |
|---|---|---|---|---|---|
| Reep Register | `reep` | 444,707 people, 45,337 teams, competitions, seasons; ids of 40+ providers anchored on Wikidata | CC0 | downloaded | 27 MB (141 MB raw) |
| Transfermarkt datasets (dcaribou) | `transfermarkt` | players, clubs, games, appearances, lineups, game events, valuations, transfers | CC0 | downloaded | 230 MB (zip of csv.gz) |

- Reep has id columns for Wyscout, Impect, SkillCorner, DFL (`key_heimspiel`), Transfermarkt,
  Opta, FBref and more, but **none for StatsBomb or PFF**: those players are linked by name,
  birth date and team in task 07.
- Transfermarkt: upstream stopped refreshing recent data; the published snapshot stays usable.

## Context data

| Source | Module | Scope | Licence | Status |
|---|---|---|---|---|
| International results | `international_results` | all internationals since 1872, incl. WC 2026; shootouts, goalscorers, former names | CC0 | downloaded |
| football-data.co.uk | `football_data` | 22 main divisions 1993/94-2026/27 + 16 extra leagues, results + odds | check site terms | downloaded (68 MB) |
| World results (schochastics) | `world_results` | 1,309,501 results, 207 top-tier leagues + 20 international club tournaments, 1888-2025-09 | ODC-BY (credit schochastics/football-data) | downloaded (16 MB) |
| openfootball World Cups | `openfootball_worldcup` | men's World Cups 1930-2026: rounds, groups, venues, goals; squads for recent tournaments | CC0 | downloaded (3 MB) |
| Club Elo | `clubelo` | club strength over time | check site terms | **not available**: the CSV API moved behind a login and registration is closed (checked 2026-10-06). We compute our own Elo instead (task 02) |

- International results: https://github.com/martj42/international_results
- football-data.co.uk: https://www.football-data.co.uk/data.php
- Club Elo: http://clubelo.com (API at http://api.clubelo.com, login only since 2026-10)
- World results: https://github.com/schochastics/football-data (only `data/results` mirrored)
- openfootball World Cups: https://github.com/openfootball/worldcup.json

## Aggregate data (no events, no tracking)

| Source | Scope | Licence | Status | Rows |
|---|---|---|---|---|
| FIFA WC 2026 Post Tournament Analysis | tournament + team aggregates, 2018/2022/2026 | data (c) FIFA | downloaded | 159 + 238 + 73 + 543 pages |
| FIFA WC 2026 match reports (community) | 104 matches, match/team/player tables | data (c) FIFA; parsed by a community repo | downloaded | 21 CSVs, 16 MB |

FIFA publishes no raw event or tracking data for 2026. Everything here is aggregates FIFA
derived from its optical tracking. Data (c) FIFA; cite the source when publishing.
Local folder: `data/raw/fifa_wc2026/` (README.md there describes every file).

**Post Tournament Analysis** (FIFA Football Performance Insights, PDF, 546 pages, Oct 2026)
- `post_tournament_analysis/tournament_comparison.csv`: 53 metrics x FWC2018/2022/2026,
  transcribed by hand from the chart slides (pages 9-38).
- `team_rankings.csv`: top-16 teams per metric as shown in the charts (not all 48 teams),
  plus the back-three build-up share (page 47, 30 teams). FIFA three-letter team codes.
- `key_findings.csv`: 73 numbered key findings from the thematic chapters, with page.
- `pages_text.jsonl`: text of every page with chapter label.
- Chart values were read from rendered slides: rounded as displayed, stacked totals may differ
  from the sum of parts by 0.1. On page 19 (stacked bar) only the total is sorted; the
  take-on and step-in parts are not. Check the `normalisation` column: some set-play metrics
  are per match, others per team per match.
- Not transcribed: shot/goal location heatmaps (pp. 14-15), goals vs xG scatter (p. 16),
  charts inside the thematic chapters (pp. 39+).
- The PDF (117 MB) is not in the repo (`*.pdf` is gitignored). Rebuild:
  `uv run python -m football_modelling.ingest.fifa_wc2026.post_tournament_analysis <pdf>`
  (needs `pdftotext`). The chart values themselves live in code, in
  `src/football_modelling/ingest/fifa_wc2026/chart_values_part*.py`.

**Match reports (community)**: https://github.com/Alamyy/Worldcup26 (not affiliated with FIFA),
parsed from the 104 FIFA Training Centre post-match reports: matches, teams, players,
appearances, attempts, passing-network edges, physical data, set plays, pressure and more.
Team codes match the FIFA codes in team_rankings.csv. In `team_key_stats.csv`, the 104 rows
for the in-contest share of possession have team `CONTEST` and no `match_team_id`.
- Fetch / refresh: `uv run python -m football_modelling.ingest.fifa_wc2026.match_reports`
  (skips existing files; delete `match_reports_community/` to pull a newer upstream commit).

## Tools

- kloppy (loads most providers into one model): https://github.com/PySport/kloppy
- socceraction (SPADL, VAEP, xT): https://github.com/ML-KULeuven/socceraction
- Reep Register (player / team id register across providers): https://github.com/withqwerty/reep
- DataBallPy (MIT): loads and synchronises event + tracking data, ships the 7 DFL matches.
  Not installed: it pins `pyarrow<23` and `numpy<2.3`, older than ours. Its event-tracking
  sync method is a reference for task 08.
- The overview of open football data that lists most of these sources is
  https://github.com/withqwerty/open-football (same author as the Reep Register).

## What can be linked to what

**Level 1: already linked inside one provider.** StatsBomb, PFF, IDSSE, SkillCorner, Metrica
(events, tracking and lineups of the same provider share ids).

**Level 2: match level, via date + teams.** Any event data with results, Elo and odds.

**Level 3: event level across providers.**
- WC 2022 StatsBomb <-> PFF. Main target: the only cross-provider case with tracking.
- WC 2018 StatsBomb <-> Wyscout (events only).
- Bundesliga 2023/24 StatsBomb <-> Impect (to check: StatsBomb only has Leverkusen matches).

**Not linkable:** IDSSE, SkillCorner, Metrica (no overlap with other providers).

## Checked and not added (2026-10-06)

| Source | Why not |
|---|---|
| SoccerMon (Zenodo, CC BY 4.0) | 99 GB of GPS data from two women's teams; far too large, and training load rather than match positions |
| SoccerNet | video behind an access form (NDA); video models are out of scope |
| Fjelstul World Cup database | CC BY-NC-SA: no commercial use; openfootball + Reep + Transfermarkt cover it |
| European Soccer Database (Kaggle) | needs a Kaggle account; 2008-2016 only, covered by football-data.co.uk and Transfermarkt |
| Alfheim / Tromsø (Simula) | 3 matches from 2013, research use only |
| eloratings.net | no licence stated; national-team Elo is computed from international results instead |
| FiveThirtyEight SPI | offline since the site shut down |
| FBref, Understat, WhoScored | terms forbid scraping and reuse |
| Last Row, Dynasty Scouting League, wosostats | too small or amateur; low value |
| openfootball football.json, footballcsv | duplicates football-data.co.uk with less detail |
