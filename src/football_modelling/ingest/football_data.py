"""Download football-data.co.uk results + betting odds into data/raw/context/football_data/.

Main leagues: one CSV per division and season (mmz4281/<season>/<div>.csv, from 1993/94).
Extra leagues: one CSV per country with all seasons (new/<code>.csv).
Finished seasons are downloaded once. The current season and the extra-league files are
refreshed on every run, because upstream updates them weekly.
"""

import os
import sys
import time
from datetime import date

from football_modelling.ingest._download import RAW, download, session, write_manifest

BASE = "https://football-data.co.uk"
DIVISIONS = [
    "E0", "E1", "E2", "E3", "EC",  # England
    "SC0", "SC1", "SC2", "SC3",  # Scotland
    "D1", "D2", "I1", "I2", "SP1", "SP2", "F1", "F2",  # Germany, Italy, Spain, France
    "N1", "B1", "P1", "T1", "G1",  # Netherlands, Belgium, Portugal, Turkey, Greece
]  # fmt: skip
EXTRA = [
    "ARG", "AUT", "BRA", "CHN", "DNK", "FIN", "IRL", "JPN",
    "MEX", "NOR", "POL", "ROU", "RUS", "SWE", "SWZ", "USA",
]  # fmt: skip
FIRST_SEASON = 1993


def season_code(start_year: int) -> str:
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def current_season_start(today: date) -> int:
    return today.year if today.month >= 7 else today.year - 1


def fetch(client, url, target, refresh: bool) -> dict:
    """Download ``url``; 404 means the division did not exist that season."""
    if target.exists() and not refresh:
        return {"path": target.as_posix(), "status": "existing"}
    tmp = target.with_name(target.name + ".new")
    try:
        rec = download(client, url, tmp)
    except Exception as exc:  # noqa: BLE001
        if "404" in repr(exc):
            return {"url": url, "status": "not_available"}
        return {"url": url, "status": "error", "error": repr(exc)}
    os.replace(tmp, target)
    time.sleep(0.3)  # be polite to a small free site
    return {**rec, "path": target.as_posix(), "status": "refreshed" if refresh else "downloaded"}


def main() -> None:
    dest = RAW / "context" / "football_data"
    client = session()
    current = current_season_start(date.today())
    results = []
    for start in range(FIRST_SEASON, current + 1):
        code = season_code(start)
        for div in DIVISIONS:
            target = dest / "mmz4281" / code / f"{div}.csv"
            url = f"{BASE}/mmz4281/{code}/{div}.csv"
            results.append(fetch(client, url, target, refresh=start == current))
        print(code, "done", flush=True)
    for code in EXTRA:
        results.append(fetch(client, f"{BASE}/new/{code}.csv", dest / "new" / f"{code}.csv", True))
    results.append(fetch(client, f"{BASE}/notes.txt", dest / "notes.txt", True))
    write_manifest(dest, "football_data", {"base": BASE, "files": results})
    errors = [r for r in results if r["status"] == "error"]
    print(f"{len(results)} files checked, {len(errors)} errors")
    if errors:
        for e in errors[:10]:
            print("ERROR", e["url"], e["error"])
        sys.exit(1)


if __name__ == "__main__":
    main()
