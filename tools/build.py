#!/usr/bin/env python3
"""Generate every page of the site from `models/<slug>/model.json`.

Standard library only: the GLBs are committed, so a fresh clone can rebuild the
HTML without installing anything.

    python tools/build.py

Output is deterministic; commit it. GitHub Pages serves the repo root as-is, so
there is no build step at deploy time and `file://` is the only thing that does
not work (a GLB fetch needs HTTP).
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_models() -> list[tuple[str, dict]]:
    """Every models/<slug>/model.json, in gallery order."""
    found = [(cfg.parent.name, load_json(cfg)) for cfg in MODELS.glob("*/model.json")]
    found.sort(key=lambda item: (item[1].get("order", 999), item[0]))
    return found


def model_url(slug: str) -> str:
    return f"models/{slug}/"


# ---------------------------------------------------------------- fragments


def view_figure(view: dict, prefix: str, link: str = "", detail: bool = False) -> str:
    attrs = [
        f'src="{esc(prefix + view["glb"])}"',
        f'alt="{esc(view.get("alt") or view.get("label") or "3D model")}"',
        "camera-controls",
        'touch-action="pan-y"',
        # the default maximum radius is the initial framing distance, which would
        # clamp the shared camera on the narrower of two comparison tiles
        'max-camera-orbit="auto auto 250%"',
        'shadow-intensity="1.2"',
        'shadow-softness="0.85"',
        'tone-mapping="aces"',
        # the prompt's wobble drags the camera a little on its own, and it fires
        # seconds after load, so it is never worth the drift
        'interaction-prompt="none"',
        f'exposure="{esc(view.get("exposure", "0.9"))}"',
    ]
    if view.get("orbit"):
        attrs.append(f'camera-orbit="{esc(view["orbit"])}"')
    if view.get("target"):
        attrs.append(f'camera-target="{esc(view["target"])}"')
    if view.get("ortho"):
        attrs.append('camera-projection="orthographic"')
    if link:
        attrs.append(f'data-link="{esc(link)}"')
    if view.get("lead"):
        attrs.append("data-lead")
    if view.get("lazy"):
        attrs.append('loading="lazy"')

    caption = f'<b>{esc(view["label"])}</b>'
    if view.get("detail"):
        caption += f'<span>{esc(view["detail"])}</span>'

    cls = "view detail" if detail else "view"
    return (
        f'<figure class="{cls}">\n'
        f'  <model-viewer {" ".join(attrs)}></model-viewer>\n'
        f"  <figcaption>{caption}</figcaption>\n"
        f"</figure>"
    )


def pair_block(
    *, title: str, note: str, views: list[dict], prefix: str, link: str = "",
    detail: bool = False, toggle: dict | None = None,
) -> str:
    head = f"<h2>{esc(title)}</h2>" if title else ""
    if toggle:
        head = (
            '<div class="block-head">'
            f"{head}"
            f'<label class="toggle"><input type="checkbox" data-link-toggle '
            f'{esc(toggle.get("checked", "checked"))}> {esc(toggle["label"])}</label>'
            "</div>"
        )
    body = "".join(view_figure(v, prefix, link, detail) for v in views)
    note_html = f'<p class="block-note">{esc(note)}</p>' if note else ""
    cls = "pair detail" if detail else "pair"
    return f'<section class="block">{head}{note_html}<div class="{cls}">{body}</div></section>'


def page(*, site: dict, title: str, description: str, prefix: str, body: str) -> str:
    full = title if title == site["title"] else f"{title} \u2014 {site['title']}"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full)}</title>
<meta name="description" content="{esc(description)}">
<meta name="color-scheme" content="dark">
<meta name="robots" content="noindex, nofollow">
<meta property="og:title" content="{esc(full)}">
<meta property="og:description" content="{esc(description)}">
<link rel="icon" href="{prefix}assets/icon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{prefix}assets/site.css">
<script type="module" src="{prefix}assets/vendor/model-viewer.min.js"></script>
<script type="module" src="{prefix}assets/viewer.js"></script>
</head>
<body>
<header class="site-head"><div class="wrap">
  <a class="mark" href="{prefix}index.html">{esc(site["title"])}</a>
  <nav><a href="{esc(site["repo"])}">GitHub</a></nav>
</div></header>
{body}
<footer class="site-foot"><div class="wrap"><p>{esc(site["footer"])}</p></div></footer>
</body>
</html>
"""


# ---------------------------------------------------------------- pages


