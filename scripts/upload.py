#!/usr/bin/env python3
"""Prepare and upload one OrbitHub audio item to Internet Archive.

Default behaviour is a dry run. Nothing is uploaded unless --upload is supplied.

Requires:
    pip install internetarchive
    ia configure

Usage:
    python3 scripts/upload.py release.nfo "/path/to/audio.mp3"
    python3 scripts/upload.py release.nfo "/path/to/audio.mp3" --upload
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

try:
    import internetarchive
except ImportError:
    internetarchive = None


FIELD_MAP = {
    "Filename": "filename",
    "Status": "status",
    "Release Date": "release_date",
    "File Size": "file_size",
    "Length": "length",
    "Encoded by": "encoded_by",
    "Type": "type",
    "Audio Format": "audio_format",
    "Bitrate": "bitrate",
    "Hz": "sample_rate",
    "Channels": "channels",
    "Source": "source",
    "Tapes/files in set": "tapes_files",
    "DJ(s) for this file": "djs_file",
    "DJ(s) for set": "djs_set",
    "Notes": "notes",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare or upload one OrbitHub set to Internet Archive."
    )
    parser.add_argument("nfo", type=Path, help="Original release .nfo file")
    parser.add_argument("audio", type=Path, help="Audio file to upload")
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Perform the upload. Without this flag the script only previews.",
    )
    parser.add_argument(
        "--identifier",
        help="Override the generated Internet Archive identifier.",
    )
    return parser.parse_args()


def read_nfo(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def clean_wrapped_value(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_nfo(text: str) -> tuple[dict[str, str], dict[str, str]]:
    banner_match = re.search(
        r"Live sets from The Orbit,\s*(\d{2}-\d{2}-\d{2}),\s*File\s+(\d+)\s+of\s+(\d+)\.",
        text,
        flags=re.IGNORECASE,
    )
    if not banner_match:
        raise ValueError("Could not parse event date/file number from .nfo banner.")

    event = {
        "display_date": banner_match.group(1),
        "file_number": banner_match.group(2),
        "file_total": banner_match.group(3),
    }

    lines = text.splitlines()
    fields: dict[str, str] = {}
    current_key: str | None = None
    current_value: list[str] = []

    def save_current() -> None:
        nonlocal current_key, current_value
        if current_key:
            fields[current_key] = clean_wrapped_value(" ".join(current_value))
        current_key = None
        current_value = []

    for line in lines:
        match = re.match(r"^([^.:][^:]*?)\.+:\s*(.*)$", line)
        if match:
            save_current()
            raw_key = match.group(1).strip()

            if raw_key == "Archive Name":
                continue
            if raw_key in FIELD_MAP:
                current_key = FIELD_MAP[raw_key]
                current_value = [match.group(2).strip()]
            continue

        if current_key and re.match(r"^\s{5,}\S", line):
            current_value.append(line.strip())
            continue

        if current_key:
            save_current()

        if "Site Information" in line:
            break

    save_current()

    required = [
        "filename",
        "status",
        "release_date",
        "file_size",
        "length",
        "audio_format",
        "bitrate",
        "sample_rate",
        "channels",
        "source",
        "tapes_files",
        "djs_file",
        "djs_set",
        "notes",
    ]
    missing = [name for name in required if not fields.get(name)]
    if missing:
        raise ValueError(f"Missing required .nfo fields: {', '.join(missing)}")

    fields["djs_set"] = fields["djs_set"].rstrip(".")
    fields["encoded_by"] = "OrbitHub"
    fields["source"] = "DAT"
    fields["notes"] = re.sub(r"\btape\b", "recording", fields["notes"], flags=re.I)
    fields["notes"] = re.sub(r"\bBut\b", "More than", fields["notes"], count=1)
    fields["notes"] = re.sub(
        r"recording\. More than more than",
        "recording. More than",
        fields["notes"],
        flags=re.I,
    )

    return event, fields


def event_date_iso(display_date: str) -> str:
    day, month, year = (int(part) for part in display_date.split("-"))
    full_year = 1900 + year if year >= 91 else 2000 + year
    return f"{full_year:04d}-{month:02d}-{day:02d}"


def slugify(value: str) -> str:
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def build_identifier(event: dict[str, str], fields: dict[str, str]) -> str:
    compact_date = event_date_iso(event["display_date"]).replace("-", "")
    artist = slugify(fields["djs_file"])
    return f"orbit-{compact_date}-{event['file_number']}-{artist}"


def normalize_notes(notes: str) -> str:
    notes = re.sub(r"\s+", " ", notes).strip()
    notes = re.sub(
        r"The named DJ\(s\) will feature on this recording\.\s*But more than",
        "The named DJ(s) will feature on this recording. More than",
        notes,
        flags=re.I,
    )
    return notes


def build_description(event: dict[str, str], fields: dict[str, str]) -> str:
    esc = lambda value: html.escape(value, quote=False)

    file_size = fields["file_size"].strip()
    if not re.search(r"\bbytes\b", file_size, flags=re.I):
        file_size = f"{file_size} bytes"

    notes = normalize_notes(fields["notes"])

    return "\n".join(
        [
            (
                f"<strong>OrbitHub presents:</strong> Live sets from The Orbit, "
                f"{esc(event['display_date'])} — File {esc(event['file_number'])} "
                f"of {esc(event['file_total'])}.<br><br>"
            ),
            f"<strong>Filename:</strong> {esc(fields['filename'])}<br>",
            f"<strong>Status:</strong> {esc(fields['status'])}<br>",
            f"<strong>Original Release Date:</strong> {esc(fields['release_date'])}<br>",
            f"<strong>File Size:</strong> {esc(file_size)}<br>",
            f"<strong>Length:</strong> {esc(fields['length'])}<br>",
            "<strong>Encoded by:</strong> OrbitHub<br>",
            f"<strong>Type:</strong> {esc(fields.get('type', 'Music - DJ Set - Techno'))}<br>",
            f"<strong>Audio Format:</strong> {esc(fields['audio_format'])}<br>",
            f"<strong>Bitrate:</strong> {esc(fields['bitrate'])}<br>",
            f"<strong>Sample Rate:</strong> {esc(fields['sample_rate'])}<br>",
            f"<strong>Channels:</strong> {esc(fields['channels'])}<br>",
            "<strong>Source:</strong> DAT<br>",
            f"<strong>Tapes/files in set:</strong> {esc(fields['tapes_files'])}<br>",
            f"<strong>DJ(s) for this file:</strong> {esc(fields['djs_file'])}<br>",
            f"<strong>DJ(s) for set:</strong> {esc(fields['djs_set'])}<br><br>",
            f"<strong>Notes:</strong> {esc(notes)}",
        ]
    )


def build_metadata(
    identifier: str,
    event: dict[str, str],
    fields: dict[str, str],
    description: str,
) -> dict[str, object]:
    return {
        "mediatype": "audio",
        "title": (
            f"The Orbit - {event['display_date']} - "
            f"File {event['file_number']} of {event['file_total']} - {fields['djs_file']}"
        ),
        "creator": fields["djs_file"],
        "date": event_date_iso(event["display_date"]),
        "description": description,
        "subject": ["The Orbit", "Techno", "DJ Set"],
        "identifier": identifier,
    }


def print_preview(
    identifier: str,
    nfo_path: Path,
    audio_path: Path,
    fields: dict[str, str],
    metadata: dict[str, object],
) -> None:
    print("Internet Archive upload preview")
    print("=" * 32)
    print(f"Identifier : {identifier}")
    print(f"Audio      : {audio_path}")
    print(f"Remote name: {fields['filename']}")
    print(f"NFO        : {nfo_path}")
    print(f"Title      : {metadata['title']}")
    print(f"Creator    : {metadata['creator']}")
    print(f"Date       : {metadata['date']}")
    print()
    print("Description")
    print("-" * 32)
    print(metadata["description"])
    print()


def upload_item(
    identifier: str,
    nfo_path: Path,
    audio_path: Path,
    fields: dict[str, str],
    metadata: dict[str, object],
) -> None:
    if internetarchive is None:
        raise RuntimeError(
            "The 'internetarchive' package is not installed. "
            "Install it with: pip install internetarchive"
        )

    item = internetarchive.get_item(identifier)

    if item.exists:
        raise RuntimeError(
            f"Internet Archive item already exists: {identifier}\n"
            "Refusing to overwrite an existing item."
        )

    print(f"Uploading audio to {identifier}...")
    response = item.upload_file(
        audio_path,
        key=fields["filename"],
        metadata=metadata,
        queue_derive=False,
        verify=True,
        retries=10,
        verbose=True,
    )
    response.raise_for_status()

    print("Uploading original .nfo...")
    response = item.upload_file(
        nfo_path,
        key=nfo_path.name,
        queue_derive=True,
        verify=True,
        retries=10,
        verbose=True,
    )
    response.raise_for_status()

    refreshed = internetarchive.get_item(identifier)
    remote_names = {file.name for file in refreshed.files}

    expected = {fields["filename"], nfo_path.name}
    missing = expected - remote_names
    if missing:
        raise RuntimeError(
            "Upload completed but verification could not find: "
            + ", ".join(sorted(missing))
        )

    print()
    print("Upload verified.")
    print(f"Item: https://archive.org/details/{identifier}")
    print(
        "Audio: "
        f"https://archive.org/download/{identifier}/{fields['filename'].replace(' ', '%20')}"
    )


def main() -> int:
    args = parse_args()

    if not args.nfo.is_file():
        print(f"ERROR: .nfo not found: {args.nfo}", file=sys.stderr)
        return 1

    if not args.audio.is_file():
        print(f"ERROR: audio file not found: {args.audio}", file=sys.stderr)
        return 1

    try:
        text = read_nfo(args.nfo)
        event, fields = parse_nfo(text)
        identifier = args.identifier or build_identifier(event, fields)
        description = build_description(event, fields)
        metadata = build_metadata(identifier, event, fields, description)

        print_preview(identifier, args.nfo, args.audio, fields, metadata)

        if not args.upload:
            print("DRY RUN: nothing uploaded. Add --upload after reviewing this preview.")
            return 0

        upload_item(
            identifier,
            args.nfo,
            args.audio,
            fields,
            metadata,
        )
        return 0

    except (ValueError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
