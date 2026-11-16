# State

## Now

- One model published: `models/zwift-towel-hooks` — original, tuned, section,
  close-up, and `towel-hook-tuned.stl` for download.
- Credited: original design by abuck on MakerWorld, CC BY-NC 4.0 (a `source`
  block under the lede on the model page).
- Not indexed: `robots.txt` disallows everything; every page carries
  `noindex, nofollow`.
- Repo is committed and pushed to https://github.com/aurele-l/shared_3d_models;
  Pages is `main` / root. Site: https://aurele-l.github.io/shared_3d_models/
- Sizes: source 0.88 MB, tuned 0.96 MB, section 15 KB, cut 36 KB, STL 2.66 MB.

## Verified

- Camera link, real Chrome over CDP (`node tools/e2e.mjs … tools/link-check.js`):
  identical initial camera, unchanged after 4 s, both drag directions copy, and
  unlinking leaves the tiles independent.
- `publish.py`: 3MF → boundary fill only (46 556 → 51 022 faces) → GLB;
  the print STL is refused if it is not watertight.
- Pages render at 1440×900, 1440×2300 and 500×900 (Chrome's floor for
  `--window-size`; the earlier 430 capture was cropped, not broken layout).

## Load-bearing gotchas

- model-viewer's interaction prompt moves the camera on its own → always
  `interaction-prompt="none"`.
- Default `max-camera-orbit` radius equals the initial framing radius → a shared
  camera cannot dolly out on the narrower tile; raised to 250%.
- `jumpCameraToGoal()` lands on the next frame, and the markup orbit is applied a
  frame or two after `load` — the init copy retries instead of trusting a delay.
- `--virtual-time-budget` starves requestAnimationFrame: fine for screenshots,
  useless for camera assertions. Use the CDP harness.
