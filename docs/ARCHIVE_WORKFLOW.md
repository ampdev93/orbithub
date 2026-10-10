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

The archive workflow uses exactly these two persistent staging directories for all batches:

```text
work/sets-to-unzip/
work/sets-to-upload/
```

Do not introduce per-batch staging directories such as `work/batch-2/`, `work/unverified-batch-2-zips/`, or alternate upload directories during an active archive run. New batches continue through the same established paths.

Raw ZIP archives are placed in:

```text
work/sets-to-unzip/
```

Prepared MP3/NFO pairs are written to:

```text
work/sets-to-upload/
```

This applies to both verified/canonical DAT sets and unverified legacy sets. The parser and metadata rules may differ by source format, but the local staging process does not.

Completed files remain governed by the existing safe/idempotent workflow. Do not delete, move, rename, or clear staged files merely to start the next batch unless a separate cleanup operation has been explicitly reviewed and approved.

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
- find exactly one NFO file per ZIP (the filename may vary, e.g. `release.nfo`)
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

## Unverified legacy sets

Legacy Orbit releases that are not part of the verified first-generation DAT collection use a separate unverified naming contract.

Supported identifier forms are:

```text
orbit-unverified-YYYYMMDD[-side]-artist
orbit-unverified-YYYY[-side]-artist
orbit-unverified-unknown[-side]-artist
```

Examples:

```text
orbit-unverified-19930417-a-westbam
orbit-unverified-1995-westbam
orbit-unverified-unknown-a-john-e-bloc-and-tanith
```

Rules:

- preserve the source date precision exactly
- exact dates are normalized to `YYYYMMDD` in the identifier
- year-only releases remain year-only; do not invent a month or day
- unknown-date releases remain unknown; do not invent a year
- one- or two-digit legacy day/month values are accepted and normalized when the source NFO supplies an exact date
- preserve side labels when present
- preserve the legacy `Source` value from the NFO, such as `Tape` or `MiniDisk`; do not convert legacy sources to DAT
- preserve source NFO status separately when present, but source wording does not make a legacy item part of the verified DAT collection
- retain legitimate `Additional Info` metadata
- unverified website events use `"verified": false`
- direct website audio URLs use the same canonical IA pattern as other sets

The publication gate is the same safety gate used elsewhere:

```text
IA item metadata verified
+ canonical MP3 present
+ direct audio URL verified
→ eligible for content/sets.json
```

An accepted IA submission is not sufficient on its own. If direct audio verification is pending because of IA propagation or a transient CDN/network failure, wait and rerun `scripts/inventory.py --check-audio` before publishing.

## Internet Archive item rules

The Internet Archive item identifier must equal the canonical basename:

```text
orbit-YYYYMMDD-N-dj-name
```

The uploaded MP3 filename must be:

```text
orbit-YYYYMMDD-N-dj-name.mp3
```

The IA title must use the canonical display format:

```text
The Orbit - DD-MM-YY - File N of N - DJ(s)
```

Example:

```text
The Orbit - 23-07-94 - File 3 of 6 - John Berry
```

The IA description must use the canonical filename, regardless of any historical filename used by an older release.

Canonical direct audio URL:

```text
https://archive.org/download/{identifier}/{identifier}.mp3
```

## Internet Archive metadata

The normalized IA metadata must include the canonical title plus the canonical description.

Canonical title:

```text
The Orbit - DD-MM-YY - File N of N - DJ(s)
```

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

The upload/migration process is split into submission and verification.

Submission must:

1. derive the matching NFO automatically
2. verify the local files exist
3. derive the canonical IA identifier
4. submit the canonical MP3 filename when required
5. submit canonical metadata when required
6. handle immediate IA/S3 transport failures
7. record/report the action as submitted
8. continue to the next item without waiting for IA propagation

Submission success means Internet Archive accepted the request. It does not mean the change has propagated through IA yet.

Verification is a separate read-only pass using `scripts/inventory.py`. This avoids serial propagation waits across large batches.

## Existing-item and rerun behavior

