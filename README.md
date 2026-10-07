# OrbitHub

OrbitHub is a small static archival website preserving material relating to The Orbit (1991–2003).

## Principles

- Static HTML, CSS and JavaScript only
- No framework
- No backend
- Minimal JavaScript
- Dark, lightweight, image-focused presentation
- Archive content kept separate from page structure
- Easy to host and edit manually

## Repository

Canonical repository:

```text
https://github.com/ampdev93/orbithub
```

Canonical branch:

```text
main
```

Production site:

```text
https://ampdev93.github.io/orbithub/
```

## Structure

```text
orbithub/
├── index.html
├── about.html
├── flyers.html
├── images.html
├── links.html
├── sets.html
├── header.html
├── footer.html
├── content/
│   ├── flyers.json
│   ├── images.json
│   ├── links.json
│   └── sets.json
├── css/
│   └── style.css
├── js/
│   └── main.js
├── assets/
│   └── flyers/
├── docs/
│   └── BASELINE.md
└── README.md
```

## Content model

HTML defines the static page structure.

Archive content is stored in:

```text
content/flyers.json
content/images.json
content/links.json
content/sets.json
```

`js/main.js` loads the JSON and renders the content into the relevant page.

For normal archive updates, edit the JSON rather than adding repeated content directly to the HTML.

## Local testing

Because shared fragments and JSON are loaded with `fetch()`, use a local HTTP server:

```bash
python3 -m http.server 8000
```

Open:

```text
http://localhost:8000/
```

Do not test the site through `file://`.

## Change workflow

OrbitHub uses a deliberately simple workflow:

```text
main
  ↓
temporary change branch
  ↓
local visual/functional test
  ↓
merge to main after approval
```

GitHub-side branch, commit, pull-request and merge operations may be handled through ChatGPT when requested. Local verification remains the maintainer's approval step before promotion to `main`.

## Deployment

GitHub Pages publishes directly from the repository root on `main`.

No build command or framework is required.

## Project separation

OrbitHub is independent from the `torn-trackers` project.

Do not carry Torn Tracker architecture, issues, terminology, runtime assumptions or project-control processes into OrbitHub. Generic Git and engineering practices may be reused where appropriate.

See `docs/BASELINE.md` for the current architectural baseline.
