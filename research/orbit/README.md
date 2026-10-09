# OrbitHub source investigation — Issue #17

Working research only. **Do not publish these records automatically.** OrbitHub's production `content/links.json`, `content/flyers.json` and `content/sets.json` remain unchanged.

## Files

- `sources.csv`: 20 categorized links: 14 existing site links (verification pending) and 6 additional researched resources. `page_verified` means the landing page was accessible and its relevant content was checked; it does **not** establish that every external media item or asserted historical detail is correct.
- `gigography.csv`: evidence rows combining initial recording indexes, flyer transcriptions and cross-referenced OrbitHub recording event groups; multiple evidence rows can describe the same night. A performer recorded on a night is **not** proof of a complete DJ lineup.

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


## Flyer transcription pass (2026-10-09)

Visually inspected ten existing repository flyer reverse-side scans and transcribed 64 advertised date rows from them, plus six June–July 1994 entries from the legible Phatmedia scan. The separate `content/sets.json` comparison contributed 11 recording-event rows. The gigography is **evidence-row based**: multiple rows for one date are intentional.

Inspected assets:
- `19921121-19921231b.jpg`
- `19930102-19930202b.jpg`
- `19930213-19930320b.jpg`
- `19930515-19930605b.jpg`
- `19930612-19930717b.jpg`
- `19940910-19941015b.jpg`
- `19941119-19950107b.jpg`
- `19950114-19950225b.jpg`
- `19951209-19960113b.jpg`
- `19970802-19970920b.jpg`

Additional readable June–July scan: [Phatmedia Orbit June 1994](https://www.phatmedia.co.uk/flyers/event/orbit-flyer13).

### Manual review flags

- The January 1993 flyer has **"Sat 2nd February"**, which cannot be correct in 1993 (2 February was a Tuesday). No dated row was added for that anomalous entry: do not silently correct it to 6 February.
- The May–June 1993 flyer has some overlapping camouflaged type. **8 May** was omitted because the Underground Resistance-related artist name is obscured. **15 May** and **20 January 1996** contain incomplete/uncertain names; verify against another scan before publication.
- The November–January 1994/95 flyer explicitly states **Christmas at home** for 24 December 1994; this is recorded as `no_event`, not as a performance.
- In the November–December 1994 flyer, the dates for **Dag (26 Nov)**, **Andy Weatherall (3 Dec)**, **David Holmes / Oliver Lieb (10 Dec)** and **Sven Väth (17 Dec)** are aligned to their respective printed rows.
- Guest and resident listings are kept distinct. Names printed as general residents are not added to every individual night.
- Other front-side/back-side scans, poorly legible flyer artwork and unverified external flyer collections remain for a subsequent pass. Only the listed scans were visually transcribed.

### Cross-referencing rule

`content/sets.json` describes **11 dated event groups** and multiple audio segments per event. Artist text is preserved at group level in a separate `orbithub_recordings` evidence row; the segmented files do not each create another event. Archive metadata alone does not establish who was advertised or who attended.

### Remaining actions

Inspect remaining front-side scans and additional loose flyers; validate questionable lettering, date anomalies and venue attribution; confirm flyers against independent dated recordings and external sources; build 1991–2003 coverage report including explicit unknown Saturdays. Nothing in this research automatically modifies published website content.

## Next investigation

Complete individual flyer image transcription, reconcile with existing flyer assets and `content/sets.json`, then expand the gigography across 1991–2003. Record source URLs for each date and separate performances from complete advertised bills.

## Source status vocabulary

- `page_verified`: accessible content confirmed in current research
- `not_verified`: link from existing site; not yet revisited
- `documented_recording`: indexed recording with date/performer
- `secondary_recording_listing`: database entry requiring primary-source corroboration
- `secondary_listing`: other catalogue requiring corroboration

No data is considered a complete concert/event history.
