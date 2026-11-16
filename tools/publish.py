#!/usr/bin/env python3
"""Copy a model project's artefacts into this repo, then rebuild the pages.

The modelling repo is the workshop: it holds the CAD, the source meshes and the
tests. This one holds only what gets shared. `publish.py` is the one-way door
between them, driven by the `publish` block in `models/<slug>/model.json`:

    uv run tools/publish.py zwift-towel-hooks
    uv run tools/publish.py zwift-towel-hooks --models-repo ..\\3d_modelling
    uv run tools/publish.py zwift-towel-hooks --no-build

An artefact is either copied verbatim (`"copy": true`, for a GLB that is already
web-ready, or a printable STL) or converted to a web GLB: bed-aligned, Y-up,
metres, flat PBR colour — model-viewer's camera units are metres and CAD is in
millimetres, so skipping that scale makes every camera number wrong.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"

# 3MF core spec namespace, and the Z-up (mm) -> Y-up (m) basis change.
NS = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
UP = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]])

DEFAULT_COLOUR = [0.86, 0.87, 0.89]


# ---------------------------------------------------------------- loading


def load_3mf(path: Path) -> trimesh.Trimesh:
    """The mesh inside a 3MF, without trimesh's scene graph (no lxml needed)."""
    with zipfile.ZipFile(path) as z:
        models = [n for n in z.namelist() if n.startswith("3D/") and n.endswith(".model")]
        models.sort(key=lambda n: len(z.read(n)), reverse=True)
        root = ET.fromstring(z.read(models[0]))
    mesh_el = root.find(".//m:mesh", NS)
    verts = np.array(
        [[float(e.get("x")), float(e.get("y")), float(e.get("z"))]
         for e in mesh_el.findall(".//m:vertex", NS)]
    )
    faces = np.array(
        [[int(e.get("v1")), int(e.get("v2")), int(e.get("v3"))]
         for e in mesh_el.findall(".//m:triangle", NS)]
    )
    return trimesh.Trimesh(vertices=verts, faces=faces, process=False)


def load_mesh(path: Path) -> trimesh.Trimesh:
    if path.suffix.lower() == ".3mf":
        return load_3mf(path)
    mesh = trimesh.load(str(path), force="mesh")
    if isinstance(mesh, trimesh.Scene):
        mesh = mesh.to_mesh()
    return mesh


def repair_fill(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Close the open boundary and nothing else.

    `pymeshfix.clean()` would also resolve self-intersections — and deletes
    embossing, cut-outs and walls on the way. Filling boundaries leaves every
    surface face where it was; the zero-volume slivers it emits are dropped.
    """
    import pymeshfix

    tm = pymeshfix.PyTMesh()
    tm.set_quiet(1)
    tm.load_array(
        np.asarray(mesh.vertices, dtype=np.float64),
        np.asarray(mesh.faces, dtype=np.int32),
    )
    tm.fill_small_boundaries()
    verts, faces = tm.return_arrays()
    filled = trimesh.Trimesh(vertices=verts, faces=faces, process=True)
    parts = filled.split(only_watertight=False)
    solid = max(parts, key=lambda p: p.volume)
    solid.fix_normals()
    return solid


# ---------------------------------------------------------------- writing


def to_web_glb(mesh: trimesh.Trimesh, path: Path, colour) -> trimesh.Trimesh:
    """Bed-aligned, Y-up, metres, one flat PBR colour."""
    m = mesh.copy()
    m.vertices = np.asarray(m.vertices, dtype=float)
    m.vertices[:, 2] -= float(m.bounds[0][2])  # min Z sits on the bed
    m.vertices = m.vertices @ UP.T
    m.apply_scale(0.001)
    m.visual = trimesh.visual.TextureVisuals(
        material=trimesh.visual.material.PBRMaterial(
            baseColorFactor=[*colour, 1.0], metallicFactor=0.0, roughnessFactor=0.55
        )
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    m.export(path)
    return m


def describe(label: str, path: Path, mesh: trimesh.Trimesh | None = None) -> str:
    size = path.stat().st_size / 1024 / 1024
    bits = [f"{label:22s} {size:6.2f} MB"]
    if mesh is not None:
        ext = mesh.extents
        bits.append(f"{ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f} mm")
        bits.append(f"{mesh.volume / 1000:.2f} cm3")
        bits.append(f"{len(mesh.faces)} faces")
        bits.append("watertight" if mesh.is_watertight else "NOT watertight")
    return "  ".join(bits)


# ---------------------------------------------------------------- publish


def publish(slug: str, models_repo: Path, build_after: bool) -> int:
    cfg_path = MODELS / slug / "model.json"
    if not cfg_path.exists():
        print(f"no such model: {cfg_path}", file=sys.stderr)
        return 1

    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    plan = data.get("publish") or {}
    project = plan.get("project", slug)
    project_dir = (models_repo / project).resolve()
    if not project_dir.exists():
        print(f"project not found: {project_dir}", file=sys.stderr)
        print("pass --models-repo <path to the modelling repo>", file=sys.stderr)
        return 1

    model_dir = MODELS / slug
    print(f"{slug}  <-  {project_dir}")
    failed = False

    for artifact in plan.get("artifacts", []):
        src = project_dir / artifact["src"]
        dest = model_dir / artifact["dest"]
        if not src.exists():
            print(f"  MISSING  {src}", file=sys.stderr)
            failed = True
            continue

        if artifact.get("copy"):
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            print(describe(artifact["dest"], dest))
            continue

        mesh = load_mesh(src)
        if artifact.get("repair"):
            before = len(mesh.faces)
            mesh = repair_fill(mesh)
            print(f"  repaired {before} -> {len(mesh.faces)} faces")

        if not mesh.is_watertight:
            print(f"  REFUSED  {src}: mesh is not watertight", file=sys.stderr)
            failed = True
            continue

        web = to_web_glb(mesh, dest, artifact.get("colour", DEFAULT_COLOUR))
        # report the size the viewer sees: Y-up metres scaled back to millimetres
        mm = web.extents * 1000.0
        print(
            f"{describe(artifact['dest'], dest)}\n"
            f"  {'':22s} viewer size X x Z x Y  {mm[0]:.1f} x {mm[2]:.1f} x {mm[1]:.1f} mm"
        )

    if failed:
        print("publish aborted; nothing was rebuilt", file=sys.stderr)
        return 1

    if build_after:
        from build import build

        print("building pages")
        build()

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slug", help="model folder name under models/")
    ap.add_argument(
        "--models-repo",
        type=Path,
        default=ROOT.parent / "3d_modelling",
        help="path to the modelling repo (default: ../3d_modelling)",
    )
    ap.add_argument("--no-build", action="store_true", help="only copy artefacts")
    args = ap.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    return publish(args.slug, args.models_repo, not args.no_build)


if __name__ == "__main__":
    sys.exit(main())
