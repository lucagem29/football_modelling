"""Link StatsBomb and PFF for matches both providers cover (WC 2022).

1. player_crosswalk: within a match both providers list shirt numbers, so players are paired
   on (match, team, jersey); names are compared as a check. The unified ``player_id`` is
   ``<name slug>_<birth date>`` from PFF (StatsBomb has no birth dates).
2. event_crosswalk: StatsBomb events are paired one-to-one with PFF events of a compatible
   type. Per period we first measure the clock offset between the providers (median time gap
   of same-player, same-type candidates), then pair events within a short window by a cost of
   time gap, location gap and player agreement.

    uv run python -m football_modelling.sync.statsbomb_pff                       # all shared
    uv run python -m football_modelling.sync.statsbomb_pff --match 2022-12-18_argentina_france
"""

from __future__ import annotations

import argparse
import difflib
import os
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

from football_modelling.db import connect
from football_modelling.ids import slugify
from football_modelling.paths import CROSSWALK

PAIR = "statsbomb_pff"
WINDOW_S = 3.0  # max time gap after the offset correction
OFFSET_WINDOW_S = 10.0  # window used to estimate the offset
OFFSET_WINDOW_WIDE_S = 90.0  # fallback when a period has no anchors (shootouts)
# StatsBomb SPADL type -> PFF possession event types it may correspond to
COMPATIBLE = {
    "pass": {"PA", "CR"},
    "cross": {"CR", "PA"},
    "throw_in": {"PA"},
    "goalkick": {"PA"},
    "freekick_short": {"PA"},
    "freekick_crossed": {"CR", "PA"},
    "corner_short": {"PA"},
    "corner_crossed": {"CR", "PA"},
    "shot": {"SH"},
    "shot_penalty": {"SH"},
    "shot_freekick": {"SH"},
    "clearance": {"CL"},
}


def _name_similarity(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, slugify(a), slugify(b)).ratio()


def link_players(con, match_id: str) -> pd.DataFrame:
    pairs = con.execute(
        """
        select s.team_id, s.jersey, s.source_player_id sb_id, ps.name sb_name, ps.nickname sb_nick,
               p.source_player_id pff_id, pp.name pff_name, pp.nickname pff_nick, pp.birth_date
        from lineups s
        join lineups p on p.match_id = s.match_id and p.team_id = s.team_id and p.jersey = s.jersey
        left join players ps on ps.source = 'statsbomb' and ps.source_player_id = s.source_player_id
        left join players pp on pp.source = 'pff' and pp.source_player_id = p.source_player_id
        where s.source = 'statsbomb' and p.source = 'pff' and s.match_id = ?
        """,
        [match_id],
    ).df()
    rows = []
    for r in pairs.itertuples():
        sim = max(
            _name_similarity(r.sb_name, r.pff_name),
            _name_similarity(r.sb_nick or r.sb_name, r.pff_nick),
            _name_similarity(r.sb_nick, r.pff_name),
        )
        player_id = f"{slugify(r.pff_name or r.pff_nick)}_{r.birth_date}" if r.birth_date else None
        conf = 1.0 if sim >= 0.6 else 0.7  # jersey match is strong; names only confirm
        for source, sid, name in (("statsbomb", r.sb_id, r.sb_name), ("pff", r.pff_id, r.pff_name)):
            rows.append(
                {
                    "player_id": player_id,
                    "source": source,
                    "source_player_id": sid,
                    "name": name,
                    "birth_date": r.birth_date,
                    "reep_id": None,
                    "method": "match_team_jersey",
                    "confidence": conf,
                    "name_similarity": round(sim, 3),
                }
            )
    return pd.DataFrame(rows)


