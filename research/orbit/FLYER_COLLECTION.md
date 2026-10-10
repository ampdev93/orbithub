# Raw flyer acquisition — Issue #17

The flyer collector intentionally makes **no image modifications**.

## Run locally

```bash
git switch research/issue-17-orbit-sources
git pull --ff-only
python3 research/orbit/download_flyers.py
```

Sources searched:

- [Old Skool Anthems Orbit category](https://www.oldskoolanthems.com/media/categories/orbit.87/) — approximately 101 listed media items across two index pages at the time of research. Some may duplicate existing files or be photographs rather than flyers.
- [Phatmedia Orbit flyer listings](https://www.phatmedia.co.uk/flyers/event/orbit-flyer13) — known Orbit flyer numbered pages, individually checked to avoid unrelated items.

Output:

- `research/orbit/downloads/` — original downloaded bytes, unchanged; filenames are deterministic hashes.
- `research/orbit/downloads.csv` — original source page/image URL, filename, SHA-256, download status, error if any.

Downloads and the manifest are gitignored **until they have been reviewed**. The existing `assets/flyers` and public website JSON files are not changed. Review `downloads.csv` to identify failures and duplicates and decide which images to preserve in version control. Files with identical byte hashes are downloaded once.

This collector is designed for public endpoints and does not bypass logins, access controls or anti-bot restrictions. It may encounter blocked images; those are reported in the manifest. It has not been tested end-to-end in the current execution environment because direct external file downloading is unavailable.

After collection, inspect the flyer images, transcribe dates/DJs and build the gigography **before** comparing with the OrbitHub sets catalogue.
