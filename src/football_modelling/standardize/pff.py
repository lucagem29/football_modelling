"""Standardize PFF FC World Cup 2022 data to the unified schema (docs/schema.md).

Per match: matches, teams, players, lineups, events and tracking, plus the PFF part of
team_crosswalk / match_crosswalk. Tracking is streamed line by line from the .jsonl.bz2 file
and written to Parquet in chunks, so memory stays flat (~200 MB) whatever the match length.

    uv run python -m football_modelling.standardize.pff                  # all 64 matches
    uv run python -m football_modelling.standardize.pff --match 10517    # the final
    uv run python -m football_modelling.standardize.pff --match 10517 --overwrite

Coordinates: PFF uses meters with the origin at the centre spot and y pointing up. Tracking is
shifted to the bottom-left origin and flipped per period so the home team always attacks left
to right (kloppy's STATIC_HOME_AWAY). Events are flipped so the acting team attacks left to
right (SPADL), using PFF's per-event ``teamAttackingDirection``.
PFF files the penalty shootout under period 4; events and frames after the end of extra time
are moved to period 5. Period 5 frames keep the period 4 orientation.
"""

from __future__ import annotations

import argparse
import bz2
import csv
import json
import os
from collections import defaultdict
from pathlib import Path

import pandas as pd
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm

from football_modelling.ids import make_match_id, team_slug
from football_modelling.paths import CROSSWALK, PROCESSED, RAW

SOURCE = "pff"
RAW_PFF = RAW / SOURCE
LENGTH, WIDTH = 105.0, 68.0
CHUNK_FRAMES = 3000  # frames per Parquet row group (~70k rows)

# PFF possession event type -> SPADL type; set pieces refine passes and shots below
TYPE_MAP = {
    "PA": "pass",
    "CR": "cross",
    "SH": "shot",
    "CL": "clearance",
    "BC": "dribble",
    "CH": "tackle",
}
BODY_MAP = {
    "R": "foot_right",
    "RF": "foot_right",
    "L": "foot_left",
    "LF": "foot_left",
    "HE": "head",
}


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --- metadata, teams, players, lineups ------------------------------------------------------


def read_players_csv() -> dict[str, dict]:
    with open(RAW_PFF / "players.csv", encoding="utf-8") as f:
        return {row["id"]: row for row in csv.DictReader(f)}


def home_attacks_right(meta: dict, period: int) -> bool:
    """Which way the home team attacks in a period, from PFF metadata."""
    if period in (1, 2):
        starts_left = bool(meta["homeTeamStartLeft"])
        return starts_left if period == 1 else not starts_left
    starts_left = meta.get("homeTeamStartLeftExtraTime")
    starts_left = bool(meta["homeTeamStartLeft"]) if starts_left is None else bool(starts_left)
    return starts_left if period == 3 else not starts_left  # period 4 and the shootout


def home_direction_from_events(events: list[dict]) -> dict[int, bool]:
    """Per period: does the home team attack right? Majority vote over PFF's per-event
    ``teamAttackingDirection``. Used instead of the metadata flags, which are wrong for
    extra time in some matches (e.g. the final, 10517)."""
    votes: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for e in events:
        ge = e["gameEvents"] or {}
        direction = (e.get("stadiumMetadata") or {}).get("teamAttackingDirection")
        if ge.get("homeTeam") is None or direction not in ("L", "R"):
            continue
        home_right = (direction == "R") == bool(ge["homeTeam"])
        votes[int(ge["period"])][home_right] += 1
    return {p: v[1] > v[0] for p, v in votes.items() if sum(v)}


def to_pitch(x: float, y: float, flip: bool) -> tuple[float, float]:
    """Centre-origin meters -> bottom-left origin, optionally rotated 180 degrees."""
    if flip:
        x, y = -x, -y
    return x + LENGTH / 2, y + WIDTH / 2


