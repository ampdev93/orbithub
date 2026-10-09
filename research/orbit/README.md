# OrbitHub source investigation — Issue #17

Working research only. **Do not publish these records automatically.** OrbitHub's production `content/links.json`, `content/flyers.json` and `content/sets.json` remain unchanged.

## Files

- `sources.csv`: 20 categorized links: 14 existing site links (verification pending) and 6 additional researched resources. `page_verified` means the landing page was accessible and its relevant content was checked; it does **not** establish that every external media item or asserted historical detail is correct.
- `gigography.csv`: 19 initial *partial* event-date records from indexed recordings / secondary lists. A performer recorded on a night is **not** proof of a complete DJ lineup.

## Verification gates

1. **Link verification**: open target URL, confirm subject/venue/date and classify; record broken, login-only and redirect links explicitly. Merely listing a URL is not verification.
2. **Flyer evidence**: retain original flyer URL, front/back side, local asset filename and line-by-line artist/date transcription. Source images already present in `assets/flyers/` include date-range names such as `19940625-19940723f.jpg`; these must be visually inspected before claiming individual dates or complete lineups.
3. **Date verification**: use ISO date (`YYYY-MM-DD`), tag venue (Morley, Ossett, off-site or unknown), retain source IDs, do not convert a month-only or year-only item to a specific day.
4. **Artist verification**: distinguish advertised artists (flyer), recorded artists (audio), and unverified recollections; confirm spelling and live/DJ status. Record disagreements rather than silently resolving them.
5. **Promotion**: only publish independently reviewed and categorized links to `content/links.json`; preserve the existing production schema unless a renderer change is separately approved.

## Initial observations (2026-10-09)

- The Phatmedia flyer page (`SRC-015`) labels an Orbit flyer **25 June 1994**, **The Afterdark Club**, **Morley Leeds**. Read both scans before extracting the full June–July programme.
- MixesDB (`SRC-016`) is a useful *recording* index, not a definitive gigography.
- DJWORX (`SRC-017`) lists the Ossett and Morley years and notes an ambiguous 22 August 1992 Leeds Corn Exchange / Orbit association; venue must not be assumed from a recording title.
- 88to98 (`SRC-018`) provides background, flyer leads and attendee comments; memories require corroboration.
- Existing `assets/flyers/` holds original-looking scans but `content/flyers.json` is empty. No image or audio files were downloaded in this phase.

## Next investigation

Complete individual flyer image transcription, reconcile with existing flyer assets and `content/sets.json`, then expand the gigography across 1991–2003. Record source URLs for each date and separate performances from complete advertised bills.

## Source status vocabulary

- `page_verified`: accessible content confirmed in current research
- `not_verified`: link from existing site; not yet revisited
- `documented_recording`: indexed recording with date/performer
- `secondary_recording_listing`: database entry requiring primary-source corroboration
- `secondary_listing`: other catalogue requiring corroboration

No data is considered a complete concert/event history.
