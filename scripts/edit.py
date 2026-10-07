#!/usr/bin/env python3
"""Preview or update the Internet Archive description for one OrbitHub item.

The audio filename determines the matching .nfo file and IA identifier.

Default behaviour is a dry run. Nothing is changed unless --apply is supplied.

Usage:
    python3 scripts/edit.py "/path/to/audio.mp3"
    python3 scripts/edit.py "/path/to/audio.mp3" --apply
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

from upload import (
    build_description,
    build_identifier,
    parse_nfo,
    read_nfo,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview or update an OrbitHub Internet Archive description."
    )
    parser.add_argument("audio", type=Path, help="Audio file whose matching .nfo supplies metadata")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the normalized description to Internet Archive.",
    )
    parser.add_argument(
        "--identifier",
        help="Override the generated Internet Archive identifier.",
    )
    return parser.parse_args()


def show_diff(current: str, desired: str) -> None:
    diff = difflib.unified_diff(
        current.splitlines(),
        desired.splitlines(),
        fromfile="current IA description",
        tofile="normalized description",
        lineterm="",
    )

    output = list(diff)
    if output:
        print("\n".join(output))
    else:
        print("Description already matches the normalized format.")


def verify_description(identifier: str, desired: str) -> bool:
    attempts = 12
    delay = 10

    for attempt in range(1, attempts + 1):
        item = internetarchive.get_item(identifier)
        current = item.metadata.get("description", "")

        if current == desired:
            return True

        if attempt < attempts:
            print(
                "Metadata update accepted; waiting for Internet Archive to refresh "
                f"({attempt}/{attempts})..."
            )
            time.sleep(delay)

    return False


def main() -> int:
    args = parse_args()

    if internetarchive is None:
        print(
            "ERROR: the 'internetarchive' Python package is not installed.",
            file=sys.stderr,
        )
        return 1

    if not args.audio.is_file():
        print(f"ERROR: audio file not found: {args.audio}", file=sys.stderr)
        return 1

    nfo_path = args.audio.with_suffix(".nfo")
    if not nfo_path.is_file():
        print(f"ERROR: matching .nfo not found: {nfo_path}", file=sys.stderr)
        return 1

    try:
        text = read_nfo(nfo_path)
        event, fields = parse_nfo(text)
        fields["filename"] = args.audio.name

        identifier = args.identifier or build_identifier(event, fields)
        desired = build_description(event, fields)

        item = internetarchive.get_item(identifier)
        if not item.exists:
            print(
                f"ERROR: Internet Archive item does not exist: {identifier}",
                file=sys.stderr,
            )
            return 1

        current = item.metadata.get("description", "")

        print("Internet Archive description preview")
        print("=" * 36)
        print(f"Identifier : {identifier}")
        print(f"Audio      : {args.audio}")
        print(f"NFO        : {nfo_path}")
        print()
        show_diff(current, desired)
        print()

        if current == desired:
            return 0

        if not args.apply:
            print("DRY RUN: nothing changed. Add --apply after reviewing the diff.")
            return 0

        print(f"Updating description for {identifier}...")
        result = item.modify_metadata({"description": desired})

        status_code = result.get("status_code") if isinstance(result, dict) else None
        if status_code is not None and not (200 <= int(status_code) < 300):
            raise RuntimeError(f"Internet Archive metadata update failed: {result}")

        if not verify_description(identifier, desired):
            raise RuntimeError(
                "Metadata update was accepted, but verification timed out before "
                "Internet Archive returned the new description."
            )

        print("Description update verified.")
        print(f"Item: https://archive.org/details/{identifier}")
        return 0

    except (ValueError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
