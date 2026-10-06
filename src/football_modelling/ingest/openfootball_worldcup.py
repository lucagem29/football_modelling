"""Mirror openfootball/worldcup.json into data/raw/context/openfootball_worldcup/.

Men's World Cups 1930-2026 as JSON: every match with round/group, date, venue, score and
goals, plus squads for recent tournaments. CC0 (public domain). Small (~3 MB).
"""

from football_modelling.ingest._download import RAW, mirror_github

REPO = "openfootball/worldcup.json"


def main() -> None:
    mirror_github(
        REPO,
        RAW / "context" / "openfootball_worldcup",
        local_path=lambda p: p,
        compress=lambda p: False,
    )


if __name__ == "__main__":
    main()
