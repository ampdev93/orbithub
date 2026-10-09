#!/usr/bin/env python3
"""Extract OrbitHub set ZIPs into normalized MP3/NFO pairs.

Source:
    work/sets-to-unzip/*.zip

Destination:
    work/sets-to-upload/

Each ZIP must contain exactly:
    - one .mp3 file
    - one .nfo file

Any other file in the ZIP is treated as an error.

The MP3 and NFO are renamed to the canonical OrbitHub basename derived
from the NFO metadata:
    orbit-YYYYMMDD-N-dj-name.mp3
    orbit-YYYYMMDD-N-dj-name.nfo

Default behaviour is a dry run. Use --apply to write files.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from upload import build_identifier, parse_nfo, read_nfo, slugify


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


def zip_members(
    archive: zipfile.ZipFile,
) -> tuple[list[zipfile.ZipInfo], list[zipfile.ZipInfo], list[zipfile.ZipInfo]]:
    mp3s = []
    nfos = []
    others = []

    for member in archive.infolist():
        if member.is_dir():
            continue

        name = Path(member.filename).name
        suffix = Path(name).suffix.lower()

        if suffix == ".mp3":
            mp3s.append(member)
        elif suffix == ".nfo":
            nfos.append(member)
        else:
            others.append(member)

    return mp3s, nfos, others


def build_unverified_identifier(text: str) -> str:
    """Build a deterministic identifier for legacy/unverified NFO formats.

    Supported banners:
      TheOrbituary presents... ARTIST live @ The Orbit, DD-MM-YY, Side A.
      TheOrbituary presents... ARTIST live @ The Orbit, DD-MM-YY.
      TheOrbituary presents... ARTIST live @ The Orbit, England, YYYY.

    Exact dates are preserved. Year-only sources remain year-only; no date is
    invented. Unsupported/ambiguous banners fail closed.
    """
    banner = re.search(
        r"TheOrbituary presents\.\.\.\s*(.+?)\s+live\s+@\s+The Orbit,\s*(?:England,\s*)?"
        r"(?:(\d{2}-\d{2}-\d{2})(?:,\s*Side\s+([A-Za-z0-9]+))?|(\d{4}))\.",
        text,
        flags=re.IGNORECASE,
    )
    if not banner:
        raise ValueError("Could not parse supported unverified NFO banner.")

    artist = re.sub(r"\s+", " ", banner.group(1)).strip()
    exact_date = banner.group(2)
    side = banner.group(3)
    year_only = banner.group(4)

    artist_slug = slugify(artist)
    if not artist_slug:
        raise ValueError("Could not derive artist slug from unverified NFO banner.")

    if exact_date:
        day, month, year = (int(part) for part in exact_date.split("-"))
        full_year = 1900 + year if year >= 91 else 2000 + year
        date_key = f"{full_year:04d}{month:02d}{day:02d}"
        side_part = f"-{slugify(side)}" if side else ""
        return f"orbit-unverified-{date_key}{side_part}-{artist_slug}"

    return f"orbit-unverified-{year_only}-{artist_slug}"


def validate_target(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"destination already exists: {path}")


def process_zip(zip_path: Path, dest: Path, apply: bool) -> tuple[str, str]:
    with zipfile.ZipFile(zip_path) as archive:
        mp3s, nfos, others = zip_members(archive)

        if others:
            other_names = ", ".join(
                Path(member.filename).name for member in others
            )
            raise ValueError(
                f"{zip_path.name}: unexpected file(s): {other_names}"
            )

        if len(mp3s) != 1:
            raise ValueError(
                f"{zip_path.name}: expected exactly 1 MP3, found {len(mp3s)}"
            )

        if len(nfos) != 1:
            raise ValueError(
                f"{zip_path.name}: expected exactly 1 NFO, found {len(nfos)}"
            )

        mp3_member = mp3s[0]
        nfo_member = nfos[0]

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            original_nfo_name = Path(nfo_member.filename).name
            nfo_temp = tmp / original_nfo_name

            with archive.open(nfo_member) as src, nfo_temp.open("wb") as out:
                shutil.copyfileobj(src, out)

            nfo_text = read_nfo(nfo_temp)
            try:
                event, fields = parse_nfo(nfo_text)
                basename = build_identifier(event, fields)
            except ValueError as canonical_error:
                try:
                    basename = build_unverified_identifier(nfo_text)
                except ValueError:
                    raise canonical_error
            mp3_name = f"{basename}.mp3"
            nfo_name = f"{basename}.nfo"

            mp3_target = dest / mp3_name
            nfo_target = dest / nfo_name

            validate_target(mp3_target)
            validate_target(nfo_target)

            original_mp3_name = Path(mp3_member.filename).name

            print(f"{zip_path.name}")
            print(f"  MP3: {original_mp3_name} -> {mp3_name}")
            print(f"  NFO: {original_nfo_name} -> {nfo_name}")

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
