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

## 2026-10-06: StatsBomb standardization choices

- socceraction's StatsBomb loader is used as is; its one JSON-reading function is wrapped so it
  opens our `.json.gz` files. Match metadata comes from the raw match file, because
  socceraction's games table drops team names.
- `multimethod<2` is pinned: socceraction pins pandera 0.17, which imports a function that
  multimethod 2.0 removed (`ImportError: cannot import name 'overload'`).
- The first provider seeds the canonical `team_id` (slug of its team name); later providers map
  onto it in team_crosswalk. StatsBomb is the seed for WC 2022.
- One Parquet file per match per table, so re-runs skip finished matches and a crash loses at
  most one match. DuckDB reads them all through one glob per table.
- Shot freeze frames get the shooter added as the actor row (StatsBomb leaves it out).

## 2026-10-06: PFF standardization choices and data problems found

- **Own streaming reader, not kloppy.** kloppy's PFF loader holds a whole match in memory
  (~170-255k frames). We read the .jsonl.bz2 line by line and write Parquet in chunks: peak
  memory ~220 MB, ~4 min and ~50 MB per match.
- **Players smoothed, ball raw.** Smoothed player positions sit a median 0.6 m (p90 2.8 m)
  from raw: jitter removed, nothing lost. The smoothed ball is unusable on fast balls: median
  3.6 m, p90 24 m from the raw ball in the final, and missing in 31k frames that have a raw
  ball. PFF's own event positions use the raw ball.
- **Direction from events, not metadata.** Each PFF event says which way the acting team
  attacks; a majority vote per period sets the tracking flip. Metadata flags are only a
  fallback, and disagreements are recorded in `matches.pff_direction_fixed_periods`.
- **Shootout = period 5.** PFF files shootout kicks under period 4; everything after the
  end of extra time moves to period 5. There is no tracking during the shootout; period-5
  event times are seconds since the end of extra time.
- **Scores from scored shots.** PFF has no score field. Own goals are not shots, so the
  StatsBomb comparison is the check for them.
- **Player labels wrong in the final's extra time.** In periods 3-4 of 10517 the positions
  under Argentina's labels are France's players and the other way round (Messi appears as
  "France 10", Lloris as "Argentina 23"). Detected two ways: both goalkeepers on the wrong
  side all period (`matches.pff_label_suspect_periods`), and StatsBomb events landing on the
  wrong team's tracked players (`sync_quality.labels_ok = false`). Not corrected: only shared
  shirt numbers carry over, the rest are paired arbitrarily, so a relabel needs player
  re-identification. A goalkeeper-only fix was tried and removed (it fixed 2 of 22 labels).
- **Unified player_id = `<PFF name slug>_<birth date>`**, set for players linked across
  StatsBomb and PFF; PFF has birth dates, StatsBomb does not.

## 2026-10-06: StatsBomb <-> PFF linking

- Players: paired on (match, team, shirt number); names only confirm (all 50 in the final).
- Events: per period, the clock offset is the median time gap of same-player same-type
  candidates (PFF runs 0.2-1.5 s ahead in the final). Pairs are then chosen one-to-one by
  cost = time gap + 0.1 x distance (m) + 2 if the player differs, within 3 s. Shootouts use a
  different zero point per provider (29.5 s apart in the final), so the offset search widens
  to 90 s when the normal 10 s window finds nothing.
- Every StatsBomb shot in the final is linked; passes 97%; clearances 71% (the providers
  define clearances differently).
