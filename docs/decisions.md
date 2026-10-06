# Decisions

One entry per non-obvious design decision. Newest at the bottom.
Format: date, decision, why, what it affects.

## 2026-10-03: Use the top-level PFF event files

The PFF download contains three versions of the event data for all 64 matches:
`Event Data/` (zipped 2025-06-03), `Event Data/May 1, 2025/` and `Event Data/March 14, 2025/`.
Checked on matches 3812 and 10517:
- Top-level and May have the same rows. Top-level adds one field,
  `stadiumMetadata.teamAttackingDirection`.
- March has fewer rows per match (1,370 vs 2,010 for 3812) over the same game event ids, and
  lacks `stadiumMetadata` (pitch size, attacking direction) and `sequence`.

Use the top-level files. Keep the dated folders untouched in raw.

## 2026-10-03: pandas capped below 3.0

socceraction 1.5.x requires `pandas>=2.1.1,<3`. Without the cap uv picks pandas 3 and falls
back to socceraction 1.1.1 (2021). Lift the cap when socceraction supports pandas 3.

## 2026-10-03: Pitch origin, direction and match_id format (decided 2026-10-06, see schema.md)

- Origin at the bottom-left corner (SPADL), not the centre, so events and tracking share one
  frame without conversion.
- Events: acting team attacks left to right (SPADL). Tracking: home team attacks left to right
  in every period, because a frame has no single acting team.
- `match_id = <date>_<home team_id>_<away team_id>`: readable, and every provider produces the
  same id once its teams are in team_crosswalk. If two providers disagree on the date
  (time zones), match_crosswalk overrides.

## 2026-10-03: Large raw text files are stored gzip-compressed

The disk has ~20 GB free; the missing sources are ~23.5 GB uncompressed (StatsBomb alone
~16 GB). JSON, JSONL and XML from StatsBomb, Impect, SkillCorner and IDSSE are stored as
`<name>.gz`, compressed while downloading. Integrity checks (git blob sha, LFS sha256,
figshare md5) run on the uncompressed bytes, so the content is byte-identical to upstream.
kloppy, polars and the standard library read `.gz` directly. Small sources (Metrica,
international results, football-data, Club Elo) and Wyscout zips stay as downloaded.
The 64 StatsBomb WC 2022 files that Codex downloaded uncompressed were verified against
upstream and compressed in place.

## 2026-10-03: All download code lives in src/football_modelling/ingest/

Codex's first-batch scripts were written into `data/raw/` (not versioned). They are ported to
one module per source in `ingest/` and the originals kept in `data/raw/_codex/` for reference.
Each run writes `data/raw/<source>/_manifest_<name>.json` (commit or article, per-file status).

## 2026-10-06: FIFA WC 2026 data lives in data/raw/, its scripts in ingest/fifa_wc2026/

The dataset arrived as a folder with CSVs, a JSONL and scripts. Following the repo rules, the
data went to `data/raw/fifa_wc2026/` (never committed) and the scripts became the package
`ingest/fifa_wc2026/`. The shell fetch script was rewritten as a Python module using the
shared GitHub mirror (works from any folder, pins the upstream commit in a manifest). The
hand-transcribed chart values are code, so they are versioned and the CSVs can be rebuilt
from them; the shipped CSVs were checked to be identical to the code output. The chart
value files are excluded from `ruff format` to keep their compact table layout.

## 2026-10-06: Compute our own Elo; Club Elo API closed

Club Elo's CSV API moved behind a login with registration closed (every ratings endpoint
returns 502, `/Fixtures` says "Fixtures API deactivated"; same finding in soccerdata issue #977).
The website only carries ratings from about 2022-09. Instead we compute Elo ourselves from
open results (world_results ODC-BY, football-data.co.uk, international results CC0): full
history, own formula, no licence question. The `clubelo` loader stays for when registration
opens. Storage stays small: 1.3M results are 16 MB; one rating row per team per match.

## 2026-10-06: Schema choices follow common practice

- Pitch 105 x 68 m, origin bottom-left: the SPADL convention used by socceraction, VAEP and xT.
  Tracking providers (TRACAB, PFF, SkillCorner) put the origin at the centre; converting is a
  shift of (+52.5, +34).
- Direction: events per acting team (SPADL); tracking with the home team always attacking left
  to right (kloppy `Orientation.STATIC_HOME_AWAY`).
- IDs: like most multi-provider setups, every row keeps the provider id and crosswalk tables map
  them to one canonical id. There is no shared standard for that canonical id, so we keep the
  readable `<date>_<home>_<away>` key. Reep / Wikidata ids are stored in team_crosswalk and
  player_crosswalk where they exist; they cannot be the key itself because Reep has no
  national teams (no Germany, no Argentina), so WC matches would have no id.
