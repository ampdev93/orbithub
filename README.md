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
- `css/style.css` — site styles
- `js/main.js` — shared fragments and audio playback
- `assets/flyers/` — tracked flyer assets

Local work directories and `assets/images/` are intentionally ignored.

## Local testing

The shared header and footer are loaded with `fetch()`, so test through a local web server rather than opening HTML files directly:

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
