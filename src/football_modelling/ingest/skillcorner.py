"""Mirror SkillCorner open data (A-League 2024/25) into data/raw/skillcorner/.

Tracking files are stored in Git LFS upstream; they are fetched from the LFS media endpoint
and stored as ``.jsonl.gz``. Notebooks and source code from the repo are not mirrored.
"""

from football_modelling.ingest._download import RAW, mirror_github

REPO = "SkillCorner/opendata"


def keep(path: str) -> bool:
    return path.startswith("data/") or path in {"LICENSE", "README.md"}


def main() -> None:
    mirror_github(REPO, RAW / "skillcorner", include=keep, workers=4)


if __name__ == "__main__":
    main()
