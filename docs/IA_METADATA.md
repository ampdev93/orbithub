# Internet Archive Metadata

OrbitHub uses the original release `.nfo` files as the source for Internet Archive item descriptions.

The original `.nfo` files should be preserved unchanged as archival artifacts. The Internet Archive description should use a cleaned HTML version intended for readable presentation.

## Retain

Keep recording and release metadata that describes the archival object:

- event/date
- file number
- Filename
- Status
- Original Release Date
- File Size
- Length
- Encoded by
- Type
- Audio Format
- Bitrate
- Sample Rate
- Channels
- Source
- Files in set
- DJ(s) for this file
- DJ(s) for set
- Notes

## Remove

Remove obsolete or redundant distribution-site material:

- Archive Name
- old website URLs
- old email/contact information
- TheOrbituary branding
- Site Information section
- promotional/community text
- slogans
- obsolete website references

Internet Archive-generated fields such as `Addeddate`, `Identifier`, and `Scanner` are not copied from the original `.nfo`; they are managed by Internet Archive.

## Normalize

Apply these rules when converting an original `.nfo` into the Internet Archive description:

- `TheOrbituary` → `OrbitHub`
- old encoder/contact identity → `OrbitHub`
- `Release Date` → `Original Release Date`
- `Hz` → `Sample Rate`
- `Source: Tape` → `Source: DAT`
- `Tapes/files in set: X tapes / Y files (sides)` → `Files in set: Y`
- references to `tape` in Notes → `recording`
- flatten wrapped DJ lists into a single line
- append `bytes` to File Size when the value is a raw byte count
- remove dotted `.nfo` alignment
- render the description as simple HTML using bold labels and `<br>` line breaks

Do not change the underlying historical facts unless a separate verification step establishes that the original metadata is wrong.

## Canonical Internet Archive Description Format

Use this structure:

```html
<strong>OrbitHub presents:</strong> Live sets from The Orbit, DD-MM-YY — File N of N.<br><br>

<strong>Filename:</strong> filename.mp3<br>
<strong>Status:</strong> Verified first-generation tape recorded on the night.<br>
<strong>Original Release Date:</strong> Month DDth, YYYY<br>
<strong>File Size:</strong> 00,000,000 bytes<br>
<strong>Length:</strong> MM:SS<br>
<strong>Encoded by:</strong> OrbitHub<br>
<strong>Type:</strong> Music - DJ Set - Techno<br>
<strong>Audio Format:</strong> MPEG 1.0 layer 3<br>
<strong>Bitrate:</strong> 160kbit (CBR)<br>
<strong>Sample Rate:</strong> 44,100Hz<br>
<strong>Channels:</strong> Joint Stereo<br>
<strong>Source:</strong> DAT<br>
<strong>Files in set:</strong> N<br>
<strong>DJ(s) for this file:</strong> Artist Name<br>
<strong>DJ(s) for set:</strong> Artist One, Artist Two, Artist Three<br><br>

<strong>Notes:</strong> The named DJ(s) will feature on this recording. More than one DJ may play on the same recording.
```

The field values should come from the source `.nfo` except where the normalization rules above explicitly apply.

## Example

Original-style metadata:

```text
Filename.............: orbit-19941001-6 (colin dale).mp3
Archive Name.........: toc-19941001-6.zip
Status...............: Verified first-generation tape recorded on the night.
Release Date.........: February 10th, 2007
File Size............: 35,600,384
Length...............: 29:39
Encoded by...........: orbithub
Type.................: Music - DJ Set - Techno
Audio Format.........: MPEG 1.0 layer 3
Bitrate..............: 160kbit (CBR)
Hz...................: 44,100Hz
Channels.............: Joint Stereo
Source...............: Tape
Tapes/files in set...: 3 tapes / 6 files (sides)
DJ(s) for this file..: Colin Dale
DJ(s) for set........: Nigel Walker, John Berry, Salt Tank, Colin Dale
Notes................: The named DJ(s) will feature on this tape. But more than
                       one DJ may play on the same tape.
```

Internet Archive description:

```html
<strong>OrbitHub presents:</strong> Live sets from The Orbit, 01-10-94 — File 6 of 6.<br><br>

<strong>Filename:</strong> orbit-19941001-6 (colin dale).mp3<br>
<strong>Status:</strong> Verified first-generation tape recorded on the night.<br>
<strong>Original Release Date:</strong> February 10th, 2007<br>
<strong>File Size:</strong> 35,600,384 bytes<br>
<strong>Length:</strong> 29:39<br>
<strong>Encoded by:</strong> OrbitHub<br>
<strong>Type:</strong> Music - DJ Set - Techno<br>
<strong>Audio Format:</strong> MPEG 1.0 layer 3<br>
<strong>Bitrate:</strong> 160kbit (CBR)<br>
<strong>Sample Rate:</strong> 44,100Hz<br>
<strong>Channels:</strong> Joint Stereo<br>
<strong>Source:</strong> DAT<br>
<strong>Files in set:</strong> 6<br>
<strong>DJ(s) for this file:</strong> Colin Dale<br>
<strong>DJ(s) for set:</strong> Nigel Walker, John Berry, Salt Tank, Colin Dale<br><br>

<strong>Notes:</strong> The named DJ(s) will feature on this recording. More than one DJ may play on the same recording.
```

## Automation

Any future conversion or upload script should follow this document as the normalization contract.

The conversion step should remain deterministic:

```text
original .nfo
    ↓
parse retained fields
    ↓
apply documented normalization rules
    ↓
produce IA HTML description
    ↓
review
    ↓
upload
```

Do not make undocumented editorial changes during automated conversion.
