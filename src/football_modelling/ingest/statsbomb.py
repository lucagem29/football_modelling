"""Mirror StatsBomb (Hudl) open data into data/raw/statsbomb/.

Layout follows the upstream ``data/`` folder (events/, lineups/, matches/, three-sixty/,
competitions.json), with every JSON file stored as ``.json.gz``. About 16 GB uncompressed.
Publishing anything built on this data requires StatsBomb attribution and logo.
"""

from football_modelling.ingest._download import RAW, mirror_github

REPO = "hudl/open-data"


def keep(path: str) -> bool:
    return path.startswith(("data/", "doc/", "img/")) or path in {"LICENSE.pdf", "README.md"}


def main() -> None:
    mirror_github(REPO, RAW / "statsbomb", include=keep, workers=12)


if __name__ == "__main__":
    main()
