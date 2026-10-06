# Data sources

Status values: `planned`, `downloaded`, `standardized`, `synced`.
Row counts are filled in when a source is standardized.

## Event data

| Source | Scope | Licence | Status | Rows |
|---|---|---|---|---|
| StatsBomb Open Data (Hudl) | 80 seasons | free, attribution + logo required when publishing | planned | |
| Wyscout (Pappalardo et al.) | ~1,941 matches | CC BY 4.0 | planned | |
| Impect | Bundesliga 2023/24 (scope to check) | check | planned | |

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
- Bundesliga 2023/24. Exact scope and licence still to check (task 05).

## Tracking data

| Source | Scope | Licence | Status | Rows |
|---|---|---|---|---|
| PFF FC WC 2022 | 64 matches, tracking + events | check download terms | downloaded | |
| IDSSE | 7 Bundesliga / 2. Bundesliga matches | CC BY 4.0 | planned | |
| SkillCorner | 10 A-League 2024/25 matches | check | planned | |
| Metrica | 3 anonymized matches | check | planned | |

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

**IDSSE**: https://github.com/spoho-datascience/idsse-data. TRACAB tracking + DFL events, CC BY 4.0.

**SkillCorner**: https://github.com/SkillCorner/opendata. 10 A-League 2024/25 matches.

**Metrica**: https://github.com/metrica-sports/sample-data. 3 anonymized matches.

## Context data

| Source | Scope | Status |
|---|---|---|
| International results | all internationals since 1872, incl. WC 2026; shootouts.csv, goalscorers.csv | planned |
| football-data.co.uk | club results + betting odds, updated weekly | planned |
| Club Elo | club strength over time | planned |

- International results: https://github.com/martj42/international_results
- football-data.co.uk: https://www.football-data.co.uk/data.php
- Club Elo: http://clubelo.com (API at http://api.clubelo.com)

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
- Overview of open football data: https://github.com/withqwerty/open-football

## What can be linked to what

**Level 1: already linked inside one provider.** StatsBomb, PFF, IDSSE, SkillCorner, Metrica
(events, tracking and lineups of the same provider share ids).

**Level 2: match level, via date + teams.** Any event data with results, Elo and odds.

**Level 3: event level across providers.**
- WC 2022 StatsBomb <-> PFF. Main target: the only cross-provider case with tracking.
- WC 2018 StatsBomb <-> Wyscout (events only).
- Bundesliga 2023/24 StatsBomb <-> Impect (to check: StatsBomb only has Leverkusen matches).

**Not linkable:** IDSSE, SkillCorner, Metrica (no overlap with other providers).
