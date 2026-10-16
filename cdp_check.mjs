// cdp_check.mjs — kiểm tra trang gallery bằng CDP của Chrome local (không cần thư viện ngoài).
// Dùng: node cdp_check.mjs <url> <outDir>
const [url, outDir] = process.argv.slice(2);
const fs = await import('node:fs/promises');

const BASE = 'http://127.0.0.1:9222';

async function newTarget(u) {
  const r = await fetch(`${BASE}/json/new?${encodeURIComponent(u)}`, { method: 'PUT' });
  if (!r.ok) throw new Error(`json/new HTTP ${r.status}`);
  return r.json();
}

function connect(wsUrl) {
  const ws = new WebSocket(wsUrl);
  let id = 0;
  const pending = new Map();
  const events = [];
  ws.addEventListener('message', (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result);
    } else if (msg.method) {
      events.push(msg);
    }
  });
  const ready = new Promise((res, rej) => {
    ws.addEventListener('open', res);
    ws.addEventListener('error', rej);
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const mid = ++id;
    pending.set(mid, { resolve, reject });
    ws.send(JSON.stringify({ id: mid, method, params }));
    setTimeout(() => { if (pending.has(mid)) { pending.delete(mid); reject(new Error('timeout ' + method)); } }, 30000);
  });
  return { ws, send, ready, events };
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const t = await newTarget(url);
const c = connect(t.webSocketDebuggerUrl);
await c.ready;
await c.send('Runtime.enable');
await c.send('Page.enable');
await c.send('Log.enable');
const evalJs = async (expr) => {
  const r = await c.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) return { error: r.exceptionDetails.text + ' ' + (r.exceptionDetails.exception?.description || '') };
  return r.result.value;
};

await sleep(1500);
const out = {};
out.title = await evalJs('document.title');
out.cards = await evalJs("document.querySelectorAll('.card').length");
out.countLabel = await evalJs("document.querySelector('#count')?.textContent");
out.thumbImgs = await evalJs("document.querySelectorAll('.thumb img').length");

// 1) slideshow thumbnail: chờ tối đa 7s xem có thẻ nào chuyển sang ảnh 2
let slideSeen = 0;
for (let i = 0; i < 14; i++) {
  slideSeen = await evalJs("document.querySelectorAll('.card.slide').length");
  if (slideSeen > 0) break;
  await sleep(500);
}
out.slideCardsAfter7s = slideSeen;

// 2) popup chi tiết
await evalJs("document.querySelector('.card').click()");
await sleep(400);
out.modalOpen = await evalJs("!document.getElementById('modal').hidden");
out.modalTitle = await evalJs("document.querySelector('#m-title').textContent");
out.modalFacts = await evalJs("document.querySelectorAll('#m-facts .fact').length");
out.modalThumbs = await evalJs("document.querySelectorAll('#m-thumbs img').length");
out.modalCounter1 = await evalJs("document.querySelector('#m-counter').textContent");
await evalJs("document.querySelector('#m-next').click()");
await sleep(300);
out.modalCounter2 = await evalJs("document.querySelector('#m-counter').textContent");

// 3) lightbox từ ảnh trong popup
await evalJs("document.querySelector('#m-img').click()");
await sleep(600);
out.lightboxOpen = await evalJs("!document.getElementById('lightbox').hidden");
out.lbCounter = await evalJs("document.querySelector('#lb-counter').textContent");
out.lbStrip = await evalJs("document.querySelectorAll('#lb-strip img').length");
out.lbNatural = await evalJs("(()=>{const i=document.getElementById('lb-img');return i.naturalWidth+'x'+i.naturalHeight})()");
await evalJs("document.querySelector('#lb-in').click()");
await sleep(200);
out.scaleAfterZoomIn = await evalJs("window.__gallery.state.lb.scale");
out.imgTransform = await evalJs("document.getElementById('lb-img').style.transform");
await evalJs("document.querySelector('#lb-reset').click()");
out.scaleAfterReset = await evalJs("window.__gallery.state.lb.scale");

// screenshot lightbox
try {
  await fs.mkdir(outDir, { recursive: true });
  let shot = await c.send('Page.captureScreenshot', { format: 'png' });
  await fs.writeFile(`${outDir}/lightbox.png`, Buffer.from(shot.data, 'base64'));
} catch (e) { out.shotLightbox = 'LỖI ' + e.message; }

// đóng lightbox (Esc) rồi chụp popup, rồi đóng popup
await evalJs("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}))");
await sleep(250);
out.lightboxClosedByEsc = await evalJs("document.getElementById('lightbox').hidden");
try {
  let shot = await c.send('Page.captureScreenshot', { format: 'png' });
  await fs.writeFile(`${outDir}/popup.png`, Buffer.from(shot.data, 'base64'));
} catch (e) { out.shotPopup = 'LỖI ' + e.message; }
await evalJs("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}))");
await sleep(250);
out.modalClosedByEsc = await evalJs("document.getElementById('modal').hidden");

// 4) search lọc
await evalJs("(()=>{const s=document.querySelector('#search'); s.value='Lữ Bố'; s.dispatchEvent(new Event('input'));})()");
await sleep(300);
out.cardsAfterSearch = await evalJs("document.querySelectorAll('.card').length");
await evalJs("(()=>{const s=document.querySelector('#search'); s.value=''; s.dispatchEvent(new Event('input'));})()");
await sleep(300);
out.cardsAfterClear = await evalJs("document.querySelectorAll('.card').length");

// screenshot gallery
try {
  let shot = await c.send('Page.captureScreenshot', { format: 'png' });
  await fs.writeFile(`${outDir}/gallery.png`, Buffer.from(shot.data, 'base64'));
} catch (e) { out.shotGallery = 'LỖI ' + e.message; }

// lỗi console
out.consoleErrors = c.events.filter((e) => e.method === 'Log.entryAdded' && e.params.entry.level === 'error')
  .map((e) => e.params.entry.text).slice(0, 10);
out.exceptions = c.events.filter((e) => e.method === 'Runtime.exceptionThrown')
  .map((e) => e.params.exceptionDetails.text).slice(0, 10);

console.log(JSON.stringify(out, null, 1));
await fetch(`${BASE}/json/close/${t.id}`).catch(() => {});
process.exit(0);
