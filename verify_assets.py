#!/usr/bin/env python3
"""Kiểm tra mọi ảnh mà data/products.json tham chiếu đều có trên đĩa — cho mọi dòng sản phẩm.

Dùng: python3 verify_assets.py [--dir tam-quoc]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="", help="chỉ kiểm 1 dòng (tên thư mục con)")
    a = ap.parse_args()
    bad = 0
    for d in sorted(ROOT.iterdir()):
        if not d.is_dir() or (a.dir and d.name != a.dir):
            continue
        f = d / "data" / "products.json"
        if not f.exists():
            continue
        items = json.loads(f.read_text(encoding="utf-8"))
        miss, n = [], 0
        for p in items:
            for rel in (p.get("images") or []) + (p.get("thumbs") or []):
                n += 1
                if not (d / rel).exists():
                    miss.append((p.get("post_id"), rel))
        print(f"{d.name}: {len(items)} sản phẩm · {n} ảnh tham chiếu · thiếu {len(miss)}")
        for pid, rel in miss[:10]:
            print("   THIẾU", pid, rel)
        bad += len(miss)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
