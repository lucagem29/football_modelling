"""Mirror the community-parsed FIFA World Cup 2026 match report CSVs.

Source: github.com/Alamyy/Worldcup26 (not affiliated with FIFA), parsed from the 104 FIFA
Training Centre post-match reports. The repo's data/ folder is mirrored into
data/raw/fifa_wc2026/match_reports_community/ at one pinned commit (recorded in the manifest).
Existing files are skipped; delete the folder to pull a newer upstream version.

    uv run python -m football_modelling.ingest.fifa_wc2026.match_reports
"""

from football_modelling.ingest._download import RAW, mirror_github

REPO = "Alamyy/Worldcup26"


def main() -> None:
    mirror_github(
        REPO,
        RAW / "fifa_wc2026" / "match_reports_community",
        include=lambda p: p.startswith("data/"),
        compress=lambda p: False,
    )


if __name__ == "__main__":
    main()
