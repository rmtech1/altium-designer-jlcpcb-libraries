"""HTTP download with conditional requests so unchanged data is not re-fetched."""

from __future__ import annotations

import json
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "jlc-altium (+https://github.com/rmtech1/altium-designer-jlcpcb-libraries)"


def fetch(url: str, dest: Path, quiet: bool = False) -> bool:
    """Download url to dest. Returns True if dest changed.

    The ETag/Last-Modified of the previous download is kept next to dest, so a
    nightly run against an unchanged upstream costs one small request.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    meta_path = dest.with_name(dest.name + ".meta.json")
    meta = {}
    if dest.exists() and meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
        except ValueError:
            meta = {}

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    if meta.get("url") == url:
        if meta.get("etag"):
            req.add_header("If-None-Match", meta["etag"])
        if meta.get("last_modified"):
            req.add_header("If-Modified-Since", meta["last_modified"])

    try:
        resp = urllib.request.urlopen(req, timeout=60)
    except urllib.error.HTTPError as e:
        if e.code == 304:
            if not quiet:
                print(f"  up to date: {url}")
            return False
        raise

    tmp = dest.with_name(dest.name + ".part")
    total = int(resp.headers.get("Content-Length") or 0)
    done = 0
    with resp, open(tmp, "wb") as out:
        while chunk := resp.read(1 << 20):
            out.write(chunk)
            done += len(chunk)
            if not quiet and total:
                sys.stdout.write(f"\r  downloading {done / 1e6:.0f}/{total / 1e6:.0f} MB")
                sys.stdout.flush()
    if not quiet and total:
        sys.stdout.write("\n")
    shutil.move(tmp, dest)

    meta_path.write_text(json.dumps({
        "url": url,
        "etag": resp.headers.get("ETag"),
        "last_modified": resp.headers.get("Last-Modified"),
    }))
    return True
