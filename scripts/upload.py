#!/usr/bin/env python3
"""Prepare and upload one OrbitHub audio item to Internet Archive.

The .nfo is used only as local source metadata and is not uploaded.

Default behaviour is a dry run. Nothing is uploaded unless --upload is supplied.

Requires:
    pip install internetarchive
    ia configure

Usage:
    python3 scripts/upload.py "/path/to/audio.mp3"
    python3 scripts/upload.py "/path/to/audio.mp3" --upload

The metadata file must sit beside the audio file and use the same basename:
    orbit-19941231-1-nigel-walker.mp3
    orbit-19941231-1-nigel-walker.nfo
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import time
from pathlib import Path

import requests

try:
    import internetarchive
except ImportError:
    internetarchive = None


class RateLimitError(RuntimeError):
    """Internet Archive rejected the request due to rate limiting/spam protection."""


FIELD_MAP = {
    "Filename": "filename",
    "Status": "status",
    "Release Date": "release_date",
    "File Size": "file_size",
    "Length": "length",
    "Uploaded by": "uploaded_by",
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
    "Additional Info": "additional_info",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare or upload one OrbitHub set to Internet Archive."
    )
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
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Return after IA accepts the upload; verify later with inventory.py.",
    )
    return parser.parse_args()


def read_nfo(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def clean_wrapped_value(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def derive_djs_file_from_filename(
    filename: str,
    djs_set: str,
) -> str | None:
    """Derive missing per-file DJ metadata from the original filename.

    The filename must contain a parenthesized DJ list immediately before .mp3.
    Casing is recovered only from exact case-insensitive matches in DJ(s) for set;
    otherwise return None rather than guessing.
    """
    match = re.search(r"\(([^()]*)\)\.mp3\s*$", filename, flags=re.IGNORECASE)
    if not match:
        return None

    filename_parts = [
        clean_wrapped_value(part)
        for part in match.group(1).split(",")
        if clean_wrapped_value(part)
    ]
    set_parts = [
        clean_wrapped_value(part)
        for part in djs_set.rstrip(".").split(",")
        if clean_wrapped_value(part)
    ]

    if not filename_parts or not set_parts:
        return None

    set_lookup = {part.casefold(): part for part in set_parts}
    resolved = []

    for part in filename_parts:
        canonical = set_lookup.get(part.casefold())
        if canonical is None:
            return None
        resolved.append(canonical)

    return ", ".join(resolved)


def parse_fields(text: str) -> dict[str, str]:
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
    return fields


def parse_unverified_nfo(text: str) -> tuple[dict[str, str], dict[str, str]]:
    banner = re.search(
        r"TheOrbituary presents\.\.\.\s*(.+?)\s+live\s+@\s+The Orbit,\s*(?:(?:England|Ossett),\s*)?"
        r"(?:(\d{2}-\d{2}-\d{2})|(\d{4})|\[Date Unknown\])"
        r"(?:,\s*Side\s+([A-Za-z0-9]+))?\.?",
        text,
        flags=re.IGNORECASE,
    )
    if not banner:
        raise ValueError("Could not parse supported unverified NFO banner.")

    artist = clean_wrapped_value(banner.group(1))
    exact_date = banner.group(2)
    year_only = banner.group(3)
    side = banner.group(4) or ""

    if exact_date:
        display_date = exact_date
        date_precision = "day"
    elif year_only:
        display_date = year_only
        date_precision = "year"
    else:
        display_date = "[Date Unknown]"
        date_precision = "unknown"

    fields = parse_fields(text)
    required = [
        "filename",
        "release_date",
        "file_size",
        "length",
        "audio_format",
        "bitrate",
        "sample_rate",
        "channels",
        "source",
    ]
    missing = [name for name in required if not fields.get(name)]
    if missing:
        raise ValueError(
            "Missing required unverified .nfo fields: " + ", ".join(missing)
        )

    fields["original_filename"] = fields["filename"]
    fields["djs_file"] = artist

    event = {
        "kind": "unverified",
        "display_date": display_date,
        "date_precision": date_precision,
        "side": side,
        "artist": artist,
    }
    return event, fields


def parse_nfo(text: str) -> tuple[dict[str, str], dict[str, str]]:
    banner_match = re.search(
        r"Live sets from The Orbit,\s*(\d{2}-\d{2}-\d{2}),\s*File\s+(\d+)\s+of\s+(\d+)\.",
        text,
        flags=re.IGNORECASE,
    )
    if not banner_match:
        return parse_unverified_nfo(text)

    event = {
        "kind": "canonical",
        "display_date": banner_match.group(1),
        "file_number": banner_match.group(2),
        "file_total": banner_match.group(3),
    }

    fields = parse_fields(text)

    if not fields.get("djs_file") and fields.get("filename") and fields.get("djs_set"):
        derived_djs = derive_djs_file_from_filename(
            fields["filename"],
            fields["djs_set"],
        )
        if derived_djs:
            fields["djs_file"] = derived_djs

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
    artist = slugify(fields["djs_file"])

    if event.get("kind") == "unverified":
        side = event.get("side", "")
        side_part = f"-{slugify(side)}" if side else ""
        precision = event.get("date_precision")

        if precision == "day":
            date_key = event_date_iso(event["display_date"]).replace("-", "")
        elif precision == "year":
            date_key = event["display_date"]
        elif precision == "unknown":
            date_key = "unknown"
        else:
            raise ValueError("Unsupported unverified date precision.")

        return f"orbit-unverified-{date_key}{side_part}-{artist}"

    compact_date = event_date_iso(event["display_date"]).replace("-", "")
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


def normalize_files_in_set(value: str) -> str:
    match = re.search(r"(\d+)\s+files?\b", value, flags=re.I)
    if match:
        return match.group(1)

    return value.strip()


def build_description(event: dict[str, str], fields: dict[str, str]) -> str:
    esc = lambda value: html.escape(value, quote=False)

    file_size = fields["file_size"].strip()
    if not re.search(r"\bbytes\b", file_size, flags=re.I):
        file_size = f"{file_size} bytes"

    if event.get("kind") == "unverified":
        location = event["display_date"]
        if event.get("side"):
            location += f" — Side {event['side']}"

        lines = [
            (
                f"<strong>OrbitHub archive:</strong> {esc(fields['djs_file'])} live @ "
                f"The Orbit, {esc(location)}.<br><br>"
            ),
            "<strong>Archive status:</strong> Unverified legacy set<br>",
            f"<strong>Filename:</strong> {esc(fields['filename'])}<br>",
        ]
        if fields.get("original_filename") and fields["original_filename"] != fields["filename"]:
            lines.append(
                f"<strong>Original filename:</strong> {esc(fields['original_filename'])}<br>"
            )
        if fields.get("status"):
            lines.append(f"<strong>Source NFO status:</strong> {esc(fields['status'])}<br>")
        lines.extend(
            [
                f"<strong>Original Release Date:</strong> {esc(fields['release_date'])}<br>",
                f"<strong>File Size:</strong> {esc(file_size)}<br>",
                f"<strong>Length:</strong> {esc(fields['length'])}<br>",
            ]
        )
        if fields.get("uploaded_by"):
            lines.append(f"<strong>Uploaded by:</strong> {esc(fields['uploaded_by'])}<br>")
        if fields.get("encoded_by"):
            lines.append(f"<strong>Encoded by:</strong> {esc(fields['encoded_by'])}<br>")
        lines.extend(
            [
                f"<strong>Type:</strong> {esc(fields.get('type', 'Music - DJ Set - Techno'))}<br>",
                f"<strong>Audio Format:</strong> {esc(fields['audio_format'])}<br>",
                f"<strong>Bitrate:</strong> {esc(fields['bitrate'])}<br>",
                f"<strong>Sample Rate:</strong> {esc(fields['sample_rate'])}<br>",
                f"<strong>Channels:</strong> {esc(fields['channels'])}<br>",
                f"<strong>Source:</strong> {esc(fields['source'])}<br>",
            ]
        )
        if fields.get("additional_info"):
            lines.append(
                f"<br><strong>Additional Info:</strong> {esc(fields['additional_info'])}"
            )
        return "\n".join(lines)

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
            f"<strong>Files in set:</strong> {esc(normalize_files_in_set(fields['tapes_files']))}<br>",
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
    if event.get("kind") == "unverified":
        side = f" - Side {event['side']}" if event.get("side") else ""
        metadata: dict[str, object] = {
            "mediatype": "audio",
            "title": (
                f"The Orbit - {event['display_date']}{side} - {fields['djs_file']}"
            ),
            "description": description,
            "subject": ["The Orbit", "Techno", "DJ Set", "Unverified"],
        }
        if event.get("date_precision") == "day":
            metadata["date"] = event_date_iso(event["display_date"])
        elif event.get("date_precision") == "year":
            metadata["date"] = event["display_date"]
        return metadata

    return {
        "mediatype": "audio",
        "title": (
            f"The Orbit - {event['display_date']} - "
            f"File {event['file_number']} of {event['file_total']} - {fields['djs_file']}"
        ),
        "date": event_date_iso(event["display_date"]),
        "description": description,
        "subject": ["The Orbit", "Techno", "DJ Set"],
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
    print(f"Title      : {metadata['title']}")
    print(f"Date       : {metadata.get('date', '-')}")
    print()
    print("Description")
    print("-" * 32)
    print(metadata["description"])
    print()



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


def upload_item(
    identifier: str,
    nfo_path: Path,
    audio_path: Path,
    fields: dict[str, str],
    metadata: dict[str, object],
    *,
    wait_for_verification: bool = True,
) -> None:
    if internetarchive is None:
        raise RuntimeError(
            "The 'internetarchive' package is not installed. "
            "Install it with: pip install internetarchive"
        )

    item = internetarchive.get_item(identifier)

    audio_already_present = False

    if item.exists:
        remote_names = remote_file_names(item)
        if fields["filename"] in remote_names:
            audio_already_present = True
            print(
                f"Internet Archive already contains {fields['filename']}: {identifier}\n"
                "Skipping upload and verifying the existing file."
            )
        else:
            print(
                f"Internet Archive item already exists but audio is absent: {identifier}\n"
                "Continuing upload to the existing item."
            )

    if not audio_already_present:
        print(f"Uploading audio to {identifier}...")
        transport_retries = 5

        for attempt in range(1, transport_retries + 1):
            try:
                response = item.upload_file(
                    str(audio_path),
                    key=fields["filename"],
                    metadata=metadata,
                    queue_derive=False,
                    verify=True,
                    retries=10,
                    verbose=True,
                )
                response.raise_for_status()
                break
            except requests.exceptions.RequestException as error:
                error_text = str(error).lower()
                rate_limited = (
                    "please reduce your request rate" in error_text
                    or "appears to be spam" in error_text
                )

                if rate_limited:
                    raise RateLimitError(
                        "Internet Archive rate limit/spam protection triggered; "
                        "stopping this item without immediate retries: "
                        f"{error}"
                    ) from error

                if attempt == transport_retries:
                    raise RuntimeError(
                        f"Upload failed after {transport_retries} connection retries: {error}"
                    ) from error

                delay = 30
                print(
                    f"Connection to Internet Archive failed ({attempt}/{transport_retries}). "
                    f"Retrying in {delay} seconds..."
                )
                time.sleep(delay)

    if not wait_for_verification:
        print()
        print("Submission accepted; verification deferred to inventory.py.")
        return

    expected = {fields["filename"]}
    verification_attempts = 12
    verification_delay = 10
    missing = expected

    for attempt in range(1, verification_attempts + 1):
        refreshed = internetarchive.get_item(identifier)
        remote_names = remote_file_names(refreshed)
        missing = expected - remote_names

        if not missing:
            break

        if attempt < verification_attempts:
            print(
                "Upload accepted; waiting for Internet Archive metadata to update "
                f"({attempt}/{verification_attempts})..."
            )
            time.sleep(verification_delay)

    if missing:
        raise RuntimeError(
            "Upload was accepted, but verification timed out before Internet Archive "
            "listed: " + ", ".join(sorted(missing))
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

    if not args.audio.is_file():
        print(f"ERROR: audio file not found: {args.audio}", file=sys.stderr)
        return 1

    nfo_path = args.audio.with_suffix(".nfo")
    if not nfo_path.is_file():
        print(
            f"ERROR: matching .nfo not found: {nfo_path}",
            file=sys.stderr,
        )
        return 1

    try:
        text = read_nfo(nfo_path)
        event, fields = parse_nfo(text)
        fields["filename"] = args.audio.name
        identifier = args.identifier or build_identifier(event, fields)
        description = build_description(event, fields)
        metadata = build_metadata(identifier, event, fields, description)

        print_preview(identifier, nfo_path, args.audio, fields, metadata)

        if not args.upload:
            print("DRY RUN: nothing uploaded. Add --upload after reviewing this preview.")
            return 0

        upload_item(
            identifier,
            nfo_path,
            args.audio,
            fields,
            metadata,
            wait_for_verification=not args.no_wait,
        )
        return 0

    except RateLimitError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    except (ValueError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
