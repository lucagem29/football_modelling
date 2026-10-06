"""Download Club Elo ratings into data/raw/context/clubelo/.

1. One ranking snapshot per year (1 January, 1940 onwards) plus today, to collect every club
   name that ever had a rating (snapshots/<date>.csv).
2. The full rating history of each club (clubs/<Club>.csv; Club Elo uses the name without
   spaces in the URL).
Existing files are skipped; pass --refresh to re-download club histories (they grow daily).
"""

import csv
import sys
import time
from datetime import date

from football_modelling.ingest._download import RAW, download, session, write_manifest

BASE = "http://api.clubelo.com"
FIRST_YEAR = 1940


def main() -> None:
    refresh = "--refresh" in sys.argv
    dest = RAW / "context" / "clubelo"
    client = session()
    results, clubs = [], set()
    days = [date(y, 1, 1) for y in range(FIRST_YEAR, date.today().year + 1)] + [date.today()]
    for day in days:
        target = dest / "snapshots" / f"{day.isoformat()}.csv"
        results.append(download(client, f"{BASE}/{day.isoformat()}", target))
        with open(target, encoding="utf-8") as f:
            clubs |= {row["Club"] for row in csv.DictReader(f)}
        time.sleep(0.2)
    print(f"{len(clubs)} clubs found in {len(days)} snapshots", flush=True)
    for club in sorted(clubs):
        key = club.replace(" ", "")
        target = dest / "clubs" / f"{key}.csv"
        if refresh and target.exists():
            target.unlink()
        try:
            rec = download(client, f"{BASE}/{key}", target)
        except Exception as exc:  # noqa: BLE001
            results.append({"club": club, "status": "error", "error": repr(exc)})
            continue
        results.append({**rec, "club": club})
        if rec["status"] == "downloaded":
            time.sleep(0.2)
    write_manifest(dest, "clubelo", {"base": BASE, "files": results})
    errors = [r for r in results if r["status"] == "error"]
    print(f"{len(results)} files, {len(errors)} errors")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
