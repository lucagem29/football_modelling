"""Smoke tests for the FIFA World Cup 2026 data in data/raw/fifa_wc2026/.

Skipped when the data is not present locally (data/ is never versioned).
"""

import json
from pathlib import Path

import pandas as pd
import pytest

BASE = Path(__file__).resolve().parents[1] / "data" / "raw" / "fifa_wc2026"
PTA = BASE / "post_tournament_analysis"
COMMUNITY = BASE / "match_reports_community" / "csv"

pytestmark = pytest.mark.skipif(not PTA.exists(), reason="fifa_wc2026 data not downloaded")

KEY_COLUMNS = {
    "tournament_comparison.csv": ["page", "metric", "unit", "normalisation", "tournament", "value"],
    "team_rankings.csv": [
        "page",
        "metric",
        "unit",
        "normalisation",
        "team_code",
        "value",
        "chart_rank",
    ],
    "key_findings.csv": ["chapter", "page", "finding_no", "finding"],
}
# Stacked bar on page 19: the chart is sorted by the total, so the parts are not monotonic
STACKED_PARTS = {"final_third_progressions_take_ons", "final_third_progressions_step_ins"}


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(PTA / name)


@pytest.mark.parametrize("name", sorted(KEY_COLUMNS))
def test_post_tournament_tables_parse_without_empty_keys(name):
    df = read(name)
    assert len(df) > 0
    assert df[KEY_COLUMNS[name]].notna().all().all()


def test_row_counts_match_readme():
    assert len(read("tournament_comparison.csv")) == 159
    assert len(read("team_rankings.csv")) == 238
    assert len(read("key_findings.csv")) == 73


def test_pages_text_is_valid_jsonl():
    with open(PTA / "pages_text.jsonl", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]
    assert len(rows) > 500
    assert all(r["text"] for r in rows)


def test_every_metric_has_one_row_per_tournament():
    tc = read("tournament_comparison.csv")
    per_metric = tc.groupby("metric")["tournament"].agg(lambda s: tuple(sorted(s)))
    assert (per_metric == ("FWC2018", "FWC2022", "FWC2026")).all()


def test_team_rankings_are_ordered_by_chart_rank():
    tr = read("team_rankings.csv")
    for metric, g in tr.groupby("metric"):
        g = g.sort_values("chart_rank")
        assert list(g["chart_rank"]) == list(range(1, len(g) + 1)), metric
        assert not g["team_code"].duplicated().any(), metric
        if metric not in STACKED_PARTS:
            assert g["value"].is_monotonic_decreasing, metric


@pytest.mark.skipif(not COMMUNITY.exists(), reason="community match reports not fetched")
def test_community_csvs_parse_and_team_codes_match():
    frames = {p.name: pd.read_csv(p) for p in COMMUNITY.glob("*.csv")}
    assert len(frames) >= 21 and all(len(df) > 0 for df in frames.values())
    assert frames["matches.csv"]["match_id"].notna().all()
    assert len(frames["matches.csv"]) == 104
    codes = set(frames["teams.csv"]["team_id"])
    assert len(codes) == 48
    assert set(frames["match_teams.csv"]["team_id"]) <= codes
    matches = frames["matches.csv"]
    assert set(matches["home_team_id"]) | set(matches["away_team_id"]) <= codes
    assert set(read("team_rankings.csv")["team_code"]) <= codes
