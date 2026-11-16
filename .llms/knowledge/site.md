# Site behaviour — verified facts

## The viewer

`model-viewer` 4.4.0, vendored at `assets/vendor/model-viewer.min.js` (1.07 MB).
model-viewer is Apache-2.0 — `assets/vendor/LICENSE-model-viewer` — and the
bundle's own header names the lit library it contains as BSD-3-Clause. No CDN:
the site works offline and cannot break on an upstream release change.

Things measured in this repo's Chrome (2026-11-16), all of which cost a wrong
assumption first:

| Behaviour | What is true in 4.4.0 |
|---|---|
| `camera-orbit` in markup | **works** — it is not discarded on load. Set it in HTML, not after `load`. |
| `jumpCameraToGoal()` | asynchronous: the camera lands on the **next frame**. Read it back after two rAFs. |
| default `max-camera-orbit` radius | the **initial framing radius**. A shared camera cannot dolly out past the narrower tile's start until this is raised (`auto auto 250%`). |
| `interaction-prompt="auto"` (the default) | its wobble **moves the camera** about 2 s after load, and the value keeps swinging. Always `interaction-prompt="none"`. |
| `camera-controls` | required, or the tile is a still image. |
| `touch-action="pan-y"` | lets a phone scroll past a model instead of trapping the gesture. |

## Camera linking — `assets/viewer.js`

Tiles sharing `data-link="<name>"` form a group; the tile with `data-lead` sets
the first view and every other tile copies it. Copying writes an **absolute**
`theta/phi/radius` in radians and metres plus `cameraTarget`, so the pair shares
one physical camera and the wider part genuinely looks wider. The init copy
retries up to ten times because model-viewer applies the markup orbit a frame or
two after `load` and would otherwise overwrite it.

The mute window around a copy (120 ms) drops the `camera-change` events the copy
itself provokes. A `[data-link-toggle]` checkbox in the markup switches the
copying off; the tiles then move independently.

`node tools/e2e.mjs models/zwift-towel-hooks/index.html tools/link-check.js`
asserts: identical initial camera, no drift over 4 s, both directions of drag,
and independence after unlinking.

## GLB conventions

`tools/publish.py` converts STL/3MF to a web GLB:

- **min Z → 0** (the part sits on the bed), then **Z-up → Y-up**, then
  **×0.001**. CAD is millimetres; model-viewer's camera units are metres.
  Skipping the scale makes every camera number wrong.
- One flat `PBRMaterial` per file; `baseColorFactor` from the artifact's
  `colour`, metallic 0, roughness 0.55.
- A GLB that is already web-ready (a cropped section, a cutaway) is copied
  verbatim with `"copy": true` — a trimesh round-trip would collapse a scene's
  parts and drop their materials.

Bed-aligning is what makes the source and the tuned part share a frame: the 3MF
source sits at z −40…+40, the printed STL at z 0…80, so both land at y 0…0.08 m.

## Search engines

The site is not indexed: `robots.txt` disallows everything, and every generated
page carries `<meta name="robots" content="noindex, nofollow">`. Both are there
because one can be bypassed: a crawler that ignores `Disallow` still obeys the
meta tag, and one that fetches the page reads the tag before the next crawl.
GitHub Pages cannot set `X-Robots-Tag`, so the meta tag is the only header-level
signal available. The public GitHub repo itself is still indexable — nothing on
a free plan prevents that.

## Site paths

GitHub Pages project site → `https://<user>.github.io/<repo>/`. Every asset
reference is relative (`../../assets/…` from a model page). `.nojekyll` at the
root. Files up to 100 MB are accepted; the tracked tree is 5.65 MB, and keeping
it that size is why GLBs are published uncompressed while they stay small.
