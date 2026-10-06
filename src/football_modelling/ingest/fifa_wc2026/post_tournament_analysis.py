"""Build CSV/JSONL tables from FIFA's "Post Tournament Analysis FIFA World Cup 2026" PDF.

Usage:
    uv run python -m football_modelling.ingest.fifa_wc2026.post_tournament_analysis PDF [OUT]

OUT defaults to data/raw/fifa_wc2026/post_tournament_analysis/. Needs ``pdftotext`` (poppler).
The PDF (117 MB) is not in the repo and must never be committed. Chart values are not
extracted from the PDF: they were transcribed by hand and live in chart_values_part*.py.
"""

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

from football_modelling.ingest._download import RAW
from football_modelling.ingest.fifa_wc2026.chart_values_part2 import K, T

DEFAULT_OUT = RAW / "fifa_wc2026" / "post_tournament_analysis"

# Chapter start pages (title slides) in the source document
CHAPTERS = [
    (6, "Tournament overview"),
    (39, "Building with a back three"),
    (84, "Wide player rotations"),
    (148, "Changing the point of attack"),
    (183, "Inside channel runs"),
    (219, "Key players progressing play"),
    (288, "Attacking transitions"),
    (332, "Counter-press"),
    (370, "Structured high press"),
    (426, "Organised low defensive blocks"),
    (467, "Goalkeeping"),
    (494, "Evolution of attacking corner strategies"),
]

# The PDF font maps some ligatures and punctuation to odd glyphs
FIXES = {"Þ": "fi", "㘶": "ff", "Ð": "–", "Õ": "'", "Ò": '"', "Ó": '"', "Ž": "é", "™": "ô"}


def clean(s: str) -> str:
    for a, b in FIXES.items():
        s = s.replace(a, b)
    return s


def chapter_for(page: int) -> str | None:
    name = None
    for start, title in CHAPTERS:
        if page >= start:
            name = title
    return name


def write_pages(pages: list[str], out: Path) -> None:
    """Full text per page, searchable, with page and chapter for provenance."""
    with open(out / "pages_text.jsonl", "w", encoding="utf-8") as f:
        for i, p in enumerate(pages, 1):
            body = re.sub(r"[ \t]+", " ", p).strip()
            body = body.replace("ADD IMAGE", "").replace("Document Sensitivity: Public", "").strip()
            if body:
                row = {"page": i, "chapter": chapter_for(i), "text": body}
                f.write(json.dumps(row, ensure_ascii=False) + "\n")


def key_findings(pages: list[str]) -> list[dict]:
    """Numbered key findings from each chapter's 'KEY FINDINGS' page."""
    rows = []
    for i, p in enumerate(pages, 1):
        if "KEY FINDINGS" not in p or "WHAT HAS BEEN IDENTIFIED" not in p:
            continue
        flat = re.sub(r"\s+", " ", p).split("IMPORTANT?", 1)[-1]
        # Split only on the next expected item number, so shirt numbers ("6. Kimmich") stay
        # inside the text
        n, pos, starts = 1, 0, []
        while m := re.search(rf"(?:^|\s){n}\.\s+", flat[pos:]):
            starts.append((n, pos + m.start(), pos + m.end()))
            pos += m.end()
            n += 1
        for j, (num, _, e) in enumerate(starts):
            end = starts[j + 1][1] if j + 1 < len(starts) else len(flat)
            body = flat[e:end].strip()
            if body:
                rows.append(
                    {"chapter": chapter_for(i), "page": i, "finding_no": num, "finding": body}
                )
    return rows


def main(pdf: Path, out: Path = DEFAULT_OUT) -> None:
    out.mkdir(parents=True, exist_ok=True)
    text = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    pages = [clean(p) for p in text.split("\f")]
    write_pages(pages, out)

    rows = key_findings(pages)
    with open(out / "key_findings.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["chapter", "page", "finding_no", "finding"])
        w.writeheader()
        w.writerows(rows)

    with open(out / "tournament_comparison.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["page", "metric", "unit", "normalisation", "tournament", "value"])
        w.writerows(T)
    with open(out / "team_rankings.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["page", "metric", "unit", "normalisation", "team_code", "value", "chart_rank"])
        w.writerows(K)

    print(
        f"pages={len(pages)} key_findings={len(rows)} tournament_rows={len(T)} team_rows={len(K)}"
    )


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    main(Path(sys.argv[1]), *(Path(a) for a in sys.argv[2:]))
