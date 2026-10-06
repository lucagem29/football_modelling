# Unified schema

All tables are Parquet under `data/processed/<table>/source=<source>/`, one file per match
(`<source match id>.parquet`), crosswalks under `data/crosswalk/`. DuckDB views in `src/football_modelling/db.py` read them with
`hive_partitioning = true`, so the `source` column (and `match_id` for tracking) comes from the
folder name, not from inside the file.

## Rules for every table

- **Pitch**: meters, 105 x 68, origin (0, 0) at the bottom-left corner, x along the length,
  y up. Providers with other pitch sizes are scaled to 105 x 68.
- **Direction**:
  - events and freeze frames: the team doing the action attacks left to right (SPADL rule);
  - tracking: the home team attacks left to right in every period.
- **Time**: `time_s` = seconds since the start of the period. `period`: 1, 2 regular time,
  3, 4 extra time, 5 penalty shootout.
- **IDs**: `match_id`, `team_id` and `player_id` are our own ids. Every row also keeps
  `source` and the provider's own id (`source_id` for the row itself, `source_match_id`,
  `source_team_id`, `source_player_id` for references).
  - `team_id`: lowercase slug, e.g. `germany`, `bayer-leverkusen`; women's sides end in `-w`.
  - `match_id`: `<YYYY-MM-DD>_<home team_id>_<away team_id>` (local kick-off date). The
    same match gets the same id from every provider once its teams are in team_crosswalk.
  - `player_id`: assigned in player_crosswalk (task 07); null until the player is mapped.
- **Provider-specific columns**: prefixed with a short source tag (`sb_`, `pff_`, `wy_`,
  `imp_`, `idsse_`, `sc_`, `met_`). Views combine partitions with `union_by_name = true`.

## Core tables

### matches
| column | type | notes |
|---|---|---|
| match_id | string | |
| source_match_id | string | |
| competition | string | e.g. `FIFA World Cup` |
| season | string | e.g. `2022`, `2023/24` |
| date | date | local kick-off date |
| kickoff_utc | timestamp | null if unknown |
| home_team_id, away_team_id | string | |
| source_home_team_id, source_away_team_id | string | |
| home_score, away_score | int16 | after extra time, without shootout |
| home_shootout, away_shootout | int16 | null if no shootout |
| stage | string | group, round of 16, final, ... |
| venue | string | |
| has_events, has_tracking, has_freeze_frames | bool | |

StatsBomb extra columns: `sb_kick_off` (raw, no time zone, so `kickoff_utc` stays null),
`sb_competition_id`, `sb_season_id`, `sb_match_week`, `sb_referee`, `sb_has_360`.
Shootout scores are counted from the period-5 penalties in the events.

### events (SPADL + provider columns)
| column | type | notes |
|---|---|---|
| match_id | string | |
| source_id | string | provider event id |
| action_idx | int32 | order within the match |
| period | int8 | |
| time_s | float64 | |
| team_id, source_team_id | string | |
| player_id, source_player_id | string | |
| start_x, start_y, end_x, end_y | float32 | meters |
| type_name | string | SPADL action type (pass, shot, tackle, ...) |
| result_name | string | success, fail, offside, owngoal, ... |
| bodypart_name | string | foot, head, other, ... |
| `<tag>_*` | any | provider-specific (e.g. `sb_xg`, `pff_pressure_type`) |

StatsBomb columns: `sb_type` (original event type), `sb_possession`, `sb_play_pattern`,
`sb_position`, `sb_under_pressure`, `sb_counterpress`, `sb_xg`, `sb_extra` (the full
type-specific block as JSON, nothing dropped), `sb_visible_area_360` (polygon as JSON).
Actions socceraction adds itself (dribbles = carries between events) have no `sb_` values.

### freeze_frames
Positions of players around one event (StatsBomb shot freeze frames and 360 frames).
| column | type | notes |
|---|---|---|
| match_id | string | |
| event_source_id | string | the event this frame belongs to |
| frame_type | string | `shot` or `360` |
| player_id, source_player_id | string | null when the provider gives no identity |
| teammate | bool | relative to the acting player |
| actor | bool | the acting player |
| keeper | bool | |
| x, y | float32 | meters, same direction as the event |

StatsBomb shot frames leave out the shooter; we add the shooter as the `actor` row at the shot
location so every frame is complete. 360 frames are anonymous (`source_player_id` null).

### tracking (one Parquet file per match)

