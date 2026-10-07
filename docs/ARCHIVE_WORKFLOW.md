# Archive Workflow

This document defines the canonical OrbitHub workflow for preparing, uploading, verifying and publishing archived audio sets.

It is the operational contract for archive handling. Automation must implement these rules; it must not invent or silently change them.

## Canonical naming

Every archived set uses one canonical basename:

```text
orbit-YYYYMMDD-N-dj-name
```

Use exactly:

```text
Identifier: orbit-YYYYMMDD-N-dj-name
MP3:        orbit-YYYYMMDD-N-dj-name.mp3
NFO:        orbit-YYYYMMDD-N-dj-name.nfo
```

Rules:

- event date uses `YYYYMMDD`
- set/file number is an unpadded integer
- DJ slug is lowercase
- spaces and punctuation become `-`
- multiple DJs remain in listed order
- repeated hyphens collapse
- identifier, MP3 and NFO must share exactly the same basename

Example:

```text
orbit-19941231-1-nigel-walker
orbit-19941231-1-nigel-walker.mp3
orbit-19941231-1-nigel-walker.nfo
```

## Source metadata

The original release `.nfo` is the source metadata for the archive item.

The local normalized pair is:

```text
orbit-YYYYMMDD-N-dj-name.mp3
orbit-YYYYMMDD-N-dj-name.nfo
```

The original `.nfo` contents remain historically authoritative except where the documented normalization rules apply.

See:

```text
docs/IA_METADATA.md
```

## Local preparation

Raw ZIP archives are stored in:

```text
work/sets-to-unzip/
```

Prepared MP3/NFO pairs are stored in:

```text
work/sets-to-upload/
```

The normal preparation flow is:

```text
source ZIP
    ↓
extract MP3 + release.nfo
    ↓
parse NFO metadata
    ↓
derive canonical basename
    ↓
rename MP3
    ↓
rename release.nfo
    ↓
write matching MP3/NFO pair to work/sets-to-upload/
```

The extraction tool must:

- find exactly one MP3 per ZIP
- find exactly one `release.nfo` per ZIP
- derive the canonical basename from NFO metadata
- refuse filename collisions
- refuse unsafe overwrites
- fail clearly on malformed ZIPs

Use:

```bash
python3 scripts/extract_sets.py
```

for a dry run.

Use:

```bash
python3 scripts/extract_sets.py --apply
```

only after the dry-run output has been reviewed.

## Internet Archive item rules

The Internet Archive item identifier must equal the canonical basename:

```text
orbit-YYYYMMDD-N-dj-name
```

The uploaded MP3 filename must be:

```text
orbit-YYYYMMDD-N-dj-name.mp3
```

The IA description must use the canonical filename, regardless of any historical filename used by an older release.

Canonical direct audio URL:

```text
https://archive.org/download/{identifier}/{identifier}.mp3
```

## Internet Archive metadata

The normalized description must include:

```text
Filename: canonical MP3 filename
Source: DAT
Files in set: N
```

Important rules:

- remove `Archive Name`
- remove obsolete TheOrbituary/site/contact/promotional material
- `Release Date` becomes `Original Release Date`
- `Hz` becomes `Sample Rate`
- `Source: Tape` becomes `Source: DAT`
- legitimate historical/provenance use of the word `tape` may remain
- do not preserve the legacy `sides` interpretation
- use `Files in set: N`
- do not upload the NFO to Internet Archive unless the archive policy is explicitly changed later

See `docs/IA_METADATA.md` for the canonical description format.

## Upload workflow

New items use:

```bash
python3 scripts/upload.py work/sets-to-upload/orbit-YYYYMMDD-N-dj-name.mp3
```

This is a dry run.

Review:

- identifier
- MP3 filename
- title
- date
- normalized description

Then upload:

```bash
python3 scripts/upload.py work/sets-to-upload/orbit-YYYYMMDD-N-dj-name.mp3 --upload
```

The upload process must:

1. derive the matching NFO automatically
2. verify the local files exist
3. derive the canonical IA identifier
4. upload the canonical MP3 filename
5. apply canonical metadata
6. handle transient IA/S3 failures
7. verify the MP3 exists on IA
8. print the final item and direct audio URLs

## Existing IA items

Existing items must be inventoried before mutation.

For each existing set, verify:

```text
event
file number
DJ
local MP3
local NFO
canonical identifier
canonical MP3 filename
existing IA identifier
existing IA MP3 filename
IA description status
OrbitHub audio URL
```

No mutation should occur if any row is ambiguous or missing.

When an existing IA identifier is already canonical, preserve it.

Preferred migration sequence:

```text
existing IA identifier
    ↓
upload canonical MP3 filename
    ↓
verify canonical MP3 exists
    ↓
update normalized description
    ↓
verify description
    ↓
remove legacy MP3 filename only after verification
```

Do not delete and recreate whole IA items unless identifier reuse has been explicitly tested and there is a concrete reason to do so.

## Description editing

For a single existing item, use:

```bash
python3 scripts/edit.py work/sets-to-upload/orbit-YYYYMMDD-N-dj-name.mp3
```

This performs a dry comparison.

Apply only after review:

```bash
python3 scripts/edit.py work/sets-to-upload/orbit-YYYYMMDD-N-dj-name.mp3 --apply
```

The comparison ignores harmless IA serialization differences such as:

```html
<br>
<br />
<br/>
```

## Website publication

OrbitHub must not be updated until the corresponding IA item is verified.

The website source of truth is:

```text
content/sets.json
```

Each audio URL should use:

```text
https://archive.org/download/{identifier}/{identifier}.mp3
```

No change to `sets.html` or the player architecture should normally be required.

## Verification gate

Before an archive item is considered complete, verify:

- [ ] local MP3/NFO basename match
- [ ] basename follows the canonical naming convention
- [ ] IA identifier matches the canonical basename
- [ ] IA MP3 filename matches the canonical basename
- [ ] IA description filename matches the canonical basename
- [ ] IA description shows `Source: DAT`
- [ ] IA description shows `Files in set: N`
- [ ] direct IA MP3 URL works
- [ ] `content/sets.json` uses the canonical direct URL
- [ ] OrbitHub player loads and plays the set
- [ ] no legacy filename remains in the active website content

Only after every applicable check passes is the item complete.

## Permanent workflow

The canonical process is:

```text
source ZIP
→ extract/normalize
→ verify local pair
→ upload.py dry run
→ upload
→ verify IA
→ update content/sets.json
→ local website test
→ merge
```

## Change control

If the naming convention, metadata contract or archive sequence needs to change:

1. change the documentation first
2. review the proposed contract
3. update automation second
4. test with one item
5. only then apply the change in bulk

Do not change archive rules opportunistically inside scripts.

## Project rule

> Define and document the archive contract first. Automation implements that contract and must not invent or change it.
