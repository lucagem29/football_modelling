"""Mirror Metrica Sports sample data (3 anonymized matches) into data/raw/metrica/.

Small source (~180 MB), stored uncompressed.
"""

from football_modelling.ingest._download import RAW, mirror_github

REPO = "metrica-sports/sample-data"


def main() -> None:
    mirror_github(REPO, RAW / "metrica", compress=lambda p: False)


if __name__ == "__main__":
    main()
