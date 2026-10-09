#!/usr/bin/env python3
"""Batch controller for new OrbitHub Internet Archive submissions.

Dry-run by default. Existing IA identifiers are never mutated here.
New items are delegated to the proven single-item scripts/upload.py path.
Verification remains a separate scripts/inventory.py pass.
"""

from __future__ import annotations

import argparse
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
    build_metadata,
    parse_nfo,
    read_nfo,
    upload_item,
    RateLimitError,
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
    parser.add_argument(
        "--delay",
        type=int,
        default=300,
        help="Seconds to wait between successful submissions (default: 300).",
    )
    parser.add_argument(
        "--identifier",
        action="append",
        default=[],
        help="Restrict processing to this canonical identifier. Repeat for multiple items.",
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


def inspect(nfo_path: Path) -> tuple[str, str, Path, str, str, dict[str, str], dict[str, object]]:
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
        return identifier, "NEW", audio_path, str(metadata["title"]), "identifier not present on IA", fields, metadata

    names = remote_names(item)
    current_title = item.metadata.get("title", "")
    current_description = item.metadata.get("description", "")

    title_matches = current_title == metadata["title"]
    description_matches = (
        normalize_html(current_description)
        == normalize_html(str(metadata["description"]))
    )

    if canonical_mp3 in names and title_matches and description_matches:
        return (
            identifier,
            "SKIPPED",
            audio_path,
            str(metadata["title"]),
            "existing canonical IA item is complete",
            fields,
            metadata,
        )

    if not names or not canonical_mp3 in names:
        return (
            identifier,
            "PENDING",
            audio_path,
            str(metadata["title"]),
            "IA item exists but canonical MP3 is not visible yet; treat as propagation pending",
            fields,
            metadata,
        )

    return (
        identifier,
        "CONFLICT",
        audio_path,
        str(metadata["title"]),
        "existing IA item differs from canonical metadata",
        fields,
        metadata,
    )


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
    if args.delay < 0:
        print("ERROR: --delay must be >= 0", file=sys.stderr)
        return 1

    files = sorted(args.directory.glob("*.nfo"))
    if args.identifier:
        wanted = set(args.identifier)
        files = [path for path in files if path.stem in wanted]
        found = {path.stem for path in files}
        missing = sorted(wanted - found)
        if missing:
            print(
                "ERROR: requested identifier(s) not found locally: "
                + ", ".join(missing),
                file=sys.stderr,
            )
            return 1
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
    print(f"Delay     : {args.delay}s between successful submissions")
    if args.identifier:
        print(f"Selected  : {len(args.identifier)} identifier(s)")
    print()

    counts = {"NEW": 0, "SKIPPED": 0, "PENDING": 0, "SUBMITTED": 0, "CONFLICT": 0, "ERROR": 0}

    successful_submissions = 0

    for nfo_path in files:
        try:
            identifier, status, audio_path, title, note, fields, metadata = inspect(nfo_path)
            print(f"[{status}] {identifier}")
            print(f"  Title : {title}")
            print(f"  Note  : {note}")

            if status == "NEW" and args.apply:
                try:
                    upload_item(
                        identifier,
                        nfo_path,
                        audio_path,
                        fields,
                        metadata,
                        wait_for_verification=False,
                    )
                    status = "SUBMITTED"
                    successful_submissions += 1
                    remaining_candidates = files.index(nfo_path) < len(files) - 1
                    if args.delay and remaining_candidates:
                        print(f"  Throttle: waiting {args.delay}s before next item...")
                        time.sleep(args.delay)
                except RateLimitError as error:
                    status = "ERROR"
                    counts[status] += 1
                    print(f"  ERROR: {error}")
                    print("  Rate limit detected. Stopping the batch immediately.")
                    print()
                    break
                except RuntimeError as error:
                    status = "ERROR"
                    print(f"  ERROR: {error}")
            elif status in {"PENDING", "CONFLICT"}:
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
