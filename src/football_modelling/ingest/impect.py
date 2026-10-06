"""Mirror Impect open data (Bundesliga 2023/24) into data/raw/impect/, JSON stored as .json.gz."""

from football_modelling.ingest._download import RAW, mirror_github

REPO = "ImpectAPI/open-data"


def keep(path: str) -> bool:
    return path.startswith(("data/", "img/")) or path in {
        "Documentation.pdf",
        "LICENSE.pdf",
        "README.md",
    }


def main() -> None:
    mirror_github(REPO, RAW / "impect", include=keep, workers=8)


if __name__ == "__main__":
    main()
