// cdp_mobile_check.mjs — kiểm tra tràn ngang ở khổ điện thoại bằng CDP (Chrome local).
// Dùng: node cdp_mobile_check.mjs <url> [width] [height] [outPng]
const [url, wArg, hArg, outPng] = process.argv.slice(2);
const W = Number(wArg || 390), H = Number(hArg || 844);
const fs = await import("node:fs/promises");

async function target(url) {
  const r = await fetch(`http://127.0.0.1:9222/json/new?${encodeURIComponent(url)}`, { method: "PUT" });
  return r.json();
}
const t = await target("about:blank");
const ws = new WebSocket(t.webSocketDebuggerUrl);
let id = 0;
const pend = new Map();
const logs = [];
ws.addEventListener("message", (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
  else if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") logs.push(JSON.stringify(m.params.args.map(a => a.value ?? a.description)).slice(0, 200));
  else if (m.method === "Log.entryAdded" && m.params.entry.level === "error") logs.push(m.params.entry.text.slice(0, 200));
  else if (m.method === "Runtime.exceptionThrown") logs.push("EXC " + (m.params.exceptionDetails.exception?.description || "").slice(0, 200));
});
const send = (method, params = {}) => new Promise((res) => { const n = ++id; pend.set(n, res); ws.send(JSON.stringify({ id: n, method, params })); });
const evalJs = async (expr) => {
  const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
  return r.result?.result?.value ?? r.result?.exceptionDetails?.exception?.description ?? null;
};
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

await new Promise(r => ws.addEventListener("open", r));
await send("Page.enable"); await send("Runtime.enable"); await send("Log.enable");
await send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 2, mobile: true });
await send("Emulation.setTouchEmulationEnabled", { enabled: true });
await send("Page.navigate", { url });
await sleep(5000);

const report = await evalJs(`(() => {
  const de = document.documentElement;
  const info = (s) => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return { w: Math.round(r.width), x: Math.round(r.x), right: Math.round(r.right) }; };
  return JSON.stringify({
    viewport: [innerWidth, innerHeight],
    docScrollW: de.scrollWidth, bodyScrollW: document.body.scrollWidth,
    overflowX: de.scrollWidth > innerWidth + 2,
    cards: document.querySelectorAll('.card').length,
    gallery: info('.gallery'), firstCard: info('.card'),
  });
})()`);
console.log("KHỔ", W + "x" + H, "→", report);

// mở popup rồi đo lại
await evalJs("document.querySelectorAll('.card').forEach((c,i)=>i===1&&c.click())");
await sleep(1500);
const rep2 = await evalJs(`(() => {
  const de = document.documentElement;
  const info = (s) => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return { w: Math.round(r.width), x: Math.round(r.x), right: Math.round(r.right) }; };
  return JSON.stringify({
    docScrollW: de.scrollWidth, panel: info('.modal-panel'), body: info('.modal-body'),
    stage: info('.stage'), infoCol: info('.info'), overflows: de.scrollWidth > innerWidth + 2,
    stageFits: (() => { const s=document.querySelector('.stage'), p=document.querySelector('.modal-body'); return s && p ? Math.round(s.getBoundingClientRect().width) <= Math.round(p.getBoundingClientRect().width)+1 : null; })(),
    title: (document.querySelector('.modal h2')||{}).textContent,
    facts: document.querySelectorAll('.fact').length, thumbs: document.querySelectorAll('.thumbs img').length,
    descHasLongLine: (() => { const d=document.querySelector('.desc'); return d ? Math.max(...d.innerText.split('\\n').map(l=>l.length)) : null; })()
  });
})()`);
console.log("POPUP →", rep2);
if (outPng) {
  const shot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
  await fs.writeFile(outPng, Buffer.from(shot.result.data, "base64"));
  console.log("ảnh:", outPng);
}
console.log("consoleErrors:", logs.length ? logs : []);
await send("Target.closeTarget", { targetId: t.id }).catch(() => {});
ws.close();
