// Keep a group of <model-viewer> tiles on one camera.
//
// The tiles' own starting angle is markup (camera-orbit works in model-viewer
// v4 — it is not discarded on load). This file adds the one thing the element
// does not do: tiles sharing a data-link value follow each other, so a
// side-by-side comparison cannot drift onto two different angles.
//
// Model-viewer's interaction prompt is deliberately off in the markup: its
// wobble animation nudges the actual camera a few seconds after load.

const viewers = [...document.querySelectorAll("model-viewer")];

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const frames = (n = 1) =>
  new Promise((resolve) => {
    let left = n;
    const tick = () => {
      left -= 1;
      if (left <= 0) resolve();
      else requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });

async function whenLoaded(mv) {
  for (let i = 0; i < 600 && !mv.loaded; i += 1) await sleep(50);
}

function cameraString(mv) {
  const orbit = mv.getCameraOrbit();
  const parts = [`${orbit.theta}rad`, `${orbit.phi}rad`, `${orbit.radius}m`];
  return parts.join(" ");
}

function applyCamera(dst, orbit, target) {
  dst.cameraOrbit = orbit;
  if (target) dst.cameraTarget = target;
  dst.jumpCameraToGoal();
}

async function linkedTiles(group) {
  const toggle = document.querySelector("[data-link-toggle]");
  const enabled = () => !toggle || toggle.checked;
  const lead = group.find((mv) => mv.hasAttribute("data-lead")) || group[0];

  await Promise.all(group.map(whenLoaded));
  await frames(2);

  const copy = (src, dst) => {
    const target = src.getCameraTarget
      ? `${src.getCameraTarget().x}m ${src.getCameraTarget().y}m ${src.getCameraTarget().z}m`
      : null;
    applyCamera(dst, cameraString(src), target);
  };

  for (const dst of group) if (dst !== lead) copy(lead, dst);
  await frames(3);

  // model-viewer applies the markup camera-orbit a frame or two after `load`,
  // which can land on top of the copy above; converge instead of guessing a
  // delay
  const near = (x, y) =>
    Math.abs(x.theta - y.theta) < 1e-3 &&
    Math.abs(x.phi - y.phi) < 1e-3 &&
    Math.abs(x.radius - y.radius) < 1e-3;
  for (let attempt = 0; attempt < 10; attempt += 1) {
    const goal = lead.getCameraOrbit();
    if (group.every((mv) => near(mv.getCameraOrbit(), goal))) break;
    for (const dst of group) if (dst !== lead) copy(lead, dst);
    await frames(2);
    await sleep(100);
  }

  // from here on, whichever tile the user touches is the source of truth;
  // the mute flag drops the camera-change events our own copy provokes
  let mute = false;
  const push = (src) => {
    if (mute || !enabled()) return;
    mute = true;
    for (const dst of group) if (dst !== src) copy(src, dst);
    setTimeout(() => {
      mute = false;
    }, 120);
  };
  for (const mv of group) {
    mv.addEventListener("camera-change", () => push(mv));
  }
}

for (const name of new Set(viewers.map((mv) => mv.dataset.link).filter(Boolean))) {
  linkedTiles(viewers.filter((mv) => mv.dataset.link === name));
}
