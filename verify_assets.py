#!/usr/bin/env python3
"""Kiểm tra mọi ảnh mà products.json tham chiếu đều tồn tại trên đĩa."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
d = json.loads((root / "data" / "products.json").read_text(encoding="utf-8"))
miss, n = [], 0
for p in d:
    for rel in (p.get("images") or []) + (p.get("thumbs") or []):
        n += 1
        if not (root / rel).exists():
            miss.append((p["post_id"], rel))
print(f"sản phẩm: {len(d)} · ảnh tham chiếu: {n} · thiếu: {len(miss)}")
for pid, rel in miss[:10]:
    print("  THIẾU", pid, rel)