Archive operations must be safe to rerun. Existing Internet Archive data must never be overwritten or deleted merely because a bulk job is run again.

For each canonical identifier:

```text
identifier not found
    → NEW
    → eligible for upload

identifier exists + canonical MP3 exists + metadata is correct
    → VALID EXISTING
    → SKIP

identifier exists + canonical MP3 exists + metadata needs normalization
    → METADATA MIGRATION
    → update metadata only after dry-run review

identifier exists + only legacy MP3 filename exists
    → LEGACY MIGRATION
    → preserve existing item
    → submit canonical MP3
    → submit normalized metadata
    → report SUBMITTED
    → verify later with inventory.py
    → retain legacy MP3 unless a separate cleanup step is explicitly approved

identifier exists but files/metadata do not match the expected set
    → CONFLICT
    → STOP and report
    → do not upload, overwrite or delete anything
```

Rules:

- bulk upload tools must be idempotent where practical
- an already-valid canonical item is a successful skip, not an error
- existing IA identifiers must not be recreated or replaced automatically
- existing IA files must not be overwritten automatically
- legacy files must not be deleted as part of upload or migration
- deletion/cleanup is a separate destructive operation requiring explicit review and approval
- ambiguous or conflicting matches must stop for that item and be reported
- rerunning a completed batch must not damage or duplicate completed items

A mutation run should report a clear status for every item, for example:

```text
SKIPPED
SUBMITTED
CONFLICT
ERROR
```

A verification run may report:

```text
NEW
SKIPPED
MIGRATION REQUIRED
CONFLICT
ERROR
```

The dry run must make the intended action visible before any mutation occurs.

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
IA title status
IA description status
OrbitHub audio URL
```

No mutation should occur if any row is ambiguous or missing.

When an existing IA identifier is already canonical, preserve it.

Preferred migration sequence:

```text
existing IA identifier
    ↓
submit canonical MP3 filename if needed
    ↓
submit canonical title/description if needed
    ↓
continue immediately to next item
    ↓
run inventory.py after the batch
    ↓
retry only items still requiring migration
    ↓
retain legacy MP3 filename
```

Do not serialize the batch by waiting for IA propagation after each item. Internet Archive may take several minutes to expose accepted file or metadata changes.

Legacy MP3 files are not deleted during migration. Any later cleanup is a separate destructive step requiring explicit review and approval.

Do not delete and recreate whole IA items unless identifier reuse has been explicitly tested, there is a concrete reason to do so, and the destructive operation has been explicitly approved.

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
- [ ] IA title matches `The Orbit - DD-MM-YY - File N of N - DJ(s)`
- [ ] IA description filename matches the canonical basename
- [ ] IA description shows `Source: DAT`
- [ ] IA description shows `Files in set: N`
- [ ] direct IA MP3 URL works (HTTP 200 or 206)
- [ ] `content/sets.json` uses the canonical direct URL
- [ ] OrbitHub player loads and plays the set
- [ ] no legacy filename remains in the active website content

Only after every applicable check passes is the item complete.

For direct-audio verification, use a byte-range GET rather than relying on HEAD. HTTP 200 or 206 is a pass. A 404 indicates a likely filename/path mismatch and must be investigated. HTTP 503, connection reset, TLS timeout or read timeout are transient IA/CDN failures: report the item as verification pending and retry later; do not mutate metadata or revert to a legacy filename solely because of a transient availability failure.

## Permanent workflow

The canonical process is:

```text
source ZIP
→ extract/normalize
→ verify local pair
→ submission dry run
→ submit uploads/metadata
→ run read-only inventory verification
→ retry only outstanding items if required
→ update content/sets.json
→ final inventory verification
→ local website test
→ merge
```

## Current archive snapshot

As of completion of the currently held set backlog:

```text
Total inventory items : 124
Unresolved NEW        : 0
Unresolved PENDING    : 0
Unresolved READY      : 0
Unresolved CONFLICT   : 0
Unresolved ERROR      : 0
```

This is a point-in-time operational snapshot, not a permanent archive-total guarantee. Future recovered sets may increase the inventory.

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
