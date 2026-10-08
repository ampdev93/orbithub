#!/usr/bin/env python3
"""Batch controller for new OrbitHub Internet Archive submissions.

Dry-run by default. Existing IA identifiers are never mutated here.
New items are delegated to the proven single-item scripts/upload.py path.
Verification remains a separate scripts/inventory.py pass.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

try:
    import internetarchive
except ImportError:
    internetarchive = None

from upload import (
    build_description,
    build_identifier,
    build_metadata,
    parse_nfo,
    read_nfo,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bulk OrbitHub IA submission controller.")
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path("work/sets-to-upload"),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Submit NEW items. Default is dry run.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Inspect at most this many pairs.",
    )
    return parser.parse_args()


def normalize_html(value: str) -> str:
    return value.replace("<br />", "<br>").replace("<br/>", "<br>")


def remote_names(item) -> set[str]:
    result: set[str] = set()
    for entry in item.files:
        name = entry.get("name") if isinstance(entry, dict) else getattr(entry, "name", None)
        if name:
            result.add(name)
    return result


def inspect(nfo_path: Path) -> tuple[str, str, Path, str]:
    event, fields = parse_nfo(read_nfo(nfo_path))
    identifier = build_identifier(event, fields)
    audio_path = nfo_path.with_suffix(".mp3")
    canonical_mp3 = f"{identifier}.mp3"

    if nfo_path.name != f"{identifier}.nfo":
        raise ValueError(f"non-canonical NFO filename: {nfo_path.name}")
    if not audio_path.is_file():
        raise ValueError(f"matching local MP3 missing: {audio_path}")
    if audio_path.name != canonical_mp3:
        raise ValueError(f"non-canonical MP3 filename: {audio_path.name}")

    fields = dict(fields)
    fields["filename"] = canonical_mp3
    description = build_description(event, fields)
    metadata = build_metadata(identifier, event, fields, description)

    item = internetarchive.get_item(identifier)
    if not item.exists:
        return identifier, "NEW", audio_path, str(metadata["title"])

    names = remote_names(item)
    current_title = item.metadata.get("title", "")
    current_description = item.metadata.get("description", "")

    if (
        canonical_mp3 in names
        and current_title == metadata["title"]
        and normalize_html(current_description)
        == normalize_html(str(metadata["description"]))
    ):
        return identifier, "SKIPPED", audio_path, str(metadata["title"])

    return identifier, "CONFLICT", audio_path, str(metadata["title"])


def main() -> int:
    args = parse_args()

    if internetarchive is None:
        print("ERROR: internetarchive package is not installed.", file=sys.stderr)
        return 1
    if not args.directory.is_dir():
        print(f"ERROR: directory not found: {args.directory}", file=sys.stderr)
        return 1
    if args.limit is not None and args.limit < 1:
        print("ERROR: --limit must be >= 1", file=sys.stderr)
        return 1

    files = sorted(args.directory.glob("*.nfo"))
    if args.limit is not None:
        files = files[: args.limit]
    if not files:
        print("ERROR: no NFO files found.", file=sys.stderr)
        return 1

    print("OrbitHub bulk IA controller")
    print("=" * 27)
    print(f"Mode      : {'APPLY' if args.apply else 'DRY RUN'}")
    print("Deletion  : DISABLED")
    print("Overwrite : DISABLED")
    print()

    counts = {"NEW": 0, "SKIPPED": 0, "SUBMITTED": 0, "CONFLICT": 0, "ERROR": 0}

    for nfo_path in files:
        try:
            identifier, status, audio_path, title = inspect(nfo_path)
            print(f"[{status}] {identifier}")
            print(f"  Title : {title}")

            if status == "NEW" and args.apply:
                result = subprocess.run(
                    [sys.executable, "scripts/upload.py", str(audio_path), "--upload", "--no-wait"],
                    check=False,
                )
                if result.returncode == 0:
                    status = "SUBMITTED"
                else:
                    status = "ERROR"
            elif status == "CONFLICT":
                print("  No mutation performed.")

            counts[status] += 1
        except (ValueError, OSError) as error:
            counts["ERROR"] += 1
            print(f"[ERROR] {nfo_path.stem}: {error}")
        print()

    print("Summary")
    print("-" * 27)
    for status, count in counts.items():
        print(f"{status:<10}: {count}")

    print()
    if args.apply:
        print("Run scripts/inventory.py later for read-only verification.")
    else:
        print("DRY RUN: no Internet Archive data was changed.")

    return 1 if counts["CONFLICT"] or counts["ERROR"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
