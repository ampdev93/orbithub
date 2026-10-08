#!/usr/bin/env python3
"""Read-only inventory for OrbitHub archive items.

Implements Issue #9 step 3: inventory before changing anything.

This script never uploads, edits or deletes local or Internet Archive data.
It compares local MP3/NFO pairs, the canonical OrbitHub naming/metadata
contract, existing Internet Archive items, and content/sets.json. It also
reports website entries that have no corresponding local MP3/NFO pair.

Requires:
    pip install internetarchive
    ia configure

Usage:
    python3 scripts/inventory.py
    python3 scripts/inventory.py --directory work/sets-to-upload
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

try:
    import internetarchive
except ImportError:
    internetarchive = None

from upload import build_description, build_identifier, parse_nfo, read_nfo


STATUSES = (
    "NEW",
    "PENDING",
    "READY FOR WEBSITE",
    "SKIPPED",
    "WEBSITE ONLY",
    "MIGRATION REQUIRED",
    "CONFLICT",
    "ERROR",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only OrbitHub local/IA/website inventory."
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path("work/sets-to-upload"),
        help="Directory containing local MP3/NFO pairs.",
    )
    parser.add_argument(
        "--sets-json",
        type=Path,
        default=Path("content/sets.json"),
        help="OrbitHub website sets JSON.",
    )
    parser.add_argument(
        "--check-audio",
        action="store_true",
        help="Verify canonical direct MP3 URLs with a one-byte range GET.",
    )
    parser.add_argument(
        "--audio-timeout",
        type=float,
        default=30.0,
        help="Timeout in seconds for each direct MP3 verification request.",
    )
    return parser.parse_args()


def normalize_html(value: str) -> str:
    return value.replace("<br />", "<br>").replace("<br/>", "<br>")


def remote_file_names(item) -> list[str]:
    names: list[str] = []

    for entry in item.files:
        if isinstance(entry, dict):
            name = entry.get("name")
        else:
            name = getattr(entry, "name", None)

        if name:
            names.append(name)

    return sorted(names)


def load_website_urls(path: Path) -> dict[str, list[str]]:
    if not path.is_file():
        raise ValueError(f"sets JSON not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, list[str]] = {}

    for event in data:
        for item in event.get("sets", []):
            url = item.get("audio")
            if not url:
                continue

            parsed = urlparse(url)
            parts = [unquote(part) for part in parsed.path.split("/") if part]

            # Expected IA path:
            # /download/{identifier}/{filename}
            if len(parts) >= 3 and parts[0] == "download":
                identifier = parts[1]
                result.setdefault(identifier, []).append(url)

    return result


def check_audio_url(url: str, timeout: float) -> str:
    if not url or url == "-":
        return "not checked"

    request = Request(url, headers={"Range": "bytes=0-0"})

    try:
        with urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", None)
            if status in (200, 206):
                return f"available ({status})"
            return f"unexpected HTTP {status}"
    except Exception as error:
        return f"pending ({error})"


def report_website_only_items(
    local_identifiers: set[str],
    website_urls: dict[str, list[str]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for identifier in sorted(set(website_urls) - local_identifiers):
        urls = website_urls[identifier]
        rows.append(
            {
                "nfo": "-",
                "local_mp3": "-",
                "event": "-",
                "file": "-",
                "dj": "-",
                "identifier": identifier,
                "canonical_mp3": f"{identifier}.mp3",
                "ia_exists": True,
                "ia_mp3": "-",
                "title": "not checked",
                "title_current": "-",
                "title_expected": "-",
                "description": "not checked",
                "website": "present",
                "website_url": " | ".join(urls),
                "audio_url": "not checked",
                "status": "WEBSITE ONLY",
                "note": "existing published item is outside the current local staging set",
            }
        )

    return rows


def website_status(
    identifier: str,
    canonical_mp3: str,
    website_urls: dict[str, list[str]],
) -> tuple[str, str]:
    urls = website_urls.get(identifier, [])

    if not urls:
        return "missing", "-"

    if len(urls) > 1:
        return "conflict", " | ".join(urls)

    url = urls[0]
    path_name = unquote(urlparse(url).path.rsplit("/", 1)[-1])

    if path_name == canonical_mp3:
        return "canonical", url

    return "legacy", url


def classify(
    *,
    local_pair_ok: bool,
    local_name_canonical: bool,
    item_exists: bool,
    canonical_mp3_present: bool,
    legacy_mp3s: list[str],
    title_matches: bool,
    description_matches: bool,
    website_state: str,
) -> str:
    if not local_pair_ok or not local_name_canonical:
        return "CONFLICT"

    if not item_exists:
        return "NEW"

    if website_state == "conflict":
        return "CONFLICT"

    if (
        item_exists
        and not canonical_mp3_present
        and not legacy_mp3s
        and title_matches
        and description_matches
    ):
        return "PENDING"

    if canonical_mp3_present and title_matches and description_matches:
        if website_state == "canonical":
            return "SKIPPED"
        if website_state == "missing":
            return "READY FOR WEBSITE"

    if canonical_mp3_present or legacy_mp3s or not title_matches or not description_matches:
        return "MIGRATION REQUIRED"

    return "PENDING"


def inspect_pair(
    nfo_path: Path,
    website_urls: dict[str, list[str]],
    *,
    check_audio: bool = False,
    audio_timeout: float = 30.0,
) -> dict[str, object]:
    row: dict[str, object] = {
        "nfo": nfo_path.name,
        "local_mp3": "-",
        "event": "-",
        "file": "-",
        "dj": "-",
        "identifier": "-",
        "canonical_mp3": "-",
        "ia_exists": False,
        "ia_mp3": "-",
        "title": "-",
        "title_current": "-",
        "title_expected": "-",
        "description": "-",
        "website": "-",
        "website_url": "-",
        "audio_url": "not checked",
        "status": "ERROR",
        "note": "",
    }

    try:
        event, fields = parse_nfo(read_nfo(nfo_path))
        identifier = build_identifier(event, fields)
        canonical_mp3 = f"{identifier}.mp3"
        local_mp3 = nfo_path.with_suffix(".mp3")

        row.update(
            {
                "event": event["display_date"],
                "file": event["file_number"],
                "dj": fields["djs_file"],
                "identifier": identifier,
                "canonical_mp3": canonical_mp3,
                "local_mp3": local_mp3.name,
            }
        )

        local_pair_ok = local_mp3.is_file()
        local_name_canonical = (
            nfo_path.name == f"{identifier}.nfo"
            and local_mp3.name == canonical_mp3
        )

        if not local_pair_ok:
            row["note"] = "matching local MP3 missing"
        elif not local_name_canonical:
            row["note"] = "local basename is not canonical"

        item = internetarchive.get_item(identifier)
        item_exists = bool(item.exists)
        row["ia_exists"] = item_exists

        canonical_present = False
        legacy_mp3s: list[str] = []
        title_matches = False
        description_matches = False

        if item_exists:
            names = remote_file_names(item)
            mp3_names = [name for name in names if name.lower().endswith(".mp3")]
            canonical_present = canonical_mp3 in mp3_names
            legacy_mp3s = [name for name in mp3_names if name != canonical_mp3]
            row["ia_mp3"] = ", ".join(mp3_names) if mp3_names else "-"

            desired_title = (
                f"The Orbit - {event['display_date']} - "
                f"File {event['file_number']} of {event['file_total']} - {fields['djs_file']}"
            )
            desired_fields = dict(fields)
            desired_fields["filename"] = canonical_mp3
            desired = build_description(event, desired_fields)

            current_title = item.metadata.get("title", "")
            current_description = item.metadata.get("description", "")
            title_matches = current_title == desired_title
            row["title_current"] = current_title or "-"
            row["title_expected"] = desired_title
            description_matches = (
                normalize_html(current_description) == normalize_html(desired)
            )
            row["title"] = "canonical" if title_matches else "needs update"
            row["description"] = "canonical" if description_matches else "needs update"
        else:
            row["title"] = "not applicable"
            row["title_current"] = "-"
            row["title_expected"] = "-"
            row["description"] = "not applicable"

        web_state, web_url = website_status(
            identifier, canonical_mp3, website_urls
        )
        row["website"] = web_state
        row["website_url"] = web_url
        if check_audio and item_exists and canonical_present:
            canonical_url = (
                f"https://archive.org/download/{identifier}/{canonical_mp3}"
            )
            row["audio_url"] = check_audio_url(canonical_url, audio_timeout)

        row["status"] = classify(
            local_pair_ok=local_pair_ok,
            local_name_canonical=local_name_canonical,
            item_exists=item_exists,
            canonical_mp3_present=canonical_present,
            legacy_mp3s=legacy_mp3s,
            title_matches=title_matches,
            description_matches=description_matches,
            website_state=web_state,
        )

        if (
            row["status"] == "MIGRATION REQUIRED"
            and not row["note"]
            and legacy_mp3s
            and not canonical_present
        ):
            row["note"] = "IA contains legacy MP3 filename only"

        return row

    except Exception as error:  # inventory must report item failures, not abort batch
        row["status"] = "ERROR"
        row["note"] = str(error)
        return row


def print_row(row: dict[str, object]) -> None:
    print(f"[{row['status']}] {row['identifier']}")
    print(f"  Event       : {row['event']}")
    print(f"  File        : {row['file']}")
    print(f"  DJ          : {row['dj']}")
    print(f"  Local MP3   : {row['local_mp3']}")
    print(f"  Local NFO   : {row['nfo']}")
    print(f"  Canonical   : {row['canonical_mp3']}")
    print(f"  IA exists   : {'yes' if row['ia_exists'] else 'no'}")
    print(f"  IA MP3      : {row['ia_mp3']}")
    print(f"  Title       : {row['title']}")
    if row["title"] == "needs update":
        print(f"  Title now   : {row['title_current']}")
        print(f"  Title want  : {row['title_expected']}")
    print(f"  Description : {row['description']}")
    print(f"  Website     : {row['website']}")
    print(f"  Website URL : {row['website_url']}")
    print(f"  Audio URL   : {row['audio_url']}")
    if row["note"]:
        print(f"  Note        : {row['note']}")
    print()


def main() -> int:
    args = parse_args()

    if internetarchive is None:
        print(
            "ERROR: the 'internetarchive' Python package is not installed.",
            file=sys.stderr,
        )
        return 1

    if not args.directory.is_dir():
        print(f"ERROR: directory not found: {args.directory}", file=sys.stderr)
        return 1

    try:
        website_urls = load_website_urls(args.sets_json)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    nfo_files = sorted(args.directory.glob("*.nfo"))
    if not nfo_files:
        print(f"ERROR: no .nfo files found in {args.directory}", file=sys.stderr)
        return 1

    print("OrbitHub archive inventory")
    print("=" * 27)
    print(f"Local source : {args.directory}")
    print(f"Website data : {args.sets_json}")
    print("Mode         : READ ONLY")
    print(f"Audio check  : {'enabled' if args.check_audio else 'disabled'}")
    print()

    rows = [
        inspect_pair(
            path,
            website_urls,
            check_audio=args.check_audio,
            audio_timeout=args.audio_timeout,
        )
        for path in nfo_files
    ]

    local_identifiers = {
        str(row["identifier"])
        for row in rows
        if row["identifier"] and row["identifier"] != "-"
    }
    rows.extend(report_website_only_items(local_identifiers, website_urls))

    for row in rows:
        print_row(row)

    counts = {status: 0 for status in STATUSES}
    for row in rows:
        counts[str(row["status"])] = counts.get(str(row["status"]), 0) + 1

    print("Summary")
    print("-" * 27)
    print(f"Items              : {len(rows)}")
    for status in STATUSES:
        print(f"{status:<19}: {counts.get(status, 0)}")

    unresolved = counts.get("CONFLICT", 0) + counts.get("ERROR", 0)

    print()
    print("READ ONLY: no local or Internet Archive data was changed.")
    if args.check_audio:
        available = sum(
            str(row.get("audio_url", "")).startswith("available")
            for row in rows
        )
        pending = sum(
            str(row.get("audio_url", "")).startswith(("pending", "unexpected"))
            for row in rows
        )
        print(f"Audio available      : {available}/{len(rows)}")
        print(f"Audio verify pending : {pending}")

    if unresolved:
        print(
            "Inventory contains unresolved CONFLICT/ERROR items. "
            "Do not proceed with archive mutation."
        )
        return 1

    print("Inventory has no unresolved conflicts/errors.")
    if counts.get("PENDING", 0):
        print("Some IA submissions are still propagating; verify them again later.")
    if counts.get("READY FOR WEBSITE", 0):
        print("Some IA items are verified and ready to be added to content/sets.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
