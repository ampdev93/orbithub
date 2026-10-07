#!/usr/bin/env python3
"""One-time bulk migration of existing OrbitHub Internet Archive descriptions.

Scans work/sets-to-upload/*.nfo, derives the canonical IA identifier from each
NFO, matches that identifier to an existing IA item, discovers the actual MP3
filename already stored in that item, and rewrites only the IA description
using the normalized OrbitHub format.

Default behaviour is a dry run. Use --apply to write changes.

This script is intentionally for one-time migration of existing IA items.
"""

from __future__ import annotations

import argparse
import difflib
import sys
import time
from pathlib import Path

try:
    import internetarchive
except ImportError:
    internetarchive = None

from upload import build_description, build_identifier, parse_nfo, read_nfo


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bulk-normalize descriptions for existing OrbitHub IA items."
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path("work/sets-to-upload"),
        help="Directory containing matching .nfo files.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write description changes to Internet Archive.",
    )
    return parser.parse_args()


def normalize_html(value: str) -> str:
    return value.replace("<br />", "<br>").replace("<br/>", "<br>")


def meaningful_diff(current: str, desired: str) -> list[str]:
    return list(
        difflib.unified_diff(
            normalize_html(current).splitlines(),
            normalize_html(desired).splitlines(),
            fromfile="current IA description",
            tofile="normalized description",
            lineterm="",
        )
    )


def remote_mp3_names(item) -> list[str]:
    names: list[str] = []

    for entry in item.files:
        if isinstance(entry, dict):
            name = entry.get("name")
        else:
            name = getattr(entry, "name", None)

        if name and name.lower().endswith(".mp3"):
            names.append(name)

    return sorted(names)


def verify_description(identifier: str, desired: str) -> bool:
    attempts = 12
    delay = 10

    for attempt in range(1, attempts + 1):
        item = internetarchive.get_item(identifier)
        current = item.metadata.get("description", "")

        if normalize_html(current) == normalize_html(desired):
            return True

        if attempt < attempts:
            print(
                f"    waiting for IA metadata refresh ({attempt}/{attempts})..."
            )
            time.sleep(delay)

    return False


def process_nfo(nfo_path: Path, apply: bool) -> tuple[str, str]:
    event, fields = parse_nfo(read_nfo(nfo_path))
    identifier = build_identifier(event, fields)

    item = internetarchive.get_item(identifier)
    if not item.exists:
        return identifier, "not found"

    mp3s = remote_mp3_names(item)
    if len(mp3s) != 1:
        return identifier, f"ambiguous MP3 count: {len(mp3s)}"

    # Existing IA items may use the older filename format. For description
    # migration, describe the file that is actually present on IA.
    fields["filename"] = mp3s[0]
    desired = build_description(event, fields)
    current = item.metadata.get("description", "")
    diff = meaningful_diff(current, desired)

    print(identifier)
    print(f"  NFO       : {nfo_path.name}")
    print(f"  IA MP3    : {mp3s[0]}")

    if not diff:
        print("  Status    : already normalized")
        return identifier, "unchanged"

    print("  Status    : needs update")
    for line in diff:
        print(f"  {line}")

    if not apply:
        return identifier, "would update"

    print("  Applying description update...")
    result = item.modify_metadata({"description": desired})

    status_code = result.get("status_code") if isinstance(result, dict) else None
    if status_code is not None and not (200 <= int(status_code) < 300):
        return identifier, f"update failed: {result}"

    if not verify_description(identifier, desired):
        return identifier, "verification timed out"

    print("  Verified")
    return identifier, "updated"


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

    nfo_files = sorted(args.directory.glob("*.nfo"))
    if not nfo_files:
        print(f"ERROR: no .nfo files found in {args.directory}", file=sys.stderr)
        return 1

    print("OrbitHub IA description migration")
    print("=" * 33)
    print(f"Directory : {args.directory}")
    print(f"Mode      : {'APPLY' if args.apply else 'DRY RUN'}")
    print()

    results: list[tuple[str, str]] = []

    for nfo_path in nfo_files:
        try:
            result = process_nfo(nfo_path, args.apply)
        except (ValueError, OSError) as error:
            result = (nfo_path.stem, f"error: {error}")

        results.append(result)
        print()

    print("Summary")
    print("-" * 33)
    for identifier, status in results:
        print(f"{identifier}: {status}")

    failures = [
        status for _, status in results
        if status.startswith("error")
        or status.startswith("ambiguous")
        or status.startswith("update failed")
        or status == "verification timed out"
    ]

    if not args.apply:
        print()
        print("DRY RUN: nothing changed. Add --apply after reviewing the matches.")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