PFF: smoothed player positions, raw ball (see decisions.md); `pff_visibility`,
`pff_confidence`, and the PFF event ids each frame belongs to (`pff_game_event_id`,
`pff_possession_event_id`). No tracking during penalty shootouts.
Path: `data/processed/tracking/source=<source>/match_id=<match_id>/part-0.parquet`.
Long format: one row per object per frame.
| column | type | notes |
|---|---|---|
| frame | int32 | provider frame number |
| period | int8 | |
| time_s | float64 | |
| object_id | string | `player_id`, or `ball` |
| source_player_id | string | null for the ball |
| team_id | string | null for the ball |
| jersey | int16 | |
| x, y | float32 | meters, home team attacks left to right |
| z | float32 | ball height, null for players |
| speed | float32 | m/s, null if not provided |
| ball_owning_team_id | string | null if unknown |
| ball_in_play | bool | null if unknown |
| `<tag>_*` | any | e.g. `pff_visibility`, `pff_confidence` |

### lineups
| column | type | notes |
|---|---|---|
| match_id | string | |
| team_id, source_team_id | string | |
| player_id, source_player_id | string | |
| jersey | int16 | |
| position | string | provider position, as given |
| position_group | string | GK, DEF, MID, FWD |
| started | bool | |
| minutes_played | float32 | null if unknown |

StatsBomb extra columns: `sb_positions` (every position played, with times, JSON), `sb_cards`.
Unused substitutes have no position.

### players
| column | type | notes |
|---|---|---|
| source_player_id | string | one row per provider player |
| player_id | string | from player_crosswalk |
| name, nickname | string | |
| birth_date | date | |
| height_cm | float32 | |
| nationality | string | |

### teams
| column | type | notes |
|---|---|---|
| source_team_id | string | one row per provider team |
| team_id | string | from team_crosswalk |
| name | string | |
| country | string | |
| team_type | string | `club` or `national` |
| gender | string | `m` or `w` |

### context
Three tables under `data/processed/context/`.

`context/results` (international results, football-data.co.uk results):
match_id (string, null if not mapped), date (date), home_team_name, away_team_name (string),
home_team_id, away_team_id (string, null if not mapped), home_score, away_score (int16),
competition (string), neutral (bool), city, country (string).

`context/odds` (football-data.co.uk): match_id, date, home_team_id, away_team_id,
bookmaker (string), market (string, e.g. `1x2`, `ou2.5`), outcome (string),
odds (float32), closing (bool).

`context/elo` (Club Elo): team_id (string), source_team_name (string), date_from, date_to (date),
elo (float32), rank (int32), country (string), level (int8).

### PFF columns
- events: `pff_game_event_id`, `pff_possession_event_id`, `pff_game_event_type`,
  `pff_event_type` (PA pass, CR cross, SH shot, CL clearance, BC carry, CH challenge, ...),
  `pff_setpiece_type`, `pff_frame` (tracking frame of the event), `pff_video_time_s`,
  `pff_attacking_direction`, `pff_extra` (all PFF event blocks as JSON). Event types with no
  SPADL counterpart are `non_action`. `end_x/end_y` = start of the next event (SPADL rule).
- matches: `kickoff_utc` is filled (PFF gives UTC), `pff_week`, `pff_fps`,
  `pff_home_start_left`, `pff_direction_fixed_periods`, `pff_label_suspect_periods`.
- players: `birth_date`, `height_cm` from PFF's players.csv.

## Crosswalk tables (`data/crosswalk/`)

Crosswalks between two providers are partitioned by `pair=<a>_<b>` instead of `source=`.

All crosswalks keep `method` (how the link was made: `exact_id`, `date_teams`, `name_dob`,
`manual`, ...) and `confidence` (float32, 0 to 1).

### team_crosswalk
team_id (string), source (string), source_team_id (string), source_team_name (string),
method, confidence.

### match_crosswalk
match_id (string), source (string), source_match_id (string), method, confidence.

### player_crosswalk
player_id (string), source (string), source_player_id (string), name (string),
birth_date (date), reep_id (string, null if not in Reep register), method, confidence,
name_similarity (0-1, check on the pairing).

### event_crosswalk
match_id (string), source_a, event_id_a, source_b, event_id_b (string),
time_diff_s (float32, after the per-period clock offset), dist_m (float32),
same_player (bool), method, confidence.
One row per linked pair; an event with no partner has no row.

### sync_quality
match_id, period, n_events, nearest_is_acting_team (share of linked events whose nearest
tracked player belongs to the acting team), actor_gap_median_m (StatsBomb location vs the
tracked position of the event's player), labels_ok (bool). Periods with labels_ok = false
have unreliable player labels in tracking.
