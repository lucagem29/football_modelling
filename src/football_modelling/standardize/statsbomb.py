"""Standardize StatsBomb open data to the unified schema (docs/schema.md).

One match at a time: raw JSON (gzip) -> matches, teams, players, lineups, events (SPADL +
``sb_`` columns), freeze_frames (shot freeze frames + 360 frames) and the StatsBomb part of
team_crosswalk / match_crosswalk. Every table gets one Parquet file per match under
``<table>/source=statsbomb/<statsbomb match id>.parquet``; matches already written are skipped.

    uv run python -m football_modelling.standardize.statsbomb                 # everything
    uv run python -m football_modelling.standardize.statsbomb --competition 43 --season 106
    uv run python -m football_modelling.standardize.statsbomb --match 3869685 --overwrite
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import warnings
from pathlib import Path

import pandas as pd
import polars as pl
import socceraction.data.statsbomb.loader as sb_loader
import socceraction.spadl as spadl
from socceraction.data.statsbomb import StatsBombLoader
from tqdm import tqdm

from football_modelling.ids import make_match_id, team_slug
from football_modelling.paths import CROSSWALK, PROCESSED, RAW

SOURCE = "statsbomb"
RAW_SB = RAW / SOURCE
FIELD_LENGTH, FIELD_WIDTH = 105.0, 68.0
# Competitions played by national teams (all others are club competitions)
NATIONAL_COMPETITIONS = {
    "FIFA World Cup",
    "Women's World Cup",
    "UEFA Euro",
    "UEFA Women's Euro",
    "Copa America",
    "African Cup of Nations",
}
TABLES = ("matches", "teams", "players", "lineups", "events", "freeze_frames")


def load_json(path: str | Path):
    """Read a raw StatsBomb JSON file, transparently using the ``.gz`` copy we store."""
    path = str(path)
    gz = path + ".gz"
    if os.path.exists(gz):
        with gzip.open(gz, "rt", encoding="utf-8") as f:
            return json.load(f)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# socceraction's local loader reads every file through this one function
sb_loader._localloadjson = load_json


def to_pitch(loc, fidelity: int) -> tuple[float, float]:
    """StatsBomb 120 x 80 cell coordinates -> meters on 105 x 68, y up.

    Same formula as socceraction.spadl.statsbomb._convert_locations, so freeze frames line
    up exactly with the SPADL actions. StatsBomb locations are already seen from the team
    performing the event, which is the SPADL direction rule.
    """
    half_cell = (0.1 if fidelity == 2 else 1.0) / 2
    x = (loc[0] - half_cell) / 120 * FIELD_LENGTH
    y = FIELD_WIDTH - (loc[1] - half_cell) / 80 * FIELD_WIDTH
    return min(max(x, 0.0), FIELD_LENGTH), min(max(y, 0.0), FIELD_WIDTH)


def position_group(position: str | None) -> str | None:
    if not position:
        return None
    if position == "Goalkeeper":
        return "GK"
    if "Back" in position:
        return "DEF"
    if "Midfield" in position:
        return "MID"
    return "FWD"  # wings, forwards, strikers


def _team(m: dict, side: str, national: bool) -> dict:
    t = m[f"{side}_team"]
    gender = "w" if t[f"{side}_team_gender"] == "female" else "m"
    name = t[f"{side}_team_name"]
    return {
        "source_team_id": str(t[f"{side}_team_id"]),
        "team_id": team_slug(name, gender),
        "name": name,
        "country": (t.get("country") or {}).get("name"),
        "team_type": "national" if national else "club",
        "gender": gender,
    }


def _jsonable(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return json.dumps(value, ensure_ascii=False, default=str)


def standardize_match(m: dict, loader: StatsBombLoader) -> dict[str, pd.DataFrame]:
    """Convert one StatsBomb match (an entry of matches/<comp>/<season>.json)."""
    sb_id = m["match_id"]
    national = m["competition"]["competition_name"] in NATIONAL_COMPETITIONS
    home, away = _team(m, "home", national), _team(m, "away", national)
    match_id = make_match_id(m["match_date"], home["team_id"], away["team_id"])
    team_ids = {t["source_team_id"]: t["team_id"] for t in (home, away)}
    fidelity = int((m.get("metadata") or {}).get("xy_fidelity_version") or 1)
    shot_fidelity = int((m.get("metadata") or {}).get("shot_fidelity_version") or 1)

    # --- events -> SPADL, acting team attacks left to right -----------------------------
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ev = loader.events(sb_id, load_360=True)
        actions = spadl.statsbomb.convert_to_actions(
            ev,
            home_team_id=int(home["source_team_id"]),
            xy_fidelity_version=fidelity,
            shot_fidelity_version=shot_fidelity,
        )
    actions = spadl.play_left_to_right(actions, int(home["source_team_id"]))
    actions = spadl.add_names(actions)

    ev_extra = ev.set_index("event_id")
    sb_cols = pd.DataFrame(
        {
            "sb_type": ev_extra["type_name"],
            "sb_possession": ev_extra["possession"],
            "sb_play_pattern": ev_extra["play_pattern_name"],
            "sb_position": ev_extra["position_name"],
            "sb_under_pressure": ev_extra["under_pressure"].fillna(False).astype(bool),
            "sb_counterpress": ev_extra["counterpress"].fillna(False).astype(bool),
            "sb_xg": ev_extra["extra"].map(
                lambda e: (e.get("shot") or {}).get("statsbomb_xg") if isinstance(e, dict) else None
            ),
            "sb_extra": ev_extra["extra"].map(_jsonable),
            "sb_visible_area_360": ev_extra["visible_area_360"].map(_jsonable),
        }
    )
    events = actions.join(sb_cols, on="original_event_id", how="left")
    events = pd.DataFrame(
        {
            "match_id": match_id,
            "source_id": events["original_event_id"].astype("string"),
            "action_idx": events["action_id"].astype("int32"),
            "period": events["period_id"].astype("int8"),
            "time_s": events["time_seconds"].astype("float64"),
            "team_id": events["team_id"].astype(str).map(team_ids),
            "source_team_id": events["team_id"].astype(str),
            "player_id": pd.Series(None, index=events.index, dtype="string"),
            "source_player_id": events["player_id"].map(
                lambda p: None if pd.isna(p) else str(int(p))
            ),
            "start_x": events["start_x"].astype("float32"),
            "start_y": events["start_y"].astype("float32"),
            "end_x": events["end_x"].astype("float32"),
            "end_y": events["end_y"].astype("float32"),
            "type_name": events["type_name"],
            "result_name": events["result_name"],
            "bodypart_name": events["bodypart_name"],
            **{c: events[c] for c in sb_cols.columns},
        }
    )

    # --- freeze frames: StatsBomb shot freeze frames + 360 frames -----------------------
    frames = []
    for e in ev.itertuples(index=False):
        extra = e.extra if isinstance(e.extra, dict) else {}
        shot_ff = (extra.get("shot") or {}).get("freeze_frame")
        if shot_ff:
            if isinstance(e.location, list):
                x, y = to_pitch(e.location, shot_fidelity)
                frames.append(
                    (e.event_id, "shot", None if pd.isna(e.player_id) else str(int(e.player_id)),
                     True, True, False, x, y)
                )  # fmt: skip
            for p in shot_ff:
                x, y = to_pitch(p["location"], shot_fidelity)
                frames.append(
                    (e.event_id, "shot", str(p["player"]["id"]), p["teammate"], False,
                     p["position"]["name"] == "Goalkeeper", x, y)
                )  # fmt: skip
        if isinstance(e.freeze_frame_360, list):
            for p in e.freeze_frame_360:
                x, y = to_pitch(p["location"], fidelity)
                frames.append(
                    (e.event_id, "360", None, p["teammate"], p["actor"], p["keeper"], x, y)
                )  # fmt: skip
    freeze_frames = pd.DataFrame(
        frames,
        columns=[
            "event_source_id",
            "frame_type",
            "source_player_id",
            "teammate",
            "actor",
            "keeper",
            "x",
            "y",
        ],
    )
    freeze_frames.insert(0, "match_id", match_id)
    freeze_frames.insert(3, "player_id", pd.Series(None, index=freeze_frames.index, dtype="string"))
    freeze_frames[["x", "y"]] = freeze_frames[["x", "y"]].astype("float32")

    # --- lineups and players from the raw lineup file --------------------------------
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        minutes = loader.players(sb_id).set_index("player_id")["minutes_played"]
    lineup_rows, player_rows = [], []
    for team in load_json(RAW_SB / "lineups" / f"{sb_id}.json"):
        tid = str(team["team_id"])
        for p in team["lineup"]:
            positions = p.get("positions") or []
            first = positions[0]["position"] if positions else None
            started = any(pos.get("start_reason") == "Starting XI" for pos in positions)
            lineup_rows.append(
                {
                    "match_id": match_id,
                    "team_id": team_ids[tid],
                    "source_team_id": tid,
                    "player_id": None,
                    "source_player_id": str(p["player_id"]),
                    "jersey": p.get("jersey_number"),
                    "position": first,
                    "position_group": position_group(first),
                    "started": started,
                    "minutes_played": minutes.get(p["player_id"]),
                    "sb_positions": _jsonable(positions),
                    "sb_cards": _jsonable(p.get("cards") or None),
                }
            )
            player_rows.append(
                {
                    "source_player_id": str(p["player_id"]),
                    "player_id": None,
                    "name": p["player_name"],
                    "nickname": p.get("player_nickname"),
                    "birth_date": None,
                    "height_cm": None,
                    "nationality": (p.get("country") or {}).get("name"),
                }
            )
    lineups = pd.DataFrame(lineup_rows)
    players = pd.DataFrame(player_rows)

    # --- match row (shootout score counted from period 5 goals) ----------------------
    so = events[(events["period"] == 5) & (events["type_name"] == "shot_penalty")]
    so_goals = so[so["result_name"] == "success"].groupby("source_team_id").size()
    has_shootout = len(so) > 0
    matches = pd.DataFrame(
        [
            {
                "match_id": match_id,
                "source_match_id": str(sb_id),
                "competition": m["competition"]["competition_name"],
                "season": m["season"]["season_name"],
                "date": pd.Timestamp(m["match_date"]).date(),
                "kickoff_utc": None,
                "home_team_id": home["team_id"],
                "away_team_id": away["team_id"],
                "source_home_team_id": home["source_team_id"],
                "source_away_team_id": away["source_team_id"],
                "home_score": m["home_score"],
                "away_score": m["away_score"],
                "home_shootout": int(so_goals.get(home["source_team_id"], 0))
                if has_shootout
                else None,
                "away_shootout": int(so_goals.get(away["source_team_id"], 0))
                if has_shootout
                else None,
                "stage": (m.get("competition_stage") or {}).get("name"),
                "venue": (m.get("stadium") or {}).get("name"),
                "has_events": True,
                "has_tracking": False,
                "has_freeze_frames": len(freeze_frames) > 0,
                # StatsBomb's kick_off has no time zone, so it is kept raw
                "sb_kick_off": m.get("kick_off"),
                "sb_competition_id": m["competition"]["competition_id"],
                "sb_season_id": m["season"]["season_id"],
                "sb_match_week": m.get("match_week"),
                "sb_referee": (m.get("referee") or {}).get("name"),
                "sb_has_360": m.get("match_status_360") == "available",
            }
        ]
    )
    teams = pd.DataFrame([home, away])
    team_xw = pd.DataFrame(
        {
            "team_id": teams["team_id"],
            "source": SOURCE,
            "source_team_id": teams["source_team_id"],
            "source_team_name": teams["name"],
            "method": "seed",
            "confidence": 1.0,
        }
    )
    match_xw = pd.DataFrame(
        [
            {
                "match_id": match_id,
                "source": SOURCE,
                "source_match_id": str(sb_id),
                "method": "seed",
                "confidence": 1.0,
            }
        ]
    )
    return {
        "matches": matches,
        "teams": teams,
        "players": players,
        "lineups": lineups,
        "events": events,
        "freeze_frames": freeze_frames,
        "team_crosswalk": team_xw,
        "match_crosswalk": match_xw,
    }


SCHEMA_CASTS = {
    "matches": {
        "home_score": pl.Int16,
        "away_score": pl.Int16,
        "home_shootout": pl.Int16,
        "away_shootout": pl.Int16,
        "kickoff_utc": pl.Datetime("us", "UTC"),
    },
    "players": {"player_id": pl.String, "birth_date": pl.Date, "height_cm": pl.Float32},
    "lineups": {"player_id": pl.String, "jersey": pl.Int16, "minutes_played": pl.Float32},
    "events": {"sb_xg": pl.Float32, "sb_possession": pl.Int32},
    "team_crosswalk": {"confidence": pl.Float32},
    "match_crosswalk": {"confidence": pl.Float32},
}


def out_path(table: str, sb_id: int) -> Path:
    base = CROSSWALK if table.endswith("_crosswalk") else PROCESSED
    return base / table / f"source={SOURCE}" / f"{sb_id}.parquet"


def write(tables: dict[str, pd.DataFrame], sb_id: int) -> None:
    for name, df in tables.items():
        frame = pl.from_pandas(df.drop(columns=["source"], errors="ignore"))
        casts = {c: t for c, t in SCHEMA_CASTS.get(name, {}).items() if c in frame.columns}
        frame = frame.cast(casts)
        path = out_path(name, sb_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        frame.write_parquet(tmp)
        os.replace(tmp, path)


def iter_matches(competition: int | None, season: int | None):
    for comp in load_json(RAW_SB / "competitions.json"):
        c, s = comp["competition_id"], comp["season_id"]
        if (competition is None or c == competition) and (season is None or s == season):
            yield from load_json(RAW_SB / "matches" / str(c) / f"{s}.json")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--competition", type=int)
    ap.add_argument("--season", type=int)
    ap.add_argument("--match", type=int, help="only this StatsBomb match id")
    ap.add_argument("--overwrite", action="store_true", help="rewrite matches already done")
    args = ap.parse_args(argv)

    loader = StatsBombLoader(getter="local", root=str(RAW_SB))
    todo = [
        m
        for m in iter_matches(args.competition, args.season)
        if (args.match is None or m["match_id"] == args.match)
        and (args.overwrite or not out_path("events", m["match_id"]).exists())
    ]
    failed = []
    for m in tqdm(todo, desc="statsbomb"):
        try:
            write(standardize_match(m, loader), m["match_id"])
        except Exception as exc:  # noqa: BLE001 - one bad match must not stop the run
            failed.append((m["match_id"], repr(exc)))
    print(f"{len(todo) - len(failed)} matches written, {len(failed)} failed")
    for sb_id, err in failed[:20]:
        print("FAILED", sb_id, err)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
