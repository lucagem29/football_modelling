"""Download the schochastics football results into data/raw/context/world_results/.

1,237,935 results from 207 top-tier domestic leagues and 20 international club tournaments,
1888-2023, one parquet file (16 MB). Open Data Commons Attribution License (credit
schochastics/football-data). Used to compute our own club Elo ratings.
The goal-timing files in the same repo (~230 MB) are not mirrored.
"""

from football_modelling.ingest._download import RAW, mirror_github

REPO = "schochastics/football-data"
FILES = {"data/results/games.parquet", "data/elo/team_dictionary_men.csv", "README.md"}


def main() -> None:
    mirror_github(
        REPO,
        RAW / "context" / "world_results",
        include=lambda p: p in FILES or p.startswith("LICENSE"),
        compress=lambda p: False,
    )


if __name__ == "__main__":
    main()
