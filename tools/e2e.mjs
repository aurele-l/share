// Assert page behaviour in a real browser, without a test framework.
//
//   node tools/e2e.mjs <page> <expression-file> [wait-ms] [--size=W,H] [--gpu]
//
// Serves the repo on a loopback port, drives headless Chrome over the DevTools
// protocol, and evaluates the expression file in the page after real time has
// passed. Prints the result as JSON, plus any page exceptions.
//
// Why not --screenshot + --virtual-time-budget: virtual time starves
// requestAnimationFrame, which is what model-viewer's camera runs on, so camera
// assertions pass or fail on timing rather than on the code. This runs in real
// time.

import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const MIME = {
  ".html": "text/html", ".js": "text/javascript", ".css": "text/css",
  ".glb": "model/gltf-binary", ".svg": "image/svg+xml", ".stl": "model/stl",
  ".json": "application/json",
};

const args = process.argv.slice(2);
const positional = args.filter((a) => !a.startsWith("--"));
const [page, exprFile, waitArg] = positional;
if (!page || !exprFile) {
  console.error("usage: node tools/e2e.mjs <page> <expression-file> [wait-ms] [--size=W,H] [--gpu]");
  process.exit(2);
}
const expr = fs.readFileSync(path.resolve(ROOT, exprFile), "utf8");
const waitMs = Number(waitArg || 4000);
const gpu = args.includes("--gpu");
const size = (args.find((a) => a.startsWith("--size=")) || "--size=1500,1000").slice(7);

const server = http.createServer((req, res) => {
  const rel = decodeURIComponent(req.url.split("?")[0]);
  const file = path.join(ROOT, rel === "/" ? "index.html" : rel);
  if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404).end("not found");
    return;
  }
  res.writeHead(200, { "content-type": MIME[path.extname(file)] || "application/octet-stream" });
  fs.createReadStream(file).pipe(res);
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const origin = `http://127.0.0.1:${server.address().port}`;

const profile = path.join(process.env.TEMP, `cdp-${Date.now()}`);
const chrome = spawn(CHROME, [
  "--headless=new", "--hide-scrollbars",
  // software GL is the default: deterministic, and it renders these GLBs fine
  ...(gpu ? [] : ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"]),
  `--window-size=${size}`,
  "--no-first-run", "--no-default-browser-check",
  "--remote-debugging-port=0", `--user-data-dir=${profile}`, "about:blank",
], { stdio: "ignore" });

const portFile = path.join(profile, "DevToolsActivePort");
for (let i = 0; i < 200 && !fs.existsSync(portFile); i++) {
  await new Promise((r) => setTimeout(r, 100));
}
const [debugPort] = fs.readFileSync(portFile, "utf8").split("\n");
const targets = await (await fetch(`http://127.0.0.1:${debugPort}/json/list`)).json();
const target = targets.find((t) => t.type === "page");

const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r, { once: true }));

let nextId = 0;
const pending = new Map();
const exceptions = [];
ws.addEventListener("message", (event) => {
  const msg = JSON.parse(event.data);
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg);
    pending.delete(msg.id);
  } else if (msg.method === "Runtime.exceptionThrown") {
    const detail = msg.params.exceptionDetails;
    exceptions.push(`${detail.text} ${detail.exception?.description || ""}`.trim());
  }
});
const send = (method, params = {}) =>
  new Promise((resolve) => {
    const id = ++nextId;
    pending.set(id, resolve);
    ws.send(JSON.stringify({ id, method, params }));
  });

await send("Runtime.enable");
await send("Page.enable");
await send("Page.navigate", { url: `${origin}/${page}` });
await new Promise((r) => setTimeout(r, waitMs));

const result = await send("Runtime.evaluate", {
  expression: expr, awaitPromise: true, returnByValue: true,
});

const value = result.result?.result?.value ?? result.result?.exceptionDetails ?? result.result;
console.log(JSON.stringify(value, null, 2));
if (exceptions.length) console.log("EXCEPTIONS:", JSON.stringify(exceptions, null, 2));

ws.close();
chrome.kill();
server.close();
