#!/usr/bin/env python3
"""Soi nhanh 1 sản phẩm trong data/products.json theo từ khoá tiêu đề."""
import json
import sys
from pathlib import Path

kw = sys.argv[1] if len(sys.argv) > 1 else ""
line = sys.argv[2] if len(sys.argv) > 2 else "final-fantasy"
items = json.loads((Path(__file__).resolve().parent / line / "data" / "products.json").read_text(encoding="utf-8"))
for p in items:
    if kw.lower() in p["title"].lower():
        print("TITLE:", p["title"], "| price:", p["price"], "| date:", p["date"], "| link:", p["link"])
        for f in p["facts"]:
            print("    -", f["k"], "=", f["v"][:110])
        print("    DESC:", p["desc"][:400].replace("\n", " ⏎ "))
        print("---")
