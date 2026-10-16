#!/usr/bin/env python3
"""Sinh trang chọn dòng sản phẩm ở gốc repo (/index.html) từ data của từng thư mục con."""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# thư mục con → (tên dòng, mô tả)
LINES = [
    ("tam-quoc", "Tam Quốc", "Quan Vũ · Lữ Bố · Triệu Vân · Trương Phi · Lưu Bị — 303Toys, JSToys, FZ Art, FYJ, Infinity…"),
    ("final-fantasy", "Final Fantasy", "Tifa · Cloud · Sephiroth · Zack · Red XIII — Square Enix, Play Arts, studio nội địa…"),
]

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
           "%3Crect width='64' height='64' rx='14' fill='%23ff6a2b'/%3E%3Ctext x='32' y='43' font-size='34' "
           "text-anchor='middle' font-family='Arial' font-weight='bold' fill='%230d0f14'%3ET%3C/text%3E%3C/svg%3E")


def card(slug: str, name: str, desc: str) -> str:
    data_file = ROOT / slug / "data" / "products.json"
    n, cover, newest = 0, "", ""
    if data_file.exists():
        items = json.loads(data_file.read_text(encoding="utf-8"))
        n = len(items)
        if items:
            cover = items[0].get("thumbs", [""])[0] or items[0].get("images", [""])[0]
            if cover:
                cover = f"{slug}/{cover}"      # đường dẫn trong products.json tính từ thư mục dòng
            newest = items[0].get("date", "")
    img = (f'<img src="{html.escape(cover)}" alt="" loading="lazy">' if cover
           else '<div class="lc-thumb"></div>')
    meta = f"{n} sản phẩm" + (f" · mới nhất {newest}" if newest else "")
    return f"""  <a class="line-card" href="{slug}/">
    <div class="lc-thumb">{img}</div>
    <div class="lc-body">
      <h3>{html.escape(name)}</h3>
      <p>{html.escape(desc)}</p>
      <div class="lc-meta">{html.escape(meta)} →</div>
    </div>
  </a>"""


def main() -> int:
    cards = "\n".join(card(*l) for l in LINES if (ROOT / l[0]).is_dir())
    out = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TOYz — Chọn dòng sản phẩm</title>
<link rel="icon" href="{FAVICON}">
<link rel="stylesheet" href="styles.css">
</head>
<body>
<header class="topbar">
  <div class="brand">
    <span class="logo">TOYz</span>
    <span class="tagline">Premium Collectibles — chọn dòng sản phẩm</span>
  </div>
</header>

<main>
  <div class="lines">
{cards}
  </div>
</main>

<footer class="footer">
  <span>Nguồn: bài đăng fanpage TOYz (Pancake Page API) — ảnh tải về máy, không hotlink.</span>
</footer>
</body>
</html>
"""
    (ROOT / "index.html").write_text(out, encoding="utf-8")
    print(f"# đã ghi {ROOT/'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
