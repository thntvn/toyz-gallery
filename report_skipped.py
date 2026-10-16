#!/usr/bin/env python3
"""Liệt kê post Tam Quốc CHƯA dựng được (thiếu ảnh tải về được)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib.util

spec = importlib.util.spec_from_file_location("b", str(Path(__file__).resolve().parent / "build.py"))
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

posts = json.loads((Path.home() / ".hermes" / "state" / "toyz_posts_cache.json").read_text(encoding="utf-8"))
sel = [p for p in posts if b.TAMQUOC.search(b.norm(p.get("message"))) and not b.NOT_TAMQUOC.search(b.norm(p.get("message"))[:600])]
sel.sort(key=lambda p: p.get("inserted_at") or "", reverse=True)
data = json.load(open(Path(__file__).resolve().parent / "data" / "products.json"))
built = {d["post_id"] for d in data}
print("post Tam Quốc:", len(sel), "· đã dựng:", len(built), "· bỏ:", len(sel) - len(built))
for p in sel:
    if p.get("id") in built:
        continue
    atts = ((p.get("attachments") or {}).get("data") or [])
    fna = sum(1 for a in atts if "fbcdn.net" in str(a.get("url") or ""))
    cdn = sum(1 for a in atts if "content.pancake.vn" in str(a.get("url") or ""))
    print(f"  BỎ {str(p.get('inserted_at'))[:10]} · đính kèm={len(atts)} (fbcdn {fna}, pancake {cdn}) · {b.norm(p.get('message')).splitlines()[0][:65]}")
