#!/usr/bin/env python3
"""Dọn ảnh thừa: xoá assets/thumbs không nằm trong data/products.json (giữ _test)."""
import json
import shutil
from pathlib import Path

root = Path(__file__).resolve().parent
data = json.loads((root / "data" / "products.json").read_text(encoding="utf-8"))
keep = set()
for p in data:
    for rel in (p.get("images") or []) + (p.get("thumbs") or []):
        keep.add(Path(rel).parts[1] if Path(rel).parts[0] in ("assets", "thumbs") else Path(rel).parts[0])

removed = []
for base in ("assets", "thumbs"):
    d = root / base
    if not d.is_dir():
        continue
    for sub in sorted(d.iterdir()):
        if sub.name == "_test" or sub.name in keep or not sub.is_dir():
            continue
        n = sum(1 for _ in sub.rglob("*") if _.is_file())
        size = sum(f.stat().st_size for f in sub.rglob("*") if f.is_file())
        shutil.rmtree(sub)
        removed.append((base, sub.name, n, size))
print(f"giữ {len(keep)} bộ ảnh · xoá {len(removed)} thư mục thừa")
total = 0
for base, name, n, size in removed:
    total += size
print(f"đã xoá {len(removed)} thư mục · thu hồi {total/1e6:.1f} MB")
