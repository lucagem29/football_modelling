"""Download the IDSSE dataset (Bassek et al., figshare article 28196177) into data/raw/idsse/.

7 matches of Bundesliga / 2. Bundesliga: DFL match information, raw events and raw observed
positions (TRACAB-based), all XML, stored as ``.xml.gz``. CC BY 4.0. ~2.6 GB uncompressed.
"""

from football_modelling.ingest._download import (
    RAW,
    download,
    raise_on_errors,
    run_parallel,
    session,
    write_manifest,
)

ARTICLE = 28196177


def main() -> None:
    dest = RAW / "idsse"
    client = session()
    r = client.get(f"https://api.figshare.com/v2/articles/{ARTICLE}", timeout=60)
    r.raise_for_status()
    article = r.json()

    def job(item: dict):
        gz = item["name"].endswith(".xml")
        target = dest / (item["name"] + (".gz" if gz else ""))
        return lambda: {
            **download(
                client,
                item["download_url"],
                target,
                compress=gz,
                size=item["size"],
                md5=item["computed_md5"],
            ),
            "name": item["name"],
        }

    results = run_parallel((job(f) for f in article["files"]), workers=4, desc="idsse")
    write_manifest(
        dest,
        "idsse",
        {"article": article["url_public_html"], "license": article["license"], "files": results},
    )
    raise_on_errors(results, "idsse")


if __name__ == "__main__":
    main()
