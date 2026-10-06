"""Mirror martj42/international_results into data/raw/context/international_results/.

results.csv, shootouts.csv, goalscorers.csv, former_names.csv; all men's full internationals
since 1872. Upstream updates after every international window; re-run to refresh is not
automatic because existing files are skipped (delete the folder to force a refresh).
"""

from football_modelling.ingest._download import RAW, mirror_github

REPO = "martj42/international_results"


def main() -> None:
    mirror_github(
        REPO,
        RAW / "context" / "international_results",
        local_path=lambda p: p,
        compress=lambda p: False,
    )


if __name__ == "__main__":
    main()
