/* TOYz product gallery — vanilla JS, không phụ thuộc thư viện ngoài. */
'use strict';

const state = {
  products: [],
  view: [],
  card: null,       // sản phẩm đang mở popup
  index: 0,         // ảnh đang xem trong popup
  lb: { open: false, scale: 1, tx: 0, ty: 0, dragging: false, sx: 0, sy: 0 }
};

const $ = (s) => document.querySelector(s);
const gallery = $('#gallery');
const modal = $('#modal');
const lightbox = $('#lightbox');

/* ---------------- nạp dữ liệu ---------------- */
async function boot() {
  try {
    const res = await fetch('data/products.json', { cache: 'no-store' });
    state.products = await res.json();
  } catch (e) {
    console.error('Không đọc được data/products.json', e);
    state.products = [];
  }
  state.view = state.products.slice();
  render();
  startSlideshow();
}

/* ---------------- gallery ---------------- */
function money(v) {
  if (!v && v !== 0) return '';
  return new Intl.NumberFormat('vi-VN').format(v) + 'đ';
}

function render() {
  gallery.innerHTML = '';
  const frag = document.createDocumentFragment();
  state.view.forEach((p, i) => {
    const card = document.createElement('article');
    card.className = 'card';
    card.dataset.idx = String(i);
    const imgs = p.thumbs || p.images || [];
    const a = imgs[0] || '';
    const b = imgs[1] || a;
    card.innerHTML = `
      <div class="thumb">
        ${a ? `<img class="a" src="${a}" alt="${escapeAttr(p.title)}" loading="lazy" decoding="async">
               <img class="b" src="${b}" alt="" loading="lazy" decoding="async">`
            : `<span class="ph">không có ảnh</span>`}
        <span class="pill ${p.badge === 'PRE-ORDER' ? '' : 'sold'}">${p.badge || 'PRE-ORDER'}</span>
      </div>
      <div class="card-info">
        <h3>${escapeHtml(p.title)}</h3>
        ${p.price ? `<div class="price">${p.price}</div>` : ''}
        <div class="sub">${escapeHtml(p.subtitle || '')}</div>
      </div>`;
    card.addEventListener('click', () => openModal(p));
    frag.appendChild(card);
  });
  gallery.appendChild(frag);
  $('#count').textContent = `${state.view.length} sản phẩm`;
  $('#empty').hidden = state.view.length > 0;
}

/* slideshow thumbnail: 2 ảnh luân phiên, mỗi thẻ lệch pha nhau */
function startSlideshow() {
  setInterval(() => {
    const now = Date.now();
    document.querySelectorAll('.card').forEach((card, i) => {
      if (card.querySelectorAll('.thumb img').length < 2) return;
      const phase = i * 700;
      const showSecond = Math.floor(((now + phase) % 9000) / 4500) === 1;
      card.classList.toggle('slide', showSecond);
    });
  }, 500);
}

/* ---------------- search ---------------- */
$('#search').addEventListener('input', (e) => {
  const q = e.target.value.trim().toLowerCase();
  state.view = !q ? state.products.slice() : state.products.filter((p) =>
    (p.title + ' ' + (p.subtitle || '') + ' ' + (p.sku || '') + ' ' + (p.desc || '')).toLowerCase().includes(q));
  render();
});

/* ---------------- popup chi tiết ---------------- */
function openModal(p) {
  state.card = p;
  state.index = 0;
  $('#m-title').textContent = p.title;
  $('#m-badge').textContent = p.badge || 'PRE-ORDER';
  $('#m-desc').textContent = p.desc || '';
  $('#m-link').href = p.link || '#';
  $('#m-date').textContent = p.date ? 'Đăng ngày ' + p.date : '';
  $('#m-facts').innerHTML = (p.facts || []).map((f) =>
    `<div class="fact"><b>${escapeHtml(f.k)}</b><span>${escapeHtml(f.v)}</span></div>`).join('');
  $('#m-thumbs').innerHTML = (p.thumbs || p.images || []).map((src, i) =>
    `<img src="${src}" data-i="${i}" class="${i === 0 ? 'on' : ''}" alt="">`).join('');
  $('#m-thumbs').querySelectorAll('img').forEach((el) =>
    el.addEventListener('click', () => setIndex(+el.dataset.i)));
  modal.hidden = false;
  document.body.style.overflow = 'hidden';
  showImage(0);
}

function setIndex(i) {
  const n = (state.card?.images || []).length || 1;
  state.index = (i + n) % n;
  showImage(state.index);
}

function showImage(i) {
  const p = state.card;
  if (!p) return;
  const imgs = p.images || [];
  $('#m-img').src = imgs[i] || '';
  $('#m-counter').textContent = imgs.length ? `${i + 1} / ${imgs.length}` : '';
  $('#m-thumbs').querySelectorAll('img').forEach((el) =>
    el.classList.toggle('on', +el.dataset.i === i));
}

function closeModal() {
  modal.hidden = true;
  document.body.style.overflow = '';
  state.card = null;
}

modal.addEventListener('click', (e) => { if (e.target.closest('[data-close]')) closeModal(); });
$('#m-prev').addEventListener('click', (e) => { e.stopPropagation(); setIndex(state.index - 1); });
$('#m-next').addEventListener('click', (e) => { e.stopPropagation(); setIndex(state.index + 1); });
$('#m-stage').addEventListener('click', (e) => {
  if (e.target.closest('.nav')) return;
  openLightbox(state.index);
});

