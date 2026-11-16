# Project: shared_3d_models

## Goal

A public, static site that shows the 3D models I print: each one an orbitable
`<model-viewer>` page with a printable STL to download. Published at
https://aurele-l.github.io/shared_3d_models/ from `main`, repo root.

The workshop stays private: CAD, tests, and source meshes live in
`C:\Users\micro\code\3d_modelling`. This repo holds only what is shared, and the
one-way door between them is `tools/publish.py`.

## Commands

```powershell
python -m http.server 8000                 # preview (file:// cannot fetch a GLB)
uv sync                                    # trimesh/pymeshfix for the converter
uv run tools/publish.py <slug>             # modelling repo -> models/<slug>, then rebuild
uv run tools/publish.py <slug> --no-build  # copy artefacts only
python tools/build.py                      # model.json -> every page (stdlib only)
node tools/e2e.mjs models/<slug>/index.html tools/link-check.js   # camera-link check
```

## Structure

| Path | What it is |
|---|---|
| `site.json` | title, tagline, description, repo URL, footer |
| `models/<slug>/model.json` | the model: prose, views, specs, publish plan |
| `models/<slug>/index.html` | generated — never hand-edited |
| `models/<slug>/*.glb`, `*.stl` | committed artefacts |
| `assets/site.css`, `assets/viewer.js` | hand-written |
| `assets/vendor/` | model-viewer 4.4.0, pinned, with its licence |
| `tools/build.py` | model.json → every page. Standard library only |
| `tools/publish.py` | modelling repo → GLB/STL. trimesh + pymeshfix |
| `tools/e2e.mjs` | serves the repo, drives Chrome over CDP, asserts in-page |

## Boundaries

- **Generated files are committed and never edited**: `index.html`,
  `models/*/index.html`. Edit `model.json` (content) or `tools/build.py` (layout).
- **No build step at deploy time.** Pages serves the repo root as-is; `.nojekyll`
  stops Jekyll from eating `_`-prefixed names.
- **All URLs are relative** — the site lives under `/<repo>/`, so `/assets/…`
  would 404.
- **`publish.py` never edits the modelling repo.** It only reads from it.
- **A GLB is only published if its mesh is watertight**, except a copy of a
  file that is already web-ready.
- **The site is deliberately not indexed.** `robots.txt` disallows everything
  and every page carries `<meta name="robots" content="noindex, nofollow">`.
  Remove both together, or the crawl behaves differently from the meta tag.
- **Attribution is a licence condition, not a courtesy.** A model adapted from
  someone else's carries a `source` block: title, link, author, licence.
- **Parts of the wording are measured, not guessed**: dimensions, volumes and
  print claims in a `model.json` come from the workshop's gate output.

## Index — read when

| File | Read when |
|---|---|
| `.llms/knowledge/site.md` | changing the viewer, cameras, layout, or the publish path |
| `.llms/knowledge/decisions.md` | wondering why the site is shaped this way |
| `.llms/memory/progress.md` | what is published and what is verified |
