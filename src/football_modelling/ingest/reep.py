"""Mirror the Reep Register into data/raw/reep/.

Stable ids for players, teams, coaches and competitions, linked to the ids of 40+ data
providers (anchored on Wikidata). CC0. The backbone for player_crosswalk and team_crosswalk.
CSV and JSON are stored gzip-compressed (~140 MB uncompressed).
"""

from football_modelling.ingest._download import RAW, mirror_github

REPO = "withqwerty/reep"


def keep(path: str) -> bool:
    return path.startswith("data/") or path in {"LICENSE", "README.md", "CHANGELOG.md"}


def main() -> None:
    mirror_github(
        REPO, RAW / "reep", include=keep, compress=lambda p: p.endswith((".csv", ".json"))
    )


if __name__ == "__main__":
    main()