def build_meta_tables(game_id: str) -> dict:
    meta = load_json(RAW_PFF / "Metadata" / f"{game_id}.json")
    meta = meta[0] if isinstance(meta, list) else meta
    roster = load_json(RAW_PFF / "Rosters" / f"{game_id}.json")
    people = read_players_csv()

    teams = []
    for side in ("homeTeam", "awayTeam"):
        t = meta[side]
        teams.append(
            {
                "source_team_id": str(t["id"]),
                "team_id": team_slug(t["name"]),
                "name": t["name"],
                "country": t["name"],
                "team_type": "national",
                "gender": "m",
                "pff_short_name": t.get("shortName"),
            }
        )
    home, away = teams
    match_id = make_match_id(meta["date"], home["team_id"], away["team_id"])
    team_ids = {t["source_team_id"]: t["team_id"] for t in teams}

    lineups, players = [], []
    for r in roster:
        pid = str(r["player"]["id"])
        tid = str(r["team"]["id"])
        p = people.get(pid, {})
        lineups.append(
            {
                "match_id": match_id,
                "team_id": team_ids[tid],
                "source_team_id": tid,
                "player_id": None,
                "source_player_id": pid,
                "jersey": int(r["shirtNumber"]),
                "position": r.get("positionGroupType"),
                "position_group": None,
                "started": bool(r.get("started")),
                "minutes_played": None,
            }
        )
        players.append(
            {
                "source_player_id": pid,
                "player_id": None,
                "name": " ".join(x for x in (p.get("firstName"), p.get("lastName")) if x)
                or r["player"].get("nickname"),
                "nickname": r["player"].get("nickname") or p.get("nickname"),
                "birth_date": p.get("dob") or None,
                "height_cm": float(p["height"]) if p.get("height") else None,
                "nationality": None,
            }
        )
    return {
        "meta": meta,
        "match_id": match_id,
        "home": home,
        "away": away,
        "team_ids": team_ids,
        "teams": pd.DataFrame(teams),
        "lineups": pd.DataFrame(lineups),
        "players": pd.DataFrame(players),
    }


# --- tracking (streamed) ----------------------------------------------------------------


TRACKING_SCHEMA = pa.schema(
    [
        ("match_id", pa.string()),
        ("frame", pa.int32()),
        ("period", pa.int8()),
        ("time_s", pa.float64()),
        ("object_id", pa.string()),
        ("source_player_id", pa.string()),
        ("team_id", pa.string()),
        ("jersey", pa.int16()),
        ("x", pa.float32()),
        ("y", pa.float32()),
        ("z", pa.float32()),
        ("speed", pa.float32()),
        ("ball_owning_team_id", pa.string()),
        ("ball_in_play", pa.bool_()),
        ("pff_visibility", pa.string()),
        ("pff_confidence", pa.string()),
        ("pff_game_event_id", pa.int64()),
        ("pff_possession_event_id", pa.int64()),
    ]
)


def tracking_path(match_id: str) -> Path:
    return PROCESSED / "tracking" / f"source={SOURCE}" / f"match_id={match_id}" / "part-0.parquet"


