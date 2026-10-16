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

FF = re.compile(r"final fantasy|\bffvii\b|\bff7\b|\bff7r\b|\bff8\b|\bffviii\b|\bffix\b|\bffx\b|\bffxv\b|"
                r"\bffxvi\b|cloud strife|sephiroth|tifa|aerith|aeris|zack fair|squall|rinoa|noctis|"
                r"tidus|\byuna\b|\bvivi\b|chocobo|moogle|cactuar|tonberry|barret|vincent valentine|"
                r"red xiii|kefka|advent children|crisis core|dissidia|play arts|bring arts|static arts|"
                r"square enix", re.I)
# dòng Square Enix KHÁC (Kingdom Hearts/Nier/Marvel…) — không tính là Final Fantasy
NOT_FF = re.compile(r"kingdom hearts|nier|automata|marvel|batman|bat man|dragon quest|star wars|halo|doom|"
                    r"god of war|horizon|tomb raider|black widow|iron man|spider|variants? play arts|thanos", re.I)

# Mỗi dòng sản phẩm = 1 trang riêng: (regex nhận, regex loại)
LINES: dict[str, tuple[re.Pattern, re.Pattern]] = {
    "tamquoc": (TAMQUOC, NOT_TAMQUOC),
    "finalfantasy": (FF, NOT_FF),
}
# tiêu đề bài đăng kiểu "thông báo" không phải tên sản phẩm → phải tìm dòng khác làm tiêu đề
BAD_TITLE = re.compile(r"^\W*(giới hạn|giá ưu đãi|sợ gì|hàng về|hàng có sẵn|hàng hiếm|new arrival|new\b|sale|"
                       r"ưu đãi|khuyến mãi|hot|tin vui|nhận order|order now|lại có duyên|một trong số|"
                       r"đã rất lâu|deal\b|cực (?:hot|phẩm)|số lượng 1)", re.I)
NAME_HINT = re.compile(r"studio|\b1[:/]\d\b|action figure|statue|tượng|scale|fz\d|tifa|sephiroth|cloud|zack|"
                       r"aerith|red xiii|chocobo", re.I)
# dòng thông số, không phải tên sản phẩm
LABEL_LINE = re.compile(r"^\W*(hãng s[xy]|nhà sản xuất|thương hiệu|chất liệu|kích thước|tỉ lệ|giá|mã sản phẩm|"
                        r"code|size|material|po close|hạn chốt|deposit|cọc)", re.I)


def clean_title(t: str) -> str:
    """Bỏ ký tự trang trí/gạch ở hai đầu dòng tiêu đề."""
    t = re.sub(r"^[\s\-–—•*|_🌟🔥〰️❗️!✅]+", "", str(t or ""))
    t = re.sub(r"[\s\-–—•*|_]+$", "", t)
    return re.sub(r"\s{2,}", " ", t).strip()

def norm(text: str) -> str:
    """Chuẩn hoá chữ 'fancy' (𝗣𝗥𝗘-𝗢𝗥𝗗𝗘𝗥) về chữ thường đọc được, giữ dấu tiếng Việt."""
    return unicodedata.normalize("NFKC", str(text or "")).replace("\u00a0", " ")



VER_RE = re.compile(r"standard|deluxe|combo|bản thường|bản đặc biệt|\bver\b|version|full ?set|premium|ultimate|exclusive", re.I)
PRICE_LINE = re.compile(r"gi[aá]\s*(?:\(price\))?\s*[:：]\s*([^\n]+)", re.I)


