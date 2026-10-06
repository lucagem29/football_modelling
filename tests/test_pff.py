"""Smoke tests for standardized PFF data and the StatsBomb <-> PFF links.

Skipped when nothing has been standardized yet.
"""

import pytest

from football_modelling.paths import CROSSWALK, PROCESSED

pytestmark = pytest.mark.skipif(
    not (PROCESSED / "events" / "source=pff").exists(),
    reason="PFF not standardized (run football_modelling.standardize.pff)",
)

FINAL = "2022-12-18_argentina_france"
HAS_FINAL = (PROCESSED / "events" / "source=pff" / "10517.parquet").exists()
HAS_SYNC = (CROSSWALK / "event_crosswalk" / "pair=statsbomb_pff" / f"{FINAL}.parquet").exists()


@pytest.fixture(scope="module")
def con():
    from football_modelling.db import connect

    return connect()


def one(con, sql, params=None):
    return con.execute(sql, params or []).fetchone()


def test_tables_have_rows_and_ids(con):
    for table in ("matches", "teams", "players", "lineups", "events", "tracking"):
        assert one(con, f"select count(*) from {table} where source = 'pff'")[0] > 0, table
    assert one(con, "select count(*) from events where source = 'pff' and match_id is null")[0] == 0


def test_every_tracked_player_is_in_the_roster(con):
    # players missing from the roster get an object_id like 'home_7'
    unknown = "object_id like 'home_%' or object_id like 'away_%'"
    assert one(con, f"select count(*) from tracking where {unknown}")[0] == 0


def test_tracking_on_pitch(con):
    share = one(
        con,
        "select avg((x between -3 and 108 and y between -3 and 71)::int) from tracking"
        " where source = 'pff' and object_id <> 'ball'",
    )[0]
    assert share > 0.995


def test_shots_start_in_attacking_half(con):
    share = one(
        con,
        "select avg((start_x > 52.5)::int) from events"
        " where source = 'pff' and pff_event_type = 'SH' and period < 5",
    )[0]
    assert share > 0.98


@pytest.mark.skipif(not HAS_FINAL, reason="final not standardized")
def test_final_scores_and_shootout(con):
    row = one(
        con,
        "select home_score, away_score, home_shootout, away_shootout, kickoff_utc::varchar"
        " from matches where source = 'pff' and match_id = ?",
        [FINAL],
    )
    assert row[:4] == (3, 3, 4, 2)
    assert row[4].startswith("2022-12-18 15:00:00")


@pytest.mark.skipif(not HAS_SYNC, reason="StatsBomb <-> PFF not linked")
def test_final_links(con):
    unlinked_players = one(
        con,
        """select count(*) from lineups l
           where l.source = 'pff' and l.match_id = ? and l.source_player_id not in
                 (select source_player_id from player_crosswalk where source = 'pff')""",
        [FINAL],
    )[0]
    assert unlinked_players == 0
    linked_shots = one(
        con,
        """select avg((x.event_id_b is not null)::int) from events e
           left join event_crosswalk x on x.event_id_a = e.source_id and x.match_id = e.match_id
           where e.source = 'statsbomb' and e.match_id = ? and e.type_name like 'shot%'""",
        [FINAL],
    )[0]
    assert linked_shots == 1.0
    suspect = [
        r[0]
        for r in con.execute(
            "select period from sync_quality where match_id = ? and not labels_ok order by 1",
            [FINAL],
        ).fetchall()
    ]
    assert suspect == [3, 4]  # PFF swapped the team labels in extra time of the final
