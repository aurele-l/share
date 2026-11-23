# share

3D-printable models I design in code, published as a static site:
**https://aurele-l.github.io/share/**

Every model is an orbitable page with a downloadable STL. The CAD, the tests and
the third-party source meshes live in a private modelling repo — this one holds
only what is published.

## View it locally

Pages need HTTP: a `file://` page cannot fetch its GLB.

```powershell
python -m http.server 8000
# http://127.0.0.1:8000/
```

## Add a model

```powershell
uv sync                                   # once: trimesh + pymeshfix for the converter
uv run tools/publish.py <slug>            # copy artefacts, rebuild pages
```

`publish.py` reads the `publish` block in `models/<slug>/model.json`, copies the
artefacts out of the modelling repo (default `../3d_modelling`), converts STL and
3MF to web GLBs — bed-aligned, Y-up, metres, one flat PBR colour — refuses a mesh
that is not watertight, and rebuilds every page.

```powershell
uv run tools/publish.py zwift-towel-hooks --models-repo ..\3d_modelling
uv run tools/publish.py zwift-towel-hooks --no-build     # copy only
python tools/build.py                                    # HTML only, stdlib
```

No modelling repo to hand? Drop the `publish` block from `model.json`, put the
GLBs and STLs in that folder yourself, and run `tools/build.py`.

## Check the viewer

```powershell
node tools/e2e.mjs models/zwift-towel-hooks/index.html tools/link-check.js
```

Serves the repo, drives headless Chrome over the DevTools protocol and asserts
that the side-by-side tiles really do share one camera (initial framing, drift,
both drag directions, and independence after unlinking). `--size=W,H` and
`--gpu` are available; the default is software GL at 1500×1000.

## Layout

```
site.json                  site title, tagline, repo link, footer
models/<slug>/model.json   title, prose, views, specs, publish plan  (hand-written)
models/<slug>/*.glb        web-ready GLBs                            (committed)
models/<slug>/*.stl        printable download                        (committed)
models/<slug>/index.html   generated
index.html                 generated gallery
assets/                    stylesheet, camera script, vendored model-viewer
tools/build.py             model.json -> every page (standard library)
tools/publish.py           modelling repo -> this repo (trimesh)
tools/e2e.mjs              in-browser check of the camera link
```

Generated HTML is committed, so GitHub Pages serves the repo root as-is with no
build step and no workflow. Edit `model.json`, not the HTML.

Model-viewer is vendored at `assets/vendor/model-viewer.min.js` (4.4.0, with its
licence) so the site does not depend on a CDN.

## Licence

- **Models** — `models/`, including every `.glb` and `.stl`: [CC BY-NC 4.0](LICENSE).
  Print them, modify them, pass them on; no commercial use.
- **Site code** — `assets/`, `tools/`, the build scripts: [MIT](LICENSE-MIT).

The container design is not mine. It is
[*Zwift Ride Containers/Storage*](https://makerworld.com/en/models/2250329-zwift-ride-containers-storage)
by **abuck** on MakerWorld, licensed CC BY-NC 4.0. The tuned variant adds the
towel hooks and the vents; the copy in `models/zwift-towel-hooks/source.glb` is
that mesh with its open boundary filled so it renders as a solid — nothing else
was changed.