def link_events(con, match_id: str, players: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    q = """select source_id, period, time_s, team_id, source_player_id, start_x, start_y,
                  type_name, {extra} from events where source = ? and match_id = ?"""
    sb = con.execute(q.format(extra="null as pff_event_type"), ["statsbomb", match_id]).df()
    pff = con.execute(q.format(extra="pff_event_type"), ["pff", match_id]).df()
    sb = sb[sb["type_name"].isin(COMPATIBLE)].reset_index(drop=True)
    pff = pff[pff["pff_event_type"].isin({"PA", "CR", "SH", "CL"}) & pff["time_s"].notna()]
    pff = pff.reset_index(drop=True)
    # StatsBomb player -> PFF player through the player crosswalk
    pid = players.pivot_table(
        index="player_id", columns="source", values="source_player_id", aggfunc="first"
    )
    sb_to_pff = dict(zip(pid["statsbomb"], pid["pff"], strict=True)) if len(pid) else {}
    sb["pff_player"] = sb["source_player_id"].map(sb_to_pff)

    rows, offsets = [], {}
    for period in sorted(set(sb["period"]) & set(pff["period"])):
        s = sb[sb["period"] == period]
        p = pff[pff["period"] == period]
        # 1) clock offset: same player and compatible type, nearest in time. Shootouts use a
        #    different zero point per provider (~30 s apart), so widen the window if needed.
        gaps = []
        for window in (OFFSET_WINDOW_S, OFFSET_WINDOW_WIDE_S):
            for e in s.itertuples():
                c = p[(p["source_player_id"] == e.pff_player)
                      & p["pff_event_type"].isin(COMPATIBLE[e.type_name])
                      & ((p["time_s"] - e.time_s).abs() <= window)]  # fmt: skip
                if len(c):
                    d = c["time_s"] - e.time_s
                    gaps.append(d.iloc[d.abs().argmin()])
            if gaps:
                break
        offset = float(np.median(gaps)) if gaps else 0.0
        offsets[int(period)] = {"offset_s": round(offset, 3), "n_anchor_pairs": len(gaps)}
        # 2) candidate pairs with a cost, then greedy one-to-one by ascending cost
        cands = []
        for e in s.itertuples():
            c = p[(p["team_id"] == e.team_id)
                  & p["pff_event_type"].isin(COMPATIBLE[e.type_name])
                  & ((p["time_s"] - offset - e.time_s).abs() <= WINDOW_S)]  # fmt: skip
            for f in c.itertuples():
                dt = f.time_s - offset - e.time_s
                dist = (
                    float(np.hypot(f.start_x - e.start_x, f.start_y - e.start_y))
                    if pd.notna(f.start_x)
                    else np.nan
                )
                same_player = f.source_player_id == e.pff_player
                cost = (
                    abs(dt)
                    + (0.1 * dist if not np.isnan(dist) else 1.0)
                    + (0 if same_player else 2)
                )
                cands.append((cost, e.source_id, f.source_id, dt, dist, same_player))
        used_sb, used_pff = set(), set()
        for _cost, sid, fid, dt, dist, same_player in sorted(cands):
            if sid in used_sb or fid in used_pff:
                continue
            used_sb.add(sid)
            used_pff.add(fid)
            conf = max(0.0, 1.0 - abs(dt) / WINDOW_S * 0.5 - (0 if same_player else 0.3))
            rows.append(
                {
                    "match_id": match_id,
                    "source_a": "statsbomb",
                    "event_id_a": sid,
                    "source_b": "pff",
                    "event_id_b": fid,
                    "time_diff_s": dt,
                    "dist_m": dist,
                    "same_player": same_player,
                    "method": "offset_time_player_type_loc",
                    "confidence": round(conf, 3),
                }
            )
    stats = {
        "sb_candidates": len(sb),
        "pff_candidates": len(pff),
        "linked": len(rows),
        "offsets": offsets,
    }
    return pd.DataFrame(rows), stats


def tracking_label_check(con, match_id: str) -> pd.DataFrame:
    """Per period: do PFF's tracking labels agree with StatsBomb's events?

    For every linked event with a PFF frame we compare the StatsBomb event location with
    (a) the tracked position of the event's player and (b) the team of the nearest tracked
    player. In clean periods (a) is a few meters and (b) is the acting team ~80% of the time.
    In the final's extra time PFF swapped the teams' labels: (a) jumps to 13-21 m and (b)
    drops to ~35%. Periods failing the check get ``labels_ok = false``.
    """
    return (
        con.execute(
            """
        with linked as (
          select distinct sb.source_id, sb.period, pf.pff_frame frame,
                 pf.source_player_id pff_player,
                 sb.team_id acting,
                 case when sb.team_id = m.home_team_id then sb.start_x else 105 - sb.start_x end hx,
                 case when sb.team_id = m.home_team_id then sb.start_y else 68 - sb.start_y end hy
          from event_crosswalk x
          join events sb on sb.source = 'statsbomb' and sb.source_id = x.event_id_a
                        and sb.match_id = x.match_id
          join events pf on pf.source = 'pff' and pf.source_id = x.event_id_b
                        and pf.match_id = x.match_id
          join matches m on m.source = 'statsbomb' and m.match_id = x.match_id
          where x.match_id = $1 and pf.pff_frame is not null),
        tr as (select frame, team_id, source_player_id, x, y from tracking
               where match_id = $1 and object_id <> 'ball'
                 and frame in (select frame from linked)),
        actor as (
          select l.period, median(sqrt((t.x - l.hx)^2 + (t.y - l.hy)^2)) gap
          from linked l join tr t on t.frame = l.frame and t.source_player_id = l.pff_player
          group by 1),
        nearest as (
          select l.period, l.acting, t.team_id,
                 row_number() over (partition by l.source_id
                                    order by (t.x - l.hx)^2 + (t.y - l.hy)^2) rk
          from linked l join tr t on t.frame = l.frame)
        select $1 match_id, n.period::int8 period, count(*) n_events,
               round(avg((n.team_id = n.acting)::int), 3) nearest_is_acting_team,
               round(any_value(a.gap), 2) actor_gap_median_m
        from nearest n left join actor a using (period)
        where n.rk = 1
        group by n.period order by n.period
        """,
            [match_id],
        )
        .df()
        .assign(
            labels_ok=lambda d: (d["nearest_is_acting_team"] >= 0.6) & (d["actor_gap_median_m"] < 6)
        )
    )


def write(df: pd.DataFrame, table: str, match_id: str) -> Path:
    path = CROSSWALK / table / f"pair={PAIR}" / f"{match_id}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    # Partitioned by provider pair, so `source` (player_crosswalk) stays a real column
    frame = pl.from_pandas(df)
    if "confidence" in frame.columns:
        frame = frame.with_columns(pl.col("confidence").cast(pl.Float32))
    tmp = path.with_suffix(".tmp")
    frame.write_parquet(tmp)
    os.replace(tmp, path)
    return path


def shared_matches(con) -> list[str]:
    return [
        r[0]
        for r in con.execute(
            """select match_id from matches group by 1
               having count(distinct source) filter (where source in ('statsbomb', 'pff')) = 2
               order by 1"""
        ).fetchall()
    ]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--match")
    args = ap.parse_args(argv)
    con = connect()
    matches = [args.match] if args.match else shared_matches(con)
    for m in matches:
        players = link_players(con, m)
        write(players, "player_crosswalk", m)
        events, stats = link_events(con, m, players)
        write(events, "event_crosswalk", m)
        # the label check reads the event_crosswalk view, so refresh the views first
        con = connect()
        quality = tracking_label_check(con, m)
        write(quality, "sync_quality", m)
        bad = quality.loc[~quality["labels_ok"], "period"].tolist()
        low = players[players["confidence"] < 1.0]["name"].nunique()
        print(f"{m}: {len(players) // 2} players linked ({low} with weak name match), "
              f"{stats['linked']}/{stats['sb_candidates']} StatsBomb events linked, "
              f"tracking labels suspect in periods {bad or 'none'}")  # fmt: skip


if __name__ == "__main__":
    main()
