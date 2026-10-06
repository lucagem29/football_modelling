"""Smoke tests for standardized StatsBomb data. Skipped when nothing has been standardized."""

import pytest

from football_modelling.paths import PROCESSED

pytestmark = pytest.mark.skipif(
    not (PROCESSED / "events" / "source=statsbomb").exists(),
    reason="StatsBomb not standardized (run football_modelling.standardize.statsbomb)",
)

FINAL = "2022-12-18_argentina_france"


@pytest.fixture(scope="module")
def con():
    from football_modelling.db import connect

    return connect()


def one(con, sql):
    return con.execute(sql).fetchone()


def test_tables_have_rows(con):
    for table in ("matches", "teams", "players", "lineups", "events", "freeze_frames"):
        assert one(con, f"select count(*) from {table} where source = 'statsbomb'")[0] > 0, table


def test_no_null_ids_and_unique_matches(con):
    assert one(con, "select count(*) from events where match_id is null or team_id is null")[0] == 0
    n, distinct = one(con, "select count(*), count(distinct match_id) from matches")
    assert n == distinct


ON_PITCH = "{x} between 0 and 105 and {y} between 0 and 68"


def test_coordinates_on_pitch(con):
    events_ok = (
        ON_PITCH.format(x="start_x", y="start_y") + " and " + ON_PITCH.format(x="end_x", y="end_y")
    )
    assert one(con, f"select count(*) from events where not ({events_ok})")[0] == 0
    frames_ok = ON_PITCH.format(x="x", y="y")
    assert one(con, f"select count(*) from freeze_frames where not ({frames_ok})")[0] == 0


def test_acting_team_attacks_left_to_right(con):
    share = one(
        con,
        "select avg((start_x > 52.5)::int) from events where type_name like 'shot%' and period < 5",
    )[0]
    assert share > 0.98


def test_time_restarts_each_period(con):
    assert one(con, "select min(time_s) from events")[0] >= 0
    assert one(con, "select max(time_s) from events where period in (1, 2)")[0] < 75 * 60


def test_freeze_frame_actor_sits_on_event_location(con):
    gap = one(
        con,
        """select max(sqrt((f.x - e.start_x)^2 + (f.y - e.start_y)^2))
           from freeze_frames f join events e
             on e.match_id = f.match_id and e.source_id = f.event_source_id
           where f.actor and e.type_name like 'shot%'""",
    )[0]
    assert gap < 0.5


@pytest.mark.skipif(
    not (PROCESSED / "matches" / "source=statsbomb" / "3869685.parquet").exists(),
    reason="WC 2022 final not standardized",
)
def test_wc2022_final(con):
    row = one(
        con,
        f"select home_score, away_score, home_shootout, away_shootout, stage from matches"
        f" where match_id = '{FINAL}'",
    )
    assert row == (3, 3, 4, 2, "Final")
    goals = one(
        con,
        f"select count(*) from events where match_id = '{FINAL}' and period < 5"
        " and type_name like 'shot%' and result_name = 'success'",
    )[0]
    assert goals == 6  # 3-3 after extra time: 3 penalties + 3 open-play goals, no own goals