/* ---------------- lightbox ---------------- */
function openLightbox(i) {
  if (!state.card) return;
  state.index = i;
  state.lb = { open: true, scale: 1, tx: 0, ty: 0, dragging: false, sx: 0, sy: 0 };
  $('#lb-title').textContent = state.card.title;
  $('#lb-strip').innerHTML = (state.card.thumbs || state.card.images || []).map((src, k) =>
    `<img src="${src}" data-i="${k}" class="${k === i ? 'on' : ''}" alt="">`).join('');
  $('#lb-strip').querySelectorAll('img').forEach((el) =>
    el.addEventListener('click', () => lbSetIndex(+el.dataset.i)));
  lightbox.hidden = false;
  lbShow(i);
}

function lbShow(i) {
  const imgs = state.card?.images || [];
  state.index = (i + imgs.length) % (imgs.length || 1);
  const img = $('#lb-img');
  img.src = imgs[state.index] || '';
  img.onload = () => { fitImage(); applyTransform(); };
  $('#lb-counter').textContent = imgs.length ? `${state.index + 1} / ${imgs.length}` : '';
  $('#lb-strip').querySelectorAll('img').forEach((el) =>
    el.classList.toggle('on', +el.dataset.i === state.index));
  resetZoom();
}

/* ảnh vừa khung khi mở (contain), zoom nhân từ tỉ lệ đó */
function fitImage() {
  const img = $('#lb-img');
  const st = $('#lb-stage');
  if (!img.naturalWidth) return;
  const k = Math.min(st.clientWidth / img.naturalWidth, st.clientHeight / img.naturalHeight, 1) * 0.94;
  img.dataset.base = String(k);
  img.style.width = (img.naturalWidth * k) + 'px';
  img.style.height = (img.naturalHeight * k) + 'px';
}

function applyTransform() {
  const s = state.lb.scale;
  $('#lb-img').style.transform = `translate(${state.lb.tx}px, ${state.lb.ty}px) scale(${s})`;
}

function zoomBy(f) {
  state.lb.scale = Math.min(6, Math.max(1, state.lb.scale * f));
  if (state.lb.scale === 1) { state.lb.tx = 0; state.lb.ty = 0; }
  applyTransform();
}

function resetZoom() {
  state.lb.scale = 1; state.lb.tx = 0; state.lb.ty = 0;
  applyTransform();
}

function lbSetIndex(i) { lbShow(i); }

function closeLightbox() {
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  lightbox.hidden = true;
  state.lb.open = false;
}

$('#lb-close').addEventListener('click', closeLightbox);
$('#lb-prev').addEventListener('click', () => lbShow(state.index - 1));
$('#lb-next').addEventListener('click', () => lbShow(state.index + 1));
$('#lb-in').addEventListener('click', () => zoomBy(1.35));
$('#lb-out').addEventListener('click', () => zoomBy(1 / 1.35));
$('#lb-reset').addEventListener('click', resetZoom);
$('#lb-full').addEventListener('click', () => {
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  else lightbox.requestFullscreen().catch(() => {});
});

/* zoom bằng lăn chuột */
$('#lb-stage').addEventListener('wheel', (e) => {
  if (lightbox.hidden) return;
  e.preventDefault();
  zoomBy(e.deltaY < 0 ? 1.12 : 1 / 1.12);
}, { passive: false });

/* kéo ảnh khi đã zoom */
const stage = $('#lb-stage');
stage.addEventListener('mousedown', (e) => {
  if (state.lb.scale <= 1) return;
  state.lb.dragging = true; state.lb.sx = e.clientX; state.lb.sy = e.clientY;
  stage.classList.add('drag');
});
window.addEventListener('mousemove', (e) => {
  if (!state.lb.dragging) return;
  state.lb.tx += e.clientX - state.lb.sx;
  state.lb.ty += e.clientY - state.lb.sy;
  state.lb.sx = e.clientX; state.lb.sy = e.clientY;
  applyTransform();
});
window.addEventListener('mouseup', () => { state.lb.dragging = false; stage.classList.remove('drag'); });

stage.addEventListener('dblclick', () => { state.lb.scale > 1 ? resetZoom() : zoomBy(2); });

/* cảm ứng: vuốt để chuyển ảnh khi chưa zoom */
let touchX = null;
stage.addEventListener('touchstart', (e) => { touchX = e.touches[0].clientX; }, { passive: true });
stage.addEventListener('touchend', (e) => {
  if (touchX === null || state.lb.scale > 1) return;
  const dx = e.changedTouches[0].clientX - touchX;
  if (Math.abs(dx) > 40) lbShow(state.index + (dx < 0 ? 1 : -1));
  touchX = null;
}, { passive: true });

window.addEventListener('resize', () => { if (state.lb.open) { fitImage(); applyTransform(); } });

/* ---------------- bàn phím ---------------- */
document.addEventListener('keydown', (e) => {
  if (state.lb.open) {
    switch (e.key) {
      case 'Escape': closeLightbox(); break;
      case 'ArrowLeft': lbShow(state.index - 1); break;
      case 'ArrowRight': lbShow(state.index + 1); break;
      case '+': case '=': zoomBy(1.35); break;
      case '-': case '_': zoomBy(1 / 1.35); break;
      case '0': resetZoom(); break;
      case 'f': case 'F': $('#lb-full').click(); break;
      default: return;
    }
    e.preventDefault();
    return;
  }
  if (!modal.hidden) {
    if (e.key === 'Escape') closeModal();
    if (e.key === 'ArrowLeft') setIndex(state.index - 1);
    if (e.key === 'ArrowRight') setIndex(state.index + 1);
  }
});

/* ---------------- helpers ---------------- */
function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function escapeAttr(s) { return escapeHtml(s).replace(/"/g, '&quot;'); }

window.__gallery = { state, openModal, openLightbox };  // để test tự động
boot();
