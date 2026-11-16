# Decisions

Append-only. A changed decision gets a new D naming the one it supersedes.

## D1 — Static site, generated output committed, no CI build

**Chosen:** `index.html` and `models/*/index.html` are generated locally and
committed. GitHub Pages serves `main` / root as-is.
**Rejected:** a Pages workflow that builds on push.
**Why:** the output is the artefact; a workflow adds a failure mode between a
commit and a live page, and needs a Node/Python environment at deploy time for
what is 40 lines of string formatting. Cost: generated HTML is in the diff, so
edit `model.json`, never the HTML.

## D2 — model-viewer vendored, not from a CDN

**Chosen:** `assets/vendor/model-viewer.min.js`, version pinned in the filename
comment and in `.llms/knowledge/site.md`, package licence alongside.
**Rejected:** the jsDelivr `<script>` the modelling repo uses.
**Why:** the site must work offline and must not change under it when upstream
publishes. Cost: 1.07 MB in the repo, and an upgrade is a deliberate copy.

## D3 — One `model.json` per model is the only hand-written page input

**Chosen:** `tools/build.py` turns `models/<slug>/model.json` into that model's
page and the gallery card. Standard library only.
**Rejected:** hand-written HTML per model; a single site-wide manifest.
**Why:** adding a model must not mean copying layout code, and a per-model file
cannot drift out of sync with the folder it describes. Cost: the template lives
in Python, so a layout change is a code change.

## D4 — `publish.py` lives here, with its own uv environment

**Chosen:** this repo owns the conversion (STL/3MF → web GLB) and reads the
private modelling repo through a `publish` block in `model.json`.
**Rejected:** a publisher in the modelling repo writing into `../shared_3d_models`.
**Why:** the public repo stays self-contained and reproducible from a clone; the
workshop needs no site-specific code, and `publish.py` only ever reads from it.
Cost: a second venv (trimesh, numpy, networkx, scipy, pymeshfix), pinned to the
workshop's versions so the exported GLBs match its own viewer.

## D5 — Comparison tiles share one physical camera

**Chosen:** a `data-lead` tile sets the view; every other tile in the group
copies absolute `theta/phi/radius` + `cameraTarget` on each change and at init
(retrying until it sticks). `max-camera-orbit` is raised to 250% and the
interaction prompt is off.
**Rejected:** syncing only the angle; syncing percentages; leaving each tile on
its own markup orbit.
**Why:** the two models are the same object at 1:1, so one camera makes the
comparison honest — the wider part really looks wider. Percentages would hide
the 28 mm width difference by normalising each tile. Measured reasons for the
two attributes: the default maximum radius is the initial framing radius (the
shared camera could not dolly out on the narrower tile), and the interaction
prompt's wobble moves the camera seconds after load.

## D6 — The third-party source mesh is published

**Chosen:** `source.glb` (the Zwift container as shipped, repaired by boundary
fill only) is on the page, because seeing the part next to the tuned one is the
point of the page.
**Rejected:** publishing only the derived part.
**Why:** explicit request (2026-11-16). This overrides the workshop's default
(`3d_modelling/.gitignore`: third-party source models are "never ours to
publish"). It is Zwift's geometry, redistributed for reference: if that becomes
a problem, delete the `source.glb` artifact and the compare view that shows it —
one edit in `model.json`, one `publish.py` run. The printable part is ours and
is unaffected.
