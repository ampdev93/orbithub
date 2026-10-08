#!/usr/bin/env python3
"""Extract OrbitHub set ZIPs into normalized MP3/NFO pairs.

Source:
    work/sets-to-unzip/*.zip

Destination:
    work/sets-to-upload/

Each ZIP must contain exactly:
    - one .mp3 file
    - one release.nfo file

The MP3 and NFO are renamed to the canonical OrbitHub basename derived
from the NFO metadata:
    orbit-YYYYMMDD-N-dj-name.mp3
    orbit-YYYYMMDD-N-dj-name.nfo

Default behaviour is a dry run. Use --apply to write files.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from upload import build_identifier, parse_nfo, read_nfo


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract OrbitHub ZIP archives into normalized MP3/NFO pairs."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("work/sets-to-unzip"),
        help="Directory containing ZIP archives.",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path("work/sets-to-upload"),
        help="Destination directory for extracted MP3/NFO pairs.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write files. Without this flag only show planned actions.",
    )
    return parser.parse_args()


def zip_members(archive: zipfile.ZipFile) -> tuple[list[zipfile.ZipInfo], list[zipfile.ZipInfo]]:
    mp3s = []
    nfos = []

    for member in archive.infolist():
        if member.is_dir():
            continue

        name = Path(member.filename).name
        suffix = Path(name).suffix.lower()

        if suffix == ".mp3":
            mp3s.append(member)
        elif name.lower() == "release.nfo":
            nfos.append(member)

    return mp3s, nfos


def validate_target(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"destination already exists: {path}")


def process_zip(zip_path: Path, dest: Path, apply: bool) -> tuple[str, str]:
    with zipfile.ZipFile(zip_path) as archive:
        mp3s, nfos = zip_members(archive)

        if len(mp3s) != 1:
            raise ValueError(
                f"{zip_path.name}: expected exactly 1 MP3, found {len(mp3s)}"
            )

        if len(nfos) != 1:
            raise ValueError(
                f"{zip_path.name}: expected exactly 1 release.nfo, found {len(nfos)}"
            )

        mp3_member = mp3s[0]
        nfo_member = nfos[0]

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            nfo_temp = tmp / "release.nfo"

            with archive.open(nfo_member) as src, nfo_temp.open("wb") as out:
                shutil.copyfileobj(src, out)

            event, fields = parse_nfo(read_nfo(nfo_temp))
            basename = build_identifier(event, fields)
            mp3_name = f"{basename}.mp3"
            nfo_name = f"{basename}.nfo"

            mp3_target = dest / mp3_name
            nfo_target = dest / nfo_name

            validate_target(mp3_target)
            validate_target(nfo_target)

            original_mp3_name = Path(mp3_member.filename).name

            print(f"{zip_path.name}")
            print(f"  MP3: {original_mp3_name} -> {mp3_name}")
            print(f"  NFO: release.nfo -> {nfo_name}")

            if not apply:
                return mp3_name, nfo_name

            dest.mkdir(parents=True, exist_ok=True)

            mp3_temp = tmp / original_mp3_name

            with archive.open(mp3_member) as src, mp3_temp.open("wb") as out:
                shutil.copyfileobj(src, out)

            shutil.move(str(mp3_temp), mp3_target)
            shutil.move(str(nfo_temp), nfo_target)

        return mp3_name, nfo_name


def main() -> int:
    args = parse_args()

    if not args.source.is_dir():
        print(f"ERROR: source directory not found: {args.source}", file=sys.stderr)
        return 1

    zip_files = sorted(args.source.glob("*.zip"))

    if not zip_files:
        print(f"ERROR: no ZIP files found in {args.source}", file=sys.stderr)
        return 1

    print("OrbitHub bulk ZIP extraction")
    print("=" * 28)
    print(f"Source      : {args.source}")
    print(f"Destination : {args.dest}")
    print(f"Mode        : {'APPLY' if args.apply else 'DRY RUN'}")
    print()

    errors: list[str] = []
    processed = 0

    for zip_path in zip_files:
        try:
            process_zip(zip_path, args.dest, args.apply)
            processed += 1
        except (zipfile.BadZipFile, ValueError, FileExistsError, OSError) as error:
            errors.append(str(error))
            print(f"  ERROR: {error}")

        print()

    print(f"ZIPs checked : {len(zip_files)}")
    print(f"Ready        : {processed}")
    print(f"Errors       : {len(errors)}")

    if errors:
        print()
        print("No unsafe overwrites were performed for failed entries.")
        return 1

    if not args.apply:
        print()
        print("DRY RUN: nothing extracted. Add --apply after reviewing the plan.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