def source_line(source: dict) -> str:
    """Attribution for a model that is an adaptation of someone else's work."""
    title = esc(source["title"])
    if source.get("url"):
        title = f'<a href="{esc(source["url"])}">{title}</a>'
    line = f"Adapted from {title}"
    if source.get("author"):
        line += f' by {esc(source["author"])}'
    if source.get("site"):
        line += f' on {esc(source["site"])}'
    if source.get("licence"):
        licence = esc(source["licence"])
        if source.get("licenceUrl"):
            licence = f'<a href="{esc(source["licenceUrl"])}">{licence}</a>'
        line += f", licensed {licence}"
    return f'<p class="source">{line}.</p>'


def render_model(data: dict, site: dict) -> str:
    prefix = "../../"
    parts = [
        '<main class="wrap">',
        '<div class="title-block">',
    ]
    if data.get("date"):
        parts.append(f'<p class="eyebrow">{esc(data["date"])}</p>')
    parts.append(f'<h1>{esc(data["title"])}</h1>')
    if data.get("lede"):
        parts.append(f'<p class="lede">{esc(data["lede"])}</p>')
    if data.get("source"):
        parts.append(source_line(data["source"]))
    parts.append("</div>")

    downloads = data.get("downloads") or []
    if downloads:
        buttons = "".join(
            f'<a class="button" href="{esc(d["file"])}" download>{esc(d["label"])}'
            + (f'<span>{esc(d["size"])}</span>' if d.get("size") else "")
            + "</a>"
            for d in downloads
        )
        parts.append(f'<div class="actions">{buttons}</div>')

    compare = data.get("compare")
    if compare:
        parts.append(
            pair_block(
                title=compare.get("title", ""),
                note=compare.get("note", ""),
                views=compare["views"],
                prefix="",
                link="compare",
                toggle=compare.get("toggle", {"label": "cameras linked"}),
            )
        )

    for group in data.get("groups") or []:
        parts.append(
            pair_block(
                title=group.get("title", ""),
                note=group.get("note", ""),
                views=group["views"],
                prefix="",
                detail=True,
            )
        )

    cols = []
    if data.get("specs"):
        rows = "".join(
            f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in data["specs"]
        )
        cols.append(f'<section><h2>Specs</h2><dl class="specs">{rows}</dl></section>')
    if data.get("notes"):
        paras = "".join(f"<p>{esc(p)}</p>" for p in data["notes"])
        cols.append(f'<section class="prose"><h2>Why it is built this way</h2>{paras}</section>')
    if cols:
        parts.append(f'<div class="cols">{"".join(cols)}</div>')

    parts.append("</main>")
    return page(
        site=site,
        title=data["title"],
        description=data.get("summary") or data.get("lede") or site["description"],
        prefix=prefix,
        body="\n".join(parts),
    )


def render_gallery(models: list[tuple[str, dict]], site: dict) -> str:
    cards = []
    for slug, data in models:
        thumb = data.get("thumb") or (data.get("compare", {}).get("views", [{}])[0].get("glb"))
        viewer = (
            f'<model-viewer src="{esc(model_url(slug) + thumb)}" '
            f'alt="{esc(data["title"])}" '
            'auto-rotate auto-rotate-delay="0" rotation-per-second="12deg" '
            'shadow-intensity="1.1" shadow-softness="0.85" tone-mapping="aces" '
            'exposure="0.9" interaction-prompt="none" loading="lazy" '
            f'camera-orbit="{esc(data.get("thumbOrbit", "25deg 72deg 105%"))}">'
            "</model-viewer>"
        )
        meta = f'<p class="card-meta">{esc(data["meta"])}</p>' if data.get("meta") else ""
        cards.append(
            f'<a class="card" href="{esc(model_url(slug))}">'
            f"{viewer}"
            '<div class="card-body">'
            f'<h2>{esc(data["title"])}</h2>'
            f'<p>{esc(data.get("summary", ""))}</p>'
            f"{meta}"
            "</div></a>"
        )

    body = (
        '<main class="wrap">'
        '<div class="intro">'
        f'<h1>{esc(site["tagline"])}</h1>'
        f'<p>{esc(site["description"])}</p>'
        "</div>"
        f'<div class="cards">{"".join(cards)}</div>'
        "</main>"
    )
    return page(
        site=site,
        title=site["title"],
        description=site["description"],
        prefix="",
        body=body,
    )


def build(*, verbose: bool = True) -> list[Path]:
    site = load_json(ROOT / "site.json")
    models = load_models()
    written = []

    for slug, data in models:
        target = MODELS / slug / "index.html"
        target.write_text(render_model(data, site), encoding="utf-8")
        written.append(target)

    gallery = ROOT / "index.html"
    gallery.write_text(render_gallery(models, site), encoding="utf-8")
    written.append(gallery)

    if verbose:
        for path in written:
            print(f"  {path.relative_to(ROOT)}")
        print(f"{len(models)} model(s), {len(written)} page(s)")
    return written


def main() -> int:
    try:
        build()
    except KeyError as exc:
        print(f"model.json is missing a required field: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
