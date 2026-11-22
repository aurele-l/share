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
  // angles MUST go out in degrees: the orbit parser ignores 'rad'
  // (silently keeping the old camera), which broke every copy until now.
  const deg = (r) => `${(r * 180) / Math.PI}deg`;
  return `${deg(orbit.theta)} ${deg(orbit.phi)} ${orbit.radius}m`;
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
  // the mute flag drops the camera-change events our own copy provokes.
  // try/finally: a throw in copy must never stick the mute flag on,
  // or every later change is dropped and the tiles stay split forever.
  let mute = false;
  const lastTouch = new Map(group.map((mv) => [mv, 0]));
  const push = (src) => {
    if (mute || !enabled()) return;
    mute = true;
    try {
      for (const dst of group) if (dst !== src) copy(src, dst);
    } finally {
      setTimeout(() => {
        mute = false;
      }, 120);
    }
  };
  const sameView = (a, b) => {
    const oa = a.getCameraOrbit();
    const ob = b.getCameraOrbit();
    if (!near(oa, ob)) return false;
    if (!a.getCameraTarget || !b.getCameraTarget) return true;
    const ta = a.getCameraTarget();
    const tb = b.getCameraTarget();
    return (
      Math.abs(ta.x - tb.x) < 1e-4 &&
      Math.abs(ta.y - tb.y) < 1e-4 &&
      Math.abs(ta.z - tb.z) < 1e-4
    );
  };
  for (const mv of group) {
    mv.addEventListener("camera-change", () => {
      lastTouch.set(mv, Date.now());
      push(mv);
    });
  }
  // Heartbeat: heals any divergence the event path drops (a touch gesture
  // fires a burst of camera-change events and the 120 ms mute window eats
  // the middle of the burst; damping tails fire after it clears). Only the
  // most-recently touched tile ever sources a copy, and only while its last
  // touch is under two seconds old - with no fresh interaction the heartbeat
  // stays hands-off so it can never fight the user or pin tiles.
  setInterval(() => {
    if (!enabled()) return;
    let src = null;
    let when = 0;
    for (const entry of lastTouch) {
      if (entry[1] > when) {
        src = entry[0];
        when = entry[1];
      }
    }
    if (!src || Date.now() - when > 2000) return;
    mute = true;
    try {
      for (const dst of group) {
        if (dst !== src && !sameView(src, dst)) copy(src, dst);
      }
    } finally {
      mute = false;
    }
  }, 500);
}

for (const name of new Set(viewers.map((mv) => mv.dataset.link).filter(Boolean))) {
  linkedTiles(viewers.filter((mv) => mv.dataset.link === name));
}
