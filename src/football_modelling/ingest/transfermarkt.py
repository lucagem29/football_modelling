"""Download the Transfermarkt datasets (dcaribou) into data/raw/transfermarkt/.

One zip with all tables as CSV: players, clubs, competitions, games, appearances, lineups,
game events, player valuations, transfers. CC0. Upstream stopped refreshing recent data
(see their status announcement); what was published stays available.
The zip is kept as downloaded (~240 MB); delete it to fetch a newer release.
"""

from football_modelling.ingest._download import RAW, download, session, write_manifest

URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/transfermarkt-datasets.zip"


def main() -> None:
    dest = RAW / "transfermarkt"
    client = session()
    head = client.head(URL, timeout=60)
    head.raise_for_status()
    size = int(head.headers["content-length"])
    # R2 returns the MD5 of the object as ETag for single-part uploads
    etag = head.headers.get("etag", "").strip('"')
    md5 = etag if len(etag) == 32 and "-" not in etag else None
    rec = download(client, URL, dest / "transfermarkt-datasets.zip", size=size, md5=md5)
    write_manifest(
        dest,
        "transfermarkt",
        {"url": URL, "last_modified": head.headers.get("last-modified"), "files": [rec]},
    )


if __name__ == "__main__":
    main()
