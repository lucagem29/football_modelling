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
