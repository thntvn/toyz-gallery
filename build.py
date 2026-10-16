#!/usr/bin/env python3
"""Dựng data/products.json + tải ảnh cho trang gallery TOYz từ cache post fanpage.

Dùng: python3 build.py [--filter tamquoc|all] [--limit 60] [--out ~/toyz-gallery]
Ảnh tải về assets/<post_id>/<n>.jpg và được tham chiếu bằng đường dẫn tương đối (không hotlink).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".hermes" / "scripts"))
CACHE = Path.home() / ".hermes" / "state" / "toyz_posts_cache.json"

TAMQUOC = re.compile(
    r"tam quốc|tam quoc|three kingdoms|jstoys|jst toys|ngũ hổ tướng|lữ bố|lubu|quan vũ|quan vu|guan yu|"
    r"triệu vân|zhao yun|triệu tử long|trương phi|lưu bị|tào tháo|gia cát lượng|khổng minh|điêu thuyền|"
    r"đát kỷ|đổng trác|mã siêu|hoàng trung|quan công|tam anh chiến|fusion fantasy|inflames|"
    r"fyj studio|hoàng trung|motor nuclear|qx00[3-7]|lub(?:u|o)", re.I)
# loại các bài KHÔNG phải Tam Quốc dù có tên hãng chung
NOT_TAMQUOC = re.compile(r"tần thủy hoàng|thần tài|god of wealth|hua rong|xiao li guang|bao công|"
                         r"triển chiêu|công tôn sách|đại kiều|tiểu kiều|hwit|phoeleo|spetsnaz|"
                         r"hongkong police|u\.?s army|lynx|dead oder", re.I)

def norm(text: str) -> str:
    """Chuẩn hoá chữ 'fancy' (𝗣𝗥𝗘-𝗢𝗥𝗗𝗘𝗥) về chữ thường đọc được, giữ dấu tiếng Việt."""
    return unicodedata.normalize("NFKC", str(text or "")).replace("\u00a0", " ")



VER_RE = re.compile(r"standard|deluxe|combo|bản thường|bản đặc biệt|\bver\b|version|full ?set|premium|ultimate|exclusive", re.I)
PRICE_LINE = re.compile(r"gi[aá]\s*(?:\(price\))?\s*[:：]\s*([^\n]+)", re.I)


def to_vnd(raw: str) -> tuple[str, int]:
    """'6.100k' -> ('6.100.000đ', 6100000); '615(ck)/nvat' -> ('615.000đ', 615000)."""
    m = re.search(r"([\d][\d.,]*)", raw or "")
    if not m:
        return "", 0
    digits = re.sub(r"\D", "", m.group(1))
    if not digits:
        return "", 0
    val = int(digits)
    if val < 100_000:                 # shop ghi theo đơn vị 'k'
        val *= 1000
    return f"{val:,}đ".replace(",", "."), val


def parse_versions(text: str) -> list[dict]:
    """Tách từng phiên bản (Standard/Deluxe/Combo…) cùng giá + cọc, theo đúng thứ tự bài đăng."""
    out, label = [], ""
    for ln in text.splitlines():
        line = ln.strip()
        if not line:
            continue
        if PRICE_LINE.search(line):
            raw = PRICE_LINE.search(line).group(1)
            price_txt, price_val = to_vnd(raw)
            dep = ""
            dm = re.search(r"c[oọ]c\s*(?:\(deposit\))?\s*[:：]\s*([^\-\n]*)", line, re.I)
            if dm:
                d_txt, _ = to_vnd(dm.group(1))
                dep = d_txt or dm.group(1).strip()
            out.append({"label": label, "price": price_txt, "price_value": price_val, "deposit": dep})
            continue
        if ":" not in line and len(line) < 70 and VER_RE.search(line):
            label = re.sub(r"^[^\wÀ-ỹ]+", "", line)[:40].strip()
            label = re.sub(r"^Standard Ver$", "Standard Ver", label)
    return out


def pick(label_regex: str, text: str) -> str:
    # Nhóm (?:...) để phép OR không phá cấu trúc nhãn → dấu ':' → giá trị (bug từng làm mất SKU/chất liệu)
    m = re.search(rf"(?:{label_regex})[^\n:：]{{0,22}}[:：]\s*(.+)", text, re.I)
    return ((m.group(1) or "").strip(" -•\t") if m else "")


def parse_price(text: str) -> tuple[str, int]:
    """'Giá (Price): 3.580' -> ('3.580.000đ', 3580000). Đơn vị shop ghi là 'k'."""
    raw = pick(r"gi[aá]", text)
    if not raw:
        return "", 0
    m = re.search(r"([\d][\d.,]*)", raw)
    if not m:
        return raw[:40], 0
    digits = re.sub(r"\D", "", m.group(1))
    if not digits:
        return raw[:40], 0
    val = int(digits)
    if val < 100_000:
        val *= 1000
    return f"{val:,}đ".replace(",", "."), val


def parse_post(p: dict) -> dict | None:
    raw = str(p.get("message") or "").strip()
    if not raw:
        return None
    text = norm(raw)
    atts = ((p.get("attachments") or {}).get("data") or [])
    images = [a.get("url") for a in atts if a.get("type") == "photo" and a.get("url")]
    if not images:
        return None

    # tiêu đề = dòng đầu, bỏ nhãn [PRE-ORDER]
    first = ""
    for line in text.splitlines():
        line = line.strip()
        if line:
            first = line
            break
    title = re.sub(r"^\[\s*(PRE-?ORDER|ĐẶT TRƯỚC)\s*\]\s*", "", first, flags=re.I).strip()
    title = re.sub(r"\s{2,}", " ", title)[:120]
    subtitle = " · ".join(x for x in (pick(r"mã sản phẩm", text) or pick(r"sku", text),) if x)

    versions = parse_versions(text)
    if not versions:
        pt, pv = parse_price(text)
        if pt:
            versions = [{"label": "", "price": pt, "price_value": pv, "deposit": ""}]
    price_txt = ""
    if versions:
        vals = [v["price_value"] for v in versions if v["price_value"]]
        if vals:
            lo, hi = min(vals), max(vals)
            f = f"từ {lo:,}đ" if lo != hi else f"{lo:,}đ"
            price_txt = f.replace(",", ".")

    facts = []
    for v in versions[:4]:
        if v["price"]:
            k = v["label"] or "Giá"
            val = v["price"] + (f" · cọc {v['deposit']}" if v["deposit"] else "")
            facts.append({"k": k[:38], "v": val[:120]})
    for label, key in (("SKU", r"mã sản phẩm|sku"), ("Chất liệu", r"chất liệu|material"),
                       ("Kích thước", r"kích thước|size"), ("Tỉ lệ", r"tỉ lệ|tỷ lệ|scale"),
                       ("Hàng về", r"dự kiến hàng về|eta|thời gian phát hành|release"),
                       ("Chốt đơn", r"hạn chốt đơn|po close"),
                       ("Giới hạn", r"giới hạn|limit")):
        v = pick(label if False else key, text)
        if v:
            facts.append({"k": label, "v": v[:160]})

    badge = "PRE-ORDER" if re.search(r"pre-?order|đặt trước", text[:400], re.I) else "CÒN HÀNG"
    pid = str(p.get("id") or "")
    permalink = p.get("link") or ("https://www.facebook.com/" + pid.split("_")[-1] if "_" in pid else "")
    dt = str(p.get("inserted_at") or "")
    try:
        date_vn = datetime.fromisoformat(dt).strftime("%d/%m/%Y")
    except Exception:
        date_vn = dt[:10]
    desc = text.strip()
    if len(desc) > 2200:
        desc = desc[:2200] + " …"
    return {"post_id": pid, "title": title, "subtitle": subtitle, "price": price_txt,
            "price_value": min([v["price_value"] for v in versions if v["price_value"]] or [0]),
            "versions": versions[:4], "sku": pick(r"mã sản phẩm|sku", text),
            "badge": badge, "desc": desc, "facts": facts, "images": images,
            "link": permalink, "date": date_vn, "inserted_at": dt}


def download(url: str, dest: Path, max_w: int = 1400, quality: int = 85) -> bool:
    """Tải ảnh; nếu có PIL thì thu nhỏ về max_w để repo nhẹ (ảnh gốc 720–1200px)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (toyz-gallery build)"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        if not data:
            return False
        dest.write_bytes(data)
        try:
            from PIL import Image
            im = Image.open(dest)
            im = im.convert("RGB")
            if im.width > max_w:
                im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
            im.save(dest, "JPEG", quality=quality, optimize=True)
        except Exception:
            pass
        return dest.stat().st_size > 0
    except Exception as e:
        print(f"      ⚠️ lỗi tải {url[:70]}: {type(e).__name__}: {e}")
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--filter", default="tamquoc", choices=["tamquoc", "all"])
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--out", default=str(Path.home() / "toyz-gallery"))
    a = ap.parse_args()
    out = Path(a.out)
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(parents=True, exist_ok=True)
    (out / "thumbs").mkdir(parents=True, exist_ok=True)

    posts = json.loads(CACHE.read_text(encoding="utf-8"))
    posts.sort(key=lambda p: p.get("inserted_at") or "", reverse=True)
    if a.filter == "tamquoc":
        posts = [p for p in posts if TAMQUOC.search(norm(p.get("message")))
                 and not NOT_TAMQUOC.search(norm(p.get("message"))[:600])]
    print(f"# {len(posts)} post sau lọc ({a.filter})")

    products, seen_titles = [], set()
    for p in posts:
        item = parse_post(p)
        if not item:
            continue
        key = re.sub(r"\W+", "", norm(item["title"]).lower())[:40]
        if key in seen_titles:          # bài đăng trùng nội dung -> giữ bản mới nhất
            continue
        seen_titles.add(key)
        folder = out / "assets" / re.sub(r"\W+", "_", item["post_id"])
        tfolder = out / "thumbs" / re.sub(r"\W+", "_", item["post_id"])
        folder.mkdir(parents=True, exist_ok=True)
        tfolder.mkdir(parents=True, exist_ok=True)
        local, local_t = [], []
        for i, url in enumerate(item["images"]):
            dest = folder / f"{i:02d}.jpg"
            tdest = tfolder / f"{i:02d}.jpg"
            if not dest.exists():
                if not download(url, dest):
                    continue
            if not tdest.exists():
                download(url, tdest, max_w=520, quality=76)
            local.append(f"assets/{folder.name}/{dest.name}")
            local_t.append(f"thumbs/{tfolder.name}/{tdest.name}" if tdest.exists() else f"assets/{folder.name}/{dest.name}")
        if not local:
            continue
        item["images"] = local
        item["thumbs"] = local_t
        products.append(item)
        print(f"  ✔ {item['date']} · {len(local)} ảnh · {item['title'][:70]}")
        if len(products) >= a.limit:
            break

    (out / "data" / "products.json").write_text(json.dumps(products, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n# {len(products)} sản phẩm → {out/'data'/'products.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
