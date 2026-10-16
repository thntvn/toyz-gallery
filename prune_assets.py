#!/usr/bin/env python3
"""Dọn ảnh thừa cho MỌI dòng sản phẩm (thư mục con có data/products.json).

Xoá assets/<id>, thumbs/<id> không được data/products.json của dòng đó tham chiếu (giữ _test).
Dùng: python3 prune_assets.py [--dry-run] [--dir tam-quoc]
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def lines(only: str = "") -> list[Path]:
    out = []
    for d in sorted(ROOT.iterdir()):
        if d.is_dir() and (d / "data" / "products.json").exists() and (not only or d.name == only):
            out.append(d)
    return out


def prune(base: Path, dry: bool) -> tuple[int, float]:
    data = json.loads((base / "data" / "products.json").read_text(encoding="utf-8"))
    keep = set()
    for p in data:
        for rel in (p.get("images") or []) + (p.get("thumbs") or []):
            parts = Path(rel).parts
            if parts and parts[0] in ("assets", "thumbs") and len(parts) > 1:
                keep.add(parts[1])
    removed, freed = 0, 0.0
    for sub in ("assets", "thumbs"):
        d = base / sub
        if not d.is_dir():
            continue
        for child in sorted(d.iterdir()):
            if child.name == "_test" or child.name in keep or not child.is_dir():
                continue
            size = sum(f.stat().st_size for f in child.rglob("*") if f.is_file())
            if not dry:
                shutil.rmtree(child)
            removed += 1
            freed += size
    return removed, freed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--dir", default="", help="chỉ dọn 1 dòng (tên thư mục con)")
    a = ap.parse_args()
    for base in lines(a.dir):
        n, freed = prune(base, a.dry_run)
        print(f"{base.name}: {'sẽ xoá' if a.dry_run else 'đã xoá'} {n} thư mục · {freed/1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
