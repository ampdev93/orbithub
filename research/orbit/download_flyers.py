#!/usr/bin/env python3
"""Collect Orbit flyers, preserving downloaded bytes without image modification.

Requires only Python standard library. Run from repository root:
  python3 research/orbit/download_flyers.py
"""
import csv
import hashlib
import html
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "downloads"
MANIFEST = ROOT / "downloads.csv"
OSA = "https://www.oldskoolanthems.com/media/categories/orbit.87/"
PHAT = "https://www.phatmedia.co.uk/flyers/event/"
HEADERS = {"User-Agent": "OrbitHub preservation research (manual archival use; contact site for removal)", "Accept": "text/html,image/*"}
PAUSE = 1.0
MAX_BYTES = 20 * 1024 * 1024

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("a", "img"):
            value = a.get("href") if tag == "a" else a.get("src")
            if value:
                self.links.append(html.unescape(value))

def fetch(url):
    request = Request(url, headers=HEADERS)
    with urlopen(request, timeout=20) as response:
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("download exceeds 20MB: " + url)
        return raw, response.headers.get("Content-Type", "")

def links(page, base):
    parser = Links()
    parser.feed(page.decode("utf-8", "replace"))
    return [urljoin(base, x) for x in parser.links]

def osa_candidates():
    pages = [OSA, OSA + "page-2"]
    item_pages = set()
    for url in pages:
        try:
            body, _ = fetch(url)
            for x in links(body, url):
                if re.search(r"/media/[^/]+\.\d+/?$", urlparse(x).path) and "/categories/" not in x:
                    item_pages.add(x)
            print("OSA index:", url, "entries:", len(item_pages))
        except (HTTPError, URLError, TimeoutError) as exc:
            print("ERROR index", url, exc)
        time.sleep(PAUSE)
    for url in sorted(item_pages):
        try:
            body, _ = fetch(url)
            candidates = [x for x in links(body, url) if re.search(r"/media/.+/full(?:\?|$)", x)]
            yield from (("oldskoolanthems", url, x) for x in sorted(set(candidates)))
        except (HTTPError, URLError, TimeoutError) as exc:
            print("ERROR item", url, exc)
        time.sleep(PAUSE)

def phat_candidates():
    # Known Orbit-labelled Phatmedia slug family. Each is checked by title/venue.
    for n in range(1, 40):
        url = PHAT + "orbit-flyer" + str(n)
        try:
            body, _ = fetch(url)
            page = body.decode("utf-8", "replace").lower()
            if "the orbit" not in page or "afterdark" not in page:
                continue
            images = sorted({x for x in links(body, url)
                             if "phatmedia-production-public.s3.eu-west-1.amazonaws.com/events/" in x
                             and "/thumbs/" not in x})
            for x in images:
                yield ("phatmedia", url, x)
        except HTTPError as exc:
            if exc.code != 404:
                print("ERROR Phatmedia", url, exc)
        except (URLError, TimeoutError) as exc:
            print("ERROR Phatmedia", url, exc)
        time.sleep(PAUSE)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    existing = {}
    if MANIFEST.exists():
        with MANIFEST.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing[row["image_url"]] = row
    known_hashes = {r["sha256"] for r in existing.values() if r.get("sha256")}
    collected = dict(existing)
    for provider, page, image_url in list(osa_candidates()) + list(phat_candidates()):
        if image_url in collected and collected[image_url]["status"] == "saved":
            continue
        status, filename, digest, detail = "error", "", "", ""
        try:
            raw, mime = fetch(image_url)
            if "image/" not in mime.lower() and not raw.startswith((b"\xff\xd8", b"\x89PNG", b"RIFF", b"GIF8")):
                raise ValueError("not an image: " + mime)
            digest = hashlib.sha256(raw).hexdigest()
            suffix = Path(urlparse(image_url).path).suffix.lower()
            if suffix not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                suffix = ".jpg" if raw.startswith(b"\xff\xd8") else ".bin"
            filename = provider + "-" + digest[:20] + suffix
            target = OUT / filename
            if digest not in known_hashes:
                target.write_bytes(raw)
                known_hashes.add(digest)
            status = "saved"
            detail = str(len(raw)) + " bytes"
            print("SAVED", filename, page)
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            detail = str(exc)
            print("ERROR image", image_url, detail)
        collected[image_url] = dict(provider=provider, source_page=page, image_url=image_url,
                                    filename=filename, sha256=digest, status=status, detail=detail)
        # Save after every image so interruptions preserve a resumable manifest.
        with MANIFEST.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["provider", "source_page", "image_url", "filename", "sha256", "status", "detail"])
            writer.writeheader()
            writer.writerows(collected.values())
        time.sleep(PAUSE)
    print("Completed. Images:", sum(x["status"] == "saved" for x in collected.values()), "Manifest:", MANIFEST)

if __name__ == "__main__":
    main()
