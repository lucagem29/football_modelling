"""Download the Wyscout public dataset (Pappalardo et al. 2019) into data/raw/wyscout/.

Figshare collection 4415000: events and matches (zip per competition), players, teams,
competitions, coaches, referees and the id-to-name lookup tables. CC BY 4.0. Zips are kept
as downloaded; they are read member by member during standardization.
"""

from football_modelling.ingest._download import (
    RAW,
    download,
    raise_on_errors,
    run_parallel,
    session,
    write_manifest,
)

COLLECTION = 4415000
WANTED = {
    "Events",
    "Matches",
    "Players",
    "Teams",
    "Competitions",
    "Coaches",
    "Referees",
    "Mapping of event identifiers to event names",
    "Mapping of tag identifiers to tag names",
}


def main() -> None:
    dest = RAW / "wyscout"
    client = session()
    r = client.get(
        f"https://api.figshare.com/v2/collections/{COLLECTION}/articles?page_size=100", timeout=60
    )
    r.raise_for_status()
    jobs = []
    for summary in r.json():
        if summary["title"] not in WANTED:
            continue
        article = client.get(summary["url"], timeout=60).json()
        for item in article["files"]:
            target = dest / item["name"]
            jobs.append(
                lambda item=item, target=target, article=article: {
                    **download(
                        client,
                        item["download_url"],
                        target,
                        size=item["size"],
                        md5=item["computed_md5"],
                    ),
                    "article": article["url_public_html"],
                    "license": article["license"]["name"],
                }
            )
    results = run_parallel(jobs, workers=4, desc="wyscout")
    write_manifest(dest, "wyscout", {"collection": COLLECTION, "files": results})
    raise_on_errors(results, "wyscout")


if __name__ == "__main__":
    main()
