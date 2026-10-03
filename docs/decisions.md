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

## 2026-10-03: Pitch origin, direction and match_id format (proposed, see schema.md)

- Origin at the bottom-left corner (SPADL), not the centre, so events and tracking share one
  frame without conversion.
- Events: acting team attacks left to right (SPADL). Tracking: home team attacks left to right
  in every period, because a frame has no single acting team.
- `match_id = <date>_<home team_id>_<away team_id>`: readable, and every provider produces the
  same id once its teams are in team_crosswalk. If two providers disagree on the date
  (time zones), match_crosswalk overrides.
