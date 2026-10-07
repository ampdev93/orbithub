# OrbitHub Baseline

## Status

This document records the foundational OrbitHub architecture after the initial stabilization and content-separation work.

Canonical repository:

```text
ampdev93/orbithub
```

Canonical branch:

```text
main
```

Hosting:

```text
GitHub Pages
https://ampdev93.github.io/orbithub/
```

## Scope

OrbitHub is an archival website for The Orbit.

The site is intentionally small and static. It is not intended to become an application platform, social network, database-backed service or general-purpose content-management system.

The baseline priorities are:

- preservation
- simplicity
- fast loading
- easy manual maintenance
- stable public URLs
- minimal dependencies

## Technology

The production site uses only:

- HTML
- CSS
- browser JavaScript
- JSON content files

There are no:

- JavaScript frameworks
- CSS frameworks
- package managers
- build systems
- server-side components
- databases

## Architecture

The site has three layers:

```text
HTML = page structure
JSON = archive/content data
JS   = shared loading and rendering
```

### Static HTML

The following files define the page shells:

```text
index.html
about.html
flyers.html
images.html
links.html
sets.html
```

`header.html` and `footer.html` are shared fragments loaded by JavaScript.

`index.html` and `about.html` remain editorial/static pages.

### Structured content

Archive content is stored separately:

```text
content/flyers.json
content/images.json
content/links.json
content/sets.json
```

The JSON files are the content source of truth for their respective archive pages.

Current state:

- `sets.json` contains the existing playable set records
- `links.json` contains the existing external links
- `flyers.json` is currently empty
- `images.json` is currently empty

Flyer and image content will be added when production archive material is ready.

### JavaScript

`js/main.js` is intentionally small.

Its responsibilities are limited to:

- loading `header.html`
- loading `footer.html`
- loading JSON content
- rendering Flyers
- rendering Sets
- rendering Images
- rendering Links
- controlling audio playback

No application framework is required.

## Audio

Playable sets are referenced from `content/sets.json`.

Audio files are hosted externally on Internet Archive and are not stored in the GitHub repository.

The site uses a hidden HTML5 audio element controlled by `js/main.js`.

## Assets

Small website assets and thumbnails may be stored in the repository.

Large archival media should normally live on archival storage such as Internet Archive rather than GitHub.

The existing `assets/flyers/` directory contains historical/work-in-progress flyer assets from the initial site work. The active Flyers content model is currently empty, so those files are not part of the published flyer catalogue unless referenced by JSON later.

`assets/images/` is intentionally ignored.

## Styling

All styling is contained in:

```text
css/style.css
```

Design direction:

- background: `#0d0d0d`
- panel: `#171717`
- text: `#e5e5e5`
- hover: `#2d2d2d`
- no gradients
- minimal effects
- mobile-friendly layout
- Inter / Helvetica / Arial / sans-serif

No CSS framework is used.

## Local development

Run from the repository root:

```bash
python3 -m http.server 8000
```

Then open:

```text
http://localhost:8000/
```

A local HTTP server is required because shared fragments and JSON content are loaded with `fetch()`.

The site should not be tested directly through `file://`.

## Git workflow

`main` is canonical.

Normal changes follow:

1. Create a temporary branch from `main`.
2. Make the change.
3. Test locally.
4. Perform visual/functional verification.
5. Merge into `main` only after approval.
6. GitHub Pages deploys from `main`.

GitHub-side branch, commit, PR and merge operations may be handled through ChatGPT when requested.

This is intentionally lightweight and should not be expanded into a heavier project-control process unless OrbitHub actually needs it.

## Deployment

GitHub Pages publishes from:

```text
branch: main
folder: /(root)
```

There is no build step.

A successful merge to `main` is sufficient to trigger deployment.

## Known baseline behavior

- Missing JSON content results in an empty content area and a console error rather than a custom error interface.
- The browser may request `/favicon.ico`; a favicon is not currently part of the active baseline.
- Flyers and Images currently contain no production catalogue entries.
- Set dates render as plain text unless a future `flyer` field is supplied.
- The JSON renderer already supports optional future flyer links without requiring an HTML change.

These are accepted baseline behaviors rather than defects.

## Boundaries

OrbitHub and `torn-trackers` are separate projects.

OrbitHub must not inherit Torn Tracker-specific:

- architecture
- issue/workstream structure
- database assumptions
- API collector patterns
- runtime/service management
- deployment model
- terminology
- project-control rules

Only generic practices such as Git branches, local verification and controlled merges should be reused where useful.

## Baseline rule

Changes should preserve the project's core constraint:

> Keep OrbitHub static, simple, deterministic and easy to maintain.

Additional infrastructure should only be introduced when a concrete archive requirement justifies it.
