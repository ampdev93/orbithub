# OrbitHub

Static archival website for The Orbit.

## Structure

- `index.html` — home/history
- `flyers.html` — flyer gallery
- `sets.html` — playable sets hosted by Internet Archive
- `images.html` — image archive
- `links.html` — external archive links
- `about.html` — project information
- `header.html` / `footer.html` — shared page fragments
- `content/sets.json` — event and set metadata
- `content/flyers.json` — flyer metadata
- `content/images.json` — image metadata
- `content/links.json` — external-link metadata
- `css/style.css` — site styles
- `js/main.js` — shared fragments, content rendering and audio playback
- `assets/flyers/` — tracked flyer assets

Local work directories and `assets/images/` are intentionally ignored.

## Content workflow

The HTML files define the static page structure. Archive content is stored separately in `content/*.json` and rendered by `js/main.js`.

For normal archive updates, edit the relevant JSON file rather than adding repeated content directly to the HTML page.

## Local testing

Shared fragments and JSON content are loaded with `fetch()`, so test through a local web server rather than opening HTML files directly:

```bash
python3 -m http.server 8000
```

Then open:

```text
http://localhost:8000/
```

## Deployment

GitHub Pages publishes the `main` branch from the repository root.

Production site:

```text
https://ampdev93.github.io/orbithub/
```
