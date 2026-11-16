// Assert the comparison tiles share one camera.
//
//   node tools/e2e.mjs models/zwift-towel-hooks/index.html tools/link-check.js
//
// Pass if, in order: both tiles start on the same camera, the camera has not
// moved 4 s later, dragging either tile moves both, and switching the checkbox
// off leaves them independent.

(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const views = [...document.querySelectorAll("model-viewer")];
  const [a, b] = views;
  for (let i = 0; i < 200; i++) {
    if (a.loaded && b.loaded) break;
    await sleep(100);
  }
  await sleep(1200);

  const orbit = (v) => {
    const o = v.getCameraOrbit();
    return [o.theta, o.phi, o.radius].map((n) => Math.round(n * 10000) / 10000);
  };
  const same = (x, y) => x.every((n, i) => Math.abs(n - y[i]) < 0.002);
  const out = { viewers: views.length, checks: {} };

  out.checks.initial = same(orbit(a), orbit(b)) ? "pass" : `FAIL ${orbit(a)} vs ${orbit(b)}`;
  await sleep(4000);
  out.checks.stable = same(orbit(a), orbit(b)) ? "pass" : `FAIL ${orbit(a)} vs ${orbit(b)}`;

  a.cameraOrbit = "130deg 55deg 90%";
  a.jumpCameraToGoal();
  await sleep(1200);
  out.checks.dragFirst = same(orbit(a), orbit(b)) ? "pass" : `FAIL ${orbit(a)} vs ${orbit(b)}`;

  b.cameraOrbit = "300deg 60deg 95%";
  b.jumpCameraToGoal();
  await sleep(1200);
  out.checks.dragSecond = same(orbit(a), orbit(b)) ? "pass" : `FAIL ${orbit(a)} vs ${orbit(b)}`;

  document.querySelector("[data-link-toggle]").checked = false;
  a.cameraOrbit = "10deg 80deg 120%";
  a.jumpCameraToGoal();
  await sleep(1200);
  out.checks.unlinked = !same(orbit(a), orbit(b)) ? "pass" : `FAIL both at ${orbit(a)}`;

  out.camera = { a: orbit(a), b: orbit(b) };
  out.result = Object.values(out.checks).every((c) => c === "pass") ? "pass" : "FAIL";
  return out;
})()
