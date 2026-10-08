#!/usr/bin/env python3
"""Safely migrate existing OrbitHub Internet Archive items.

Implements Issue #9 step 5.

Default behaviour is dry-run only. Nothing is uploaded or edited unless
--apply is supplied. This script never deletes Internet Archive files.

For each local canonical MP3/NFO pair:
- derive canonical identifier
- inspect existing IA item
- skip already-canonical items
- submit canonical MP3 if only a legacy MP3 exists
- submit canonical title and description only if needed
- continue immediately without waiting for IA propagation
- retain all legacy MP3 files

Verification is performed separately with scripts/inventory.py.

Usage:
    python3 scripts/migrate_ia.py
    python3 scripts/migrate_ia.py --apply
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import requests

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
        description="Safely migrate existing OrbitHub IA items."
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path("work/sets-to-upload"),
        help="Directory containing canonical MP3/NFO pairs.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform uploads/metadata updates. Default is dry run.",
    )
    return parser.parse_args()


def normalize_html(value: str) -> str:
    return value.replace("<br />", "<br>").replace("<br/>", "<br>")


def remote_file_names(item) -> set[str]:
    names: set[str] = set()
    for entry in item.files:
        if isinstance(entry, dict):
            name = entry.get("name")
        else:
            name = getattr(entry, "name", None)
        if name:
            names.add(name)
    return names


def upload_canonical_mp3(item, audio_path: Path, filename: str) -> None:
    retries = 5

    for attempt in range(1, retries + 1):
        try:
            response = item.upload_file(
                str(audio_path),
                key=filename,
                queue_derive=False,
                verify=True,
                retries=10,
                verbose=True,
            )
            response.raise_for_status()
            return
        except requests.exceptions.RequestException as error:
            if attempt == retries:
                raise RuntimeError(
                    f"upload failed after {retries} connection retries: {error}"
                ) from error

            delay = 30
            print(
                f"    IA connection failed ({attempt}/{retries}); "
                f"retrying in {delay} seconds..."
            )
            time.sleep(delay)


def inspect_item(nfo_path: Path) -> dict[str, object]:
    event, fields = parse_nfo(read_nfo(nfo_path))
    identifier = build_identifier(event, fields)
    canonical_mp3 = f"{identifier}.mp3"
    audio_path = nfo_path.with_suffix(".mp3")

    if nfo_path.name != f"{identifier}.nfo":
        raise ValueError(f"non-canonical NFO filename: {nfo_path.name}")

    if not audio_path.is_file():
        raise ValueError(f"matching local MP3 missing: {audio_path}")

    if audio_path.name != canonical_mp3:
        raise ValueError(f"non-canonical MP3 filename: {audio_path.name}")

    item = internetarchive.get_item(identifier)
    if not item.exists:
        raise ValueError(
            f"existing IA item not found for migration: {identifier}"
        )

    names = remote_file_names(item)
    mp3_names = sorted(name for name in names if name.lower().endswith(".mp3"))
    canonical_present = canonical_mp3 in mp3_names
    legacy_mp3s = [name for name in mp3_names if name != canonical_mp3]

    desired_title = (
        f"The Orbit - {event['display_date']} - "
        f"File {event['file_number']} of {event['file_total']} - {fields['djs_file']}"
    )
    desired_fields = dict(fields)
    desired_fields["filename"] = canonical_mp3
    desired_description = build_description(event, desired_fields)

    current_title = item.metadata.get("title", "")
    current_description = item.metadata.get("description", "")
    title_matches = current_title == desired_title
    description_matches = (
        normalize_html(current_description)
        == normalize_html(desired_description)
    )

    if canonical_present and title_matches and description_matches:
        action = "SKIP"
    elif canonical_present:
        action = "UPDATE METADATA"
    elif legacy_mp3s:
        action = "UPLOAD + UPDATE METADATA"
    else:
        raise ValueError(
            "IA item exists but contains no canonical or legacy MP3 file"
        )

    return {
        "identifier": identifier,
        "audio_path": audio_path,
        "canonical_mp3": canonical_mp3,
        "legacy_mp3s": legacy_mp3s,
        "canonical_present": canonical_present,
        "title_matches": title_matches,
        "description_matches": description_matches,
        "desired_title": desired_title,
        "desired_description": desired_description,
        "action": action,
    }


def print_plan(info: dict[str, object]) -> None:
    print(info["identifier"])
    print(f"  Local MP3 : {info['audio_path']}")
    print(f"  Canonical : {info['canonical_mp3']}")
    print(
        "  IA legacy : "
        + (", ".join(info["legacy_mp3s"]) if info["legacy_mp3s"] else "-")
    )
    print(
        f"  IA canonical MP3 : "
        f"{'yes' if info['canonical_present'] else 'no'}"
    )
    print(
        f"  Title            : "
        f"{'canonical' if info['title_matches'] else 'needs update'}"
    )
    print(
        f"  Description      : "
        f"{'canonical' if info['description_matches'] else 'needs update'}"
    )
    print(f"  Action           : {info['action']}")
    print("  Delete legacy    : no")


def apply_item(info: dict[str, object]) -> str:
    identifier = str(info["identifier"])
    canonical_mp3 = str(info["canonical_mp3"])
    audio_path = Path(info["audio_path"])
    desired_title = str(info["desired_title"])
    desired_description = str(info["desired_description"])

    if info["action"] == "SKIP":
        return "SKIPPED"

    item = internetarchive.get_item(identifier)

    if not info["canonical_present"]:
        print("  Uploading canonical MP3...")
        upload_canonical_mp3(item, audio_path, canonical_mp3)
        print("  Canonical MP3 submission accepted.")

    refreshed = internetarchive.get_item(identifier)
    current_title = refreshed.metadata.get("title", "")
    current_description = refreshed.metadata.get("description", "")

    metadata_update: dict[str, str] = {}

    if current_title != desired_title:
        metadata_update["title"] = desired_title

    if normalize_html(current_description) != normalize_html(desired_description):
        metadata_update["description"] = desired_description

    if metadata_update:
        changed = " + ".join(metadata_update.keys())
        print(f"  Updating {changed}...")
        result = refreshed.modify_metadata(metadata_update)

        try:
            result.raise_for_status()
        except requests.exceptions.RequestException as error:
            status_code = getattr(result, "status_code", "unknown")
            response_text = getattr(result, "text", "")
            if response_text:
                response_text = response_text.strip().replace("\n", " ")
                if len(response_text) > 500:
                    response_text = response_text[:500] + "..."
            detail = f"HTTP {status_code}"
            if response_text:
                detail += f": {response_text}"
            raise RuntimeError(
                f"metadata update failed ({detail})"
            ) from error

        print(f"  Metadata submission accepted (HTTP {result.status_code}).")

    return "SUBMITTED"


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

    print("OrbitHub IA migration")
    print("=" * 21)
    print(f"Directory : {args.directory}")
    print(f"Mode      : {'APPLY' if args.apply else 'DRY RUN'}")
    print("Deletion  : DISABLED")
    print()

    results: list[tuple[str, str]] = []

    for nfo_path in nfo_files:
        try:
            info = inspect_item(nfo_path)
            print_plan(info)

            if args.apply:
                status = apply_item(info)
            else:
                status = str(info["action"])

            results.append((str(info["identifier"]), status))

        except (ValueError, RuntimeError, OSError) as error:
            results.append((nfo_path.stem, f"ERROR: {error}"))
            print(f"{nfo_path.stem}")
            print(f"  ERROR: {error}")

        print()

    print("Summary")
    print("-" * 21)

    for identifier, status in results:
        print(f"{identifier}: {status}")

    errors = [status for _, status in results if status.startswith("ERROR")]

    print()
    if args.apply:
        print("No legacy IA files were deleted.")
        print("Run scripts/inventory.py later to verify IA propagation.")
    else:
        print("DRY RUN: no Internet Archive data was changed.")

    if errors:
        print("Errors detected. Do not proceed until resolved.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