def to_vnd(raw: str) -> tuple[str, int]:
    """'6.100k' -> ('6.100.000đ', 6100000); '615(ck)/nvat' -> ('615.000đ', 615000);
    '40 tr' -> ('40.000.000đ', 40000000); giá mơ hồ kiểu '6X tr' -> giữ nguyên chữ, value 0 (không đoán)."""
    s = str(raw or "").replace("\u00a0", " ")
    m = re.search(r"(\d[\d.,]*)\s*(k|tr|triệu|m)?", s, re.I)
    if not m:
        return "", 0
    digits = re.sub(r"\D", "", m.group(1))
    if not digits:
        return "", 0
    unit = (m.group(2) or "").lower()
    val = int(digits)
    if unit == "k":
        val *= 1_000
    elif unit in ("tr", "triệu", "m"):
        val *= 1_000_000
    elif val < 100_000:               # shop ghi theo đơn vị 'k'
        val *= 1_000
    if re.search(r"\d\s*[xX]\b", s) or val < 10_000:   # '6X tr', 'giá liên hệ' → không đoán số
        return s.strip()[:40], 0
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
            price_part, _, dep_part = raw.partition(" - ")
            price_txt, price_val = to_vnd(price_part)
            dep = ""
            dm = (re.search(r"c[oọ]c\s*(?:\s*\(deposit\))?\s*[:：]?\s*(.*)", dep_part, re.I)
                  or re.search(r"c[oọ]c\s*(?:\s*\(deposit\))?\s*[:：]\s*(.*)", raw, re.I))
            if dm:
                dtxt = dm.group(1).strip(" .-")
                if "%" in dtxt:                      # cọc theo % → giữ nguyên chữ, không đoán số
                    dep = dtxt[:20]
                else:
                    t, _ = to_vnd(dtxt)
                    dep = t or dtxt[:20]
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
    """'Giá (Price): 3.580' -> ('3.580.000đ', 3580000). Đơn vị shop ghi là 'k' (hoặc 'tr' = triệu)."""
    raw = pick(r"gi[aá]", text)
    if not raw:
        return "", 0
    t, v = to_vnd(raw)
    return (t or raw.strip()[:40], v)


def parse_post(p: dict) -> dict | None:
    raw = str(p.get("message") or "").strip()
    if not raw:
        return None
    text = norm(raw)
    atts = ((p.get("attachments") or {}).get("data") or [])
    images = [a.get("url") for a in atts if a.get("type") == "photo" and a.get("url")]
    if not images:
        return None

    # tiêu đề = dòng đầu, bỏ nhãn [PRE-ORDER]; bài kiểu thông báo thì lấy dòng có tên sản phẩm
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    first = lines[0] if lines else ""
    if BAD_TITLE.search(first):
        cand = next((ln for ln in lines[1:12]
                     if NAME_HINT.search(ln) and not LABEL_LINE.search(ln) and len(ln) <= 110), "")
        if cand:
            first = cand
    title = re.sub(r"^\[\s*(PRE-?ORDER|ĐẶT TRƯỚC)\s*\]\s*", "", first, flags=re.I).strip()
    title = clean_title(re.sub(r"\s{2,}", " ", title))[:120]
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
    ap.add_argument("--filter", default="tamquoc", choices=sorted(LINES) + ["all"],
                    help="dòng sản phẩm (mỗi dòng = 1 trang riêng)")
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--max-img", type=int, default=0, help="giới hạn số ảnh mỗi sản phẩm (0 = không giới hạn)")
    ap.add_argument("--skip", default="", help="danh sách post_id bỏ qua, cách nhau dấu phẩy")
    ap.add_argument("--out", default=str(Path.home() / "toyz-gallery"))
    a = ap.parse_args()
    out = Path(a.out)
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(parents=True, exist_ok=True)
    (out / "thumbs").mkdir(parents=True, exist_ok=True)

    posts = json.loads(CACHE.read_text(encoding="utf-8"))
    posts.sort(key=lambda p: p.get("inserted_at") or "", reverse=True)
    if a.filter != "all":
        inc, exc = LINES[a.filter]
        posts = [p for p in posts if inc.search(norm(p.get("message")))
                 and not exc.search(norm(p.get("message"))[:600])]
    skip = {s.strip() for s in a.skip.split(",") if s.strip()}
    if skip:
        posts = [p for p in posts if str(p.get("id")) not in skip]
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
        imgs = item["images"][:a.max_img] if a.max_img else item["images"]
        local, local_t = [], []
        for i, url in enumerate(imgs):
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
