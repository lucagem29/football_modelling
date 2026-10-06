"""Shared helpers for raw downloads: streaming, optional gzip, integrity checks, manifests.

Every download is idempotent: an existing target is skipped. Files are streamed to a
``.part`` file and renamed only after the integrity check passes, so an interrupted run never
leaves a half-written file behind. Large text files (JSON, JSONL, XML) can be stored
gzip-compressed; checks always run on the uncompressed bytes, so the stored content is
byte-identical to upstream once decompressed.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3.util.retry import Retry

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW = PROJECT_ROOT / "data" / "raw"
CHUNK = 1024 * 1024
COMPRESS_SUFFIXES = (".json", ".jsonl", ".xml")


def session() -> requests.Session:
    client = requests.Session()
    retry = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    client.mount("https://", HTTPAdapter(max_retries=retry, pool_maxsize=16))
    client.mount("http://", HTTPAdapter(max_retries=retry, pool_maxsize=16))
    client.headers["User-Agent"] = "football_modelling (research data mirror)"
    return client


class _Hashes:
    """Running hashes over uncompressed bytes; git blob sha needs the size up front."""

    def __init__(self, git_size: int | None = None):
        self.md5 = hashlib.md5()
        self.sha256 = hashlib.sha256()
        self.git = hashlib.sha1(f"blob {git_size}\0".encode()) if git_size is not None else None
        self.size = 0

    def update(self, chunk: bytes) -> None:
        self.md5.update(chunk)
        self.sha256.update(chunk)
        if self.git is not None:
            self.git.update(chunk)
        self.size += len(chunk)


def _check(h: _Hashes, target: Path, *, size, md5, sha256, git_sha) -> None:
    problems = []
    if size is not None and h.size != size:
        problems.append(f"size {h.size} != {size}")
    if md5 is not None and h.md5.hexdigest() != md5:
        problems.append("md5 mismatch")
    if sha256 is not None and h.sha256.hexdigest() != sha256:
        problems.append("sha256 mismatch")
    if git_sha is not None and h.git.hexdigest() != git_sha:
        problems.append("git blob sha mismatch")
    if problems:
        raise ValueError(f"Integrity check failed for {target}: {', '.join(problems)}")


def download(
    client: requests.Session,
    url: str,
    target: Path,
    *,
    compress: bool = False,
    size: int | None = None,
    md5: str | None = None,
    sha256: str | None = None,
    git_sha: str | None = None,
) -> dict:
    """Stream ``url`` to ``target`` (``target`` already carries ``.gz`` when compressing)."""
    if target.exists():
        return {"path": target.as_posix(), "status": "existing"}
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".part")
    h = _Hashes(git_size=size if git_sha else None)
    with client.get(url, stream=True, timeout=(15, 300)) as response:
        response.raise_for_status()
        opener = gzip.open if compress else open
        with opener(part, "wb") as out:
            for chunk in response.iter_content(CHUNK):
                h.update(chunk)
                out.write(chunk)
    try:
        _check(h, target, size=size, md5=md5, sha256=sha256, git_sha=git_sha)
    except ValueError:
        part.unlink()
        raise
    os.replace(part, target)
    return {
        "path": target.as_posix(),
        "status": "downloaded",
        "bytes_uncompressed": h.size,
        "sha256_uncompressed": h.sha256.hexdigest(),
    }


def adopt_uncompressed(existing: Path, target: Path, *, size=None, git_sha=None) -> bool:
    """Compress a file downloaded earlier without gzip, after verifying it against upstream.

    Returns True if ``existing`` was verified, compressed to ``target`` and removed.
    """
    if not existing.exists() or target.exists():
        return False
    h = _Hashes(git_size=existing.stat().st_size if git_sha else None)
    part = target.with_name(target.name + ".part")
    with open(existing, "rb") as src, gzip.open(part, "wb") as out:
        for chunk in iter(lambda: src.read(CHUNK), b""):
            h.update(chunk)
            out.write(chunk)
    try:
        _check(h, existing, size=size, md5=None, sha256=None, git_sha=git_sha)
    except ValueError:
        part.unlink()
        return False
    os.replace(part, target)
    existing.unlink()
    return True


def run_parallel(jobs: Iterable[Callable[[], dict]], *, workers: int, desc: str) -> list[dict]:
    """Run download jobs in threads; collect results and errors instead of stopping early."""
    jobs = list(jobs)
    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(job) for job in jobs]
        for future in tqdm(as_completed(futures), total=len(futures), desc=desc):
            try:
                results.append(future.result())
            except Exception as exc:  # noqa: BLE001 - recorded in the manifest, re-raised below
                results.append({"status": "error", "error": repr(exc)})
    return results


def write_manifest(dest: Path, name: str, payload: dict) -> Path:
    """Write ``<dest>/_manifest_<name>.json`` (overwritten on every run)."""
    payload = {"retrieved_utc": datetime.now(UTC).isoformat(timespec="seconds"), **payload}
    path = dest / f"_manifest_{name}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return path


def raise_on_errors(results: list[dict], source: str) -> None:
    errors = [r for r in results if r.get("status") == "error"]
    if errors:
        for e in errors[:10]:
            print("ERROR", e["error"])
        raise SystemExit(f"{source}: {len(errors)} downloads failed (see above); re-run to retry")


# --- GitHub mirrors -------------------------------------------------------------------------


def github_tree(client: requests.Session, repo: str, ref: str) -> tuple[str, list[dict]]:
    """Resolve ``ref`` to a commit and list every blob in it."""
    r = client.get(f"https://api.github.com/repos/{repo}/commits/{ref}", timeout=60)
    r.raise_for_status()
    commit = r.json()["sha"]
    url = f"https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1"
    r = client.get(url, timeout=120)
    r.raise_for_status()
    tree = r.json()
    if tree.get("truncated"):
        raise RuntimeError(f"GitHub tree listing for {repo} is truncated")
    return commit, [item for item in tree["tree"] if item["type"] == "blob"]


def _lfs_pointer(client: requests.Session, repo: str, commit: str, path: str) -> dict | None:
    r = client.get(f"https://raw.githubusercontent.com/{repo}/{commit}/{quote(path)}", timeout=60)
    r.raise_for_status()
    text = r.text
    if not text.startswith("version https://git-lfs"):
        return None
    fields = dict(line.split(" ", 1) for line in text.splitlines() if " " in line)
    return {"sha256": fields["oid"].removeprefix("sha256:"), "size": int(fields["size"])}


def mirror_github(
    repo: str,
    dest: Path,
    *,
    ref: str = "HEAD",
    include: Callable[[str], bool] = lambda p: not p.startswith("."),
    local_path: Callable[[str], str] = lambda p: p.removeprefix("data/"),
    compress: Callable[[str], bool] = lambda p: p.endswith(COMPRESS_SUFFIXES),
    workers: int = 8,
) -> list[dict]:
    """Mirror the files of a GitHub repo at one pinned commit into ``dest``.

    Git LFS files are fetched from media.githubusercontent.com and checked against the
    sha256 in their pointer file. Other files are checked against their git blob sha.
    """
    client = session()
    commit, blobs = github_tree(client, repo, ref)
    blobs = [b for b in blobs if include(b["path"])]
    dest.mkdir(parents=True, exist_ok=True)

    def job(blob: dict) -> Callable[[], dict]:
        def run() -> dict:
            path = blob["path"]
            gz = compress(path)
            local = dest / local_path(path)
            target = local.with_name(local.name + ".gz") if gz else local
            if target.exists():
                return {"path": path, "status": "existing"}
            if blob["size"] < 1024 and path.endswith((".jsonl", ".csv", ".parquet", ".zip")):
                pointer = _lfs_pointer(client, repo, commit, path)
            else:
                pointer = None
            if pointer:
                url = f"https://media.githubusercontent.com/media/{repo}/{commit}/{quote(path)}"
                rec = download(client, url, target, compress=gz, **pointer)
            else:
                if gz and adopt_uncompressed(local, target, git_sha=blob["sha"]):
                    return {"path": path, "status": "compressed_existing"}
                url = f"https://raw.githubusercontent.com/{repo}/{commit}/{quote(path)}"
                rec = download(
                    client, url, target, compress=gz, size=blob["size"], git_sha=blob["sha"]
                )
            return {**rec, "path": path, "lfs": bool(pointer)}

        return run

    results = run_parallel((job(b) for b in blobs), workers=workers, desc=repo)
    name = repo.split("/")[-1].replace(".", "-")
    write_manifest(dest, name, {"repo": repo, "commit": commit, "files": results})
    raise_on_errors(results, repo)
    return results


def move_if_missing(src: Path, dst: Path) -> None:
    if src.exists() and not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src, dst)