def stream_tracking(
    game_id: str, info: dict, shootout_start: float | None, home_right: dict[int, bool]
) -> dict:
    """Write tracking for one match; return event-id -> (period, time_s, frame) lookups.

    ``shootout_start`` is the video time (s) of the end of extra time; later period-4 frames
    belong to the shootout (period 5). None when there was no shootout.
    """
    meta, match_id, home, away = info["meta"], info["match_id"], info["home"], info["away"]
    by_jersey = defaultdict(dict)  # team side -> jersey -> source player id
    for r in info["lineups"].itertuples():
        side = "home" if r.source_team_id == home["source_team_id"] else "away"
        by_jersey[side][int(r.jersey)] = r.source_player_id
    sides = {"home": home["team_id"], "away": away["team_id"]}
    flips = {p: not home_right.get(p, home_attacks_right(meta, p)) for p in (1, 2, 3, 4)}

    out = tracking_path(match_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    writer = pq.ParquetWriter(tmp, TRACKING_SCHEMA, compression="zstd")
    cols = {name: [] for name in TRACKING_SCHEMA.names}
    event_times: dict[str, dict[int, tuple]] = {"game": {}, "possession": {}}
    n_frames = 0
    unmatched_jerseys: set = set()
    gk_jerseys = {
        side: {int(r.jersey) for r in info["lineups"].itertuples()
               if r.position == "GK" and r.source_team_id == info[side]["source_team_id"]}
        for side in ("home", "away")
    }  # fmt: skip
    gk_x: dict[tuple, list[float]] = defaultdict(lambda: [0.0, 0])  # (period, side, jersey)

    def flush():
        if cols["frame"]:
            writer.write_table(pa.table(cols, schema=TRACKING_SCHEMA))
            for v in cols.values():
                v.clear()

    def add(frame, period, t, obj, pid, team, jersey, x, y, z, speed, vis, conf, gev, pev):
        cols["match_id"].append(match_id)
        cols["frame"].append(frame)
        cols["period"].append(period)
        cols["time_s"].append(t)
        cols["object_id"].append(obj)
        cols["source_player_id"].append(pid)
        cols["team_id"].append(team)
        cols["jersey"].append(jersey)
        cols["x"].append(x)
        cols["y"].append(y)
        cols["z"].append(z)
        cols["speed"].append(speed)
        cols["ball_owning_team_id"].append(None)
        cols["ball_in_play"].append(None)
        cols["pff_visibility"].append(vis)
        cols["pff_confidence"].append(conf)
        cols["pff_game_event_id"].append(gev)
        cols["pff_possession_event_id"].append(pev)

    try:
        with bz2.open(RAW_PFF / "Tracking Data" / f"{game_id}.jsonl.bz2", "rt") as f:
            for line in f:
                fr = json.loads(line)
                period = fr.get("period")
                if period is None:
                    continue
                period = int(period)
                t = float(fr["periodElapsedTime"])
                flip = flips[min(period, 4)]
                video_s = float(fr.get("videoTimeMs") or 0) / 1000
                if period == 4 and shootout_start is not None and video_s > shootout_start:
                    period = 5
                frame = int(fr["frameNum"])
                gev = int(fr["game_event_id"]) if fr.get("game_event_id") is not None else None
                pev = (
                    int(fr["possession_event_id"])
                    if fr.get("possession_event_id") is not None
                    else None
                )
                if gev is not None:
                    event_times["game"].setdefault(gev, (period, t, frame))
                if pev is not None:
                    event_times["possession"].setdefault(pev, (period, t, frame))

                for side in ("home", "away"):
                    raw_speed = {
                        int(p["jerseyNum"]): p.get("speed") for p in fr.get(f"{side}Players") or []
                    }
                    for p in fr.get(f"{side}PlayersSmoothed") or []:
                        if p.get("x") is None:
                            continue
                        jersey = int(p["jerseyNum"])
                        pid = by_jersey[side].get(jersey)
                        if pid is None:
                            unmatched_jerseys.add((side, jersey))
                        x, y = to_pitch(p["x"], p["y"], flip)
                        if jersey in gk_jerseys[side]:
                            acc = gk_x[(period, side, jersey)]
                            acc[0] += x
                            acc[1] += 1
                        add(frame, period, t, pid or f"{side}_{jersey}", pid, sides[side], jersey,
                            x, y, None, raw_speed.get(jersey), p.get("visibility"),
                            p.get("confidence"), gev, pev)  # fmt: skip
                # Raw ball: the smoothed ball lags badly on fast balls (median 3.6 m, p90 24 m
                # off the raw position in the final) and PFF's own event positions use the raw.
                ball = (fr.get("balls") or [None])[0]
                if ball and ball.get("x") is not None:
                    x, y = to_pitch(ball["x"], ball["y"], flip)
                    add(frame, period, t, "ball", None, None, None, x, y, ball.get("z"), None,
                        ball.get("visibility"), None, gev, pev)  # fmt: skip
                n_frames += 1
                if n_frames % CHUNK_FRAMES == 0:
                    flush()
        flush()
    finally:
        writer.close()
    os.replace(tmp, out)
    # Detection only: in the final's extra time the whole team labels are swapped, not just
    # the keepers, so relabelling keepers alone would make things worse. See decisions.md.
    swaps = goalkeeper_swaps(gk_x)
    return {
        "event_times": event_times,
        "n_frames": n_frames,
        "unmatched": unmatched_jerseys,
        "gk_swaps": swaps,
    }


def goalkeeper_swaps(gk_x: dict) -> dict[int, tuple[int, int]]:
    """Periods in which both goalkeepers sit on the wrong side for the whole period.

    After our transform the home team always attacks right, so the home keeper must spend the
    period in the left half and the away keeper in the right half. Both on the wrong side means
    PFF's player labels are wrong in that period (in the final's extra time the two teams'
    labels are swapped). Returns {period: (home GK jersey, away GK jersey)}.
    """
    swaps = {}
    for period in sorted({k[0] for k in gk_x}):
        main = {}
        for side in ("home", "away"):
            cands = [(v[1], k[2], v[0] / v[1]) for k, v in gk_x.items()
                     if k[0] == period and k[1] == side and v[1]]  # fmt: skip
            if cands:
                main[side] = max(cands)  # keeper with the most frames
        if len(main) == 2 and main["home"][2] > LENGTH / 2 and main["away"][2] < LENGTH / 2:
            swaps[period] = (main["home"][1], main["away"][1])
    return swaps


# --- events ----------------------------------------------------------------------------------


def shootout_start_time(events: list[dict]) -> float | None:
    """Video time (s) of the last END event of period 4, if any penalties follow it."""
    ends = [e for e in events if e["gameEvents"]["gameEventType"] == "END"]
    p4_end = [e for e in ends if int(e["gameEvents"]["period"]) == 4]
    if not p4_end:
        return None
    end_t = min(e["startTime"] for e in p4_end)
    after = [
        e
        for e in events
        if int(e["gameEvents"]["period"]) == 4
        and e["startTime"] > end_t
        and (e.get("possessionEvents") or {}).get("possessionEventType") == "SH"
    ]
    return end_t if after else None


def spadl_type(pe_type: str | None, setpiece: str | None, pe: dict) -> str:
    base = TYPE_MAP.get(pe_type or "", "non_action")
    if base == "pass":
        return {"T": "throw_in", "G": "goalkick", "C": "corner_short", "F": "freekick_short"}.get(
            setpiece or "", "pass"
        )
    if base == "cross":
        return {"C": "corner_crossed", "F": "freekick_crossed"}.get(setpiece or "", "cross")
    if base == "shot":
        return {"P": "shot_penalty", "F": "shot_freekick"}.get(setpiece or "", "shot")
    return base


def spadl_result(pe_type: str | None, pe: dict) -> str | None:
    if pe_type in ("PA",):
        return "success" if pe.get("passOutcomeType") == "C" else "fail"
    if pe_type == "CR":
        return "success" if pe.get("crossOutcomeType") == "C" else "fail"
    if pe_type == "SH":
        return "success" if pe.get("shotOutcomeType") == "G" else "fail"
    if pe_type == "BC":
        return "fail" if pe.get("ballCarryOutcome") == "L" else "success"
    if pe_type == "CL":
        return "fail" if pe.get("clearanceOutcomeType") in ("O", "D") else "success"
    return None


def build_events(
    game_id: str, info: dict, raw_events: list[dict], times: dict, so_start
) -> pd.DataFrame:
    match_id, team_ids = info["match_id"], info["team_ids"]
    rows = []
    for e in raw_events:
        ge = e["gameEvents"] or {}
        pe = e.get("possessionEvents") or {}
        period = int(ge["period"])
        if so_start is not None and period == 4 and e["startTime"] > so_start:
            period = 5
        hit = times["possession"].get(e.get("possessionEventId")) or times["game"].get(
            e.get("gameEventId")
        )
        time_s, frame = (hit[1], hit[2]) if hit else (None, None)
        if period == 5:  # no tracking during the shootout: seconds since the end of extra time
            time_s, frame = e["startTime"] - so_start, None
        ball = (e.get("ball") or [None])[0] or {}
        direction = (e.get("stadiumMetadata") or {}).get("teamAttackingDirection")
        team = str(int(ge["teamId"])) if ge.get("teamId") is not None else None
        sx = sy = None
        if ball.get("x") is not None and direction in ("L", "R"):
            sx, sy = to_pitch(ball["x"], ball["y"], flip=direction == "L")
            if period == 5 and sx < LENGTH / 2:  # both teams shoot at one goal in a shootout
                sx, sy = LENGTH - sx, WIDTH - sy
        player = (
            pe.get("passerPlayerId")
            or pe.get("crosserPlayerId")
            or pe.get("shooterPlayerId")
            or pe.get("clearerPlayerId")
            or pe.get("ballCarrierPlayerId")
            or ge.get("playerId")
        )
        rows.append(
            {
                "match_id": match_id,
                "source_id": str(e["possessionEventId"] or e["gameEventId"]),
                "period": period,
                "time_s": time_s,
                "team_id": team_ids.get(team),
                "source_team_id": team,
                "player_id": None,
                "source_player_id": str(int(player)) if player is not None else None,
                "start_x": sx,
                "start_y": sy,
                "end_x": None,
                "end_y": None,
                "type_name": spadl_type(pe.get("possessionEventType"), ge.get("setpieceType"), pe),
                "result_name": spadl_result(pe.get("possessionEventType"), pe),
                "bodypart_name": BODY_MAP.get(pe.get("bodyType"), "other")
                if pe.get("bodyType")
                else None,
                "pff_game_event_id": e.get("gameEventId"),
                "pff_possession_event_id": e.get("possessionEventId"),
                "pff_game_event_type": ge.get("gameEventType"),
                "pff_event_type": pe.get("possessionEventType"),
                "pff_setpiece_type": ge.get("setpieceType"),
                "pff_frame": frame,
                "pff_video_time_s": e.get("startTime"),
                "pff_attacking_direction": direction,
                "pff_extra": json.dumps(
                    {
                        k: e.get(k)
                        for k in (
                            "gameEvents",
                            "initialTouch",
                            "possessionEvents",
                            "fouls",
                            "grades",
                        )
                    },
                    ensure_ascii=False,
                ),
            }
        )
    ev = pd.DataFrame(rows).sort_values(
        ["period", "time_s", "pff_video_time_s"], na_position="last"
    )
    ev.insert(2, "action_idx", range(len(ev)))
    # SPADL convention: an action ends where the next one starts, seen from the acting team
    nxt_x, nxt_y = ev["start_x"].shift(-1), ev["start_y"].shift(-1)
    same_team = ev["source_team_id"].shift(-1) == ev["source_team_id"]
    same_period = ev["period"].shift(-1) == ev["period"]
    ev["end_x"] = nxt_x.where(same_team, LENGTH - nxt_x).where(same_period)
    ev["end_y"] = nxt_y.where(same_team, WIDTH - nxt_y).where(same_period)
    return ev


# --- match ------------------------------------------------------------------------------


def out_path(table: str, game_id: str) -> Path:
    base = CROSSWALK if table.endswith("_crosswalk") else PROCESSED
    return base / table / f"source={SOURCE}" / f"{game_id}.parquet"


CASTS = {
    "matches": {"home_score": pl.Int16, "away_score": pl.Int16, "home_shootout": pl.Int16,
                "away_shootout": pl.Int16, "kickoff_utc": pl.Datetime("us", "UTC")},
    "players": {"player_id": pl.String, "birth_date": pl.Date, "height_cm": pl.Float32},
    "lineups": {"player_id": pl.String, "jersey": pl.Int16, "minutes_played": pl.Float32,
                "position_group": pl.String},
    "events": {"period": pl.Int8, "action_idx": pl.Int32, "time_s": pl.Float64,
               "start_x": pl.Float32, "start_y": pl.Float32, "end_x": pl.Float32,
               "end_y": pl.Float32, "player_id": pl.String, "pff_frame": pl.Int32},
    "team_crosswalk": {"confidence": pl.Float32},
    "match_crosswalk": {"confidence": pl.Float32},
}  # fmt: skip


def write_tables(tables: dict[str, pd.DataFrame], game_id: str) -> None:
    for name, df in tables.items():
        frame = pl.from_pandas(df)
        casts = {c: t for c, t in CASTS.get(name, {}).items() if c in frame.columns}
        if "birth_date" in casts:
            frame = frame.with_columns(pl.col("birth_date").str.to_date(strict=False))
            casts.pop("birth_date")
        frame = frame.cast(casts)
        path = out_path(name, game_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        frame.write_parquet(tmp)
        os.replace(tmp, path)


def standardize_match(game_id: str) -> dict:
    info = build_meta_tables(game_id)
    meta = info["meta"]
    raw_events = load_json(RAW_PFF / "Event Data" / f"{game_id}.json")
    so_start = shootout_start_time(raw_events)  # video time, shared by events and tracking
    home_right = home_direction_from_events(raw_events)
    meta_disagrees = sorted(
        p for p, r in home_right.items() if p <= 4 and r != home_attacks_right(meta, p)
    )
    tracking = stream_tracking(game_id, info, so_start, home_right)
    events = build_events(game_id, info, raw_events, tracking["event_times"], so_start)

    shots5 = events[(events["period"] == 5) & (events["pff_event_type"] == "SH")]
    goals5 = shots5[shots5["result_name"] == "success"].groupby("source_team_id").size()
    home, away = info["home"], info["away"]
    # Scores count scored shots only; PFF has no score field, and own goals are not shots.
    # The StatsBomb crosswalk check compares scores and exposes any own goals missed here.
    scored = (events["pff_event_type"] == "SH") & (events["result_name"] == "success")
    goals = events[scored & (events["period"] < 5)].groupby("source_team_id").size()
    matches = pd.DataFrame(
        [
            {
                "match_id": info["match_id"],
                "source_match_id": game_id,
                "competition": meta["competition"]["name"],
                "season": str(meta["season"]),
                "date": pd.Timestamp(meta["date"]).date(),
                "kickoff_utc": pd.Timestamp(meta["date"], tz="UTC"),
                "home_team_id": home["team_id"],
                "away_team_id": away["team_id"],
                "source_home_team_id": home["source_team_id"],
                "source_away_team_id": away["source_team_id"],
                "home_score": int(goals.get(home["source_team_id"], 0)),
                "away_score": int(goals.get(away["source_team_id"], 0)),
                "home_shootout": int(goals5.get(home["source_team_id"], 0))
                if len(shots5)
                else None,
                "away_shootout": int(goals5.get(away["source_team_id"], 0))
                if len(shots5)
                else None,
                "stage": None,
                "venue": (meta.get("stadium") or {}).get("name"),
                "has_events": True,
                "has_tracking": True,
                "has_freeze_frames": False,
                "pff_week": meta.get("week"),
                "pff_fps": meta.get("fps"),
                "pff_home_start_left": meta.get("homeTeamStartLeft"),
                # periods where the metadata direction flags contradict the events (events win)
                "pff_direction_fixed_periods": ",".join(map(str, meta_disagrees)) or None,
                # periods where both keepers sit on the wrong side: player labels unreliable
                "pff_label_suspect_periods": ",".join(map(str, sorted(tracking["gk_swaps"])))
                or None,
            }
        ]
    )
    teams = info["teams"]
    tables = {
        "matches": matches,
        "teams": teams,
        "players": info["players"],
        "lineups": info["lineups"],
        "events": events,
        "team_crosswalk": pd.DataFrame(
            {
                "team_id": teams["team_id"],
                "source": SOURCE,
                "source_team_id": teams["source_team_id"],
                "source_team_name": teams["name"],
                "method": "name_slug",
                "confidence": 1.0,
            }
        ),  # fmt: skip
        "match_crosswalk": pd.DataFrame(
            [
                {
                    "match_id": info["match_id"],
                    "source": SOURCE,
                    "source_match_id": game_id,
                    "method": "date_teams",
                    "confidence": 1.0,
                }
            ]
        ),  # fmt: skip
    }
    write_tables(
        {k: v.drop(columns=["source"], errors="ignore") for k, v in tables.items()}, game_id
    )
    return {"n_frames": tracking["n_frames"], "unmatched_jerseys": tracking["unmatched"]}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--match", help="only this PFF game id")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args(argv)
    game_ids = sorted(p.stem for p in (RAW_PFF / "Metadata").glob("*.json"))
    if args.match:
        game_ids = [g for g in game_ids if g == args.match]
    todo = [g for g in game_ids if args.overwrite or not out_path("events", g).exists()]
    failed = []
    for g in tqdm(todo, desc="pff"):
        try:
            res = standardize_match(g)
            if res["unmatched_jerseys"]:
                print(g, "jerseys not in roster:", sorted(res["unmatched_jerseys"]))
        except Exception as exc:  # noqa: BLE001 - one bad match must not stop the run
            failed.append((g, repr(exc)))
    print(f"{len(todo) - len(failed)} matches written, {len(failed)} failed")
    for g, err in failed:
        print("FAILED", g, err)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
