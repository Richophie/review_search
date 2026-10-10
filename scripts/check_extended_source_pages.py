#!/usr/bin/env python3
"""Confirm source-only extraction on public, permitted pages."""
import ast
from pathlib import Path
ast.parse(Path("scripts/collect.py").read_text(encoding="utf-8"))
import sys
sys.path.insert(0,"scripts")
import collect
for key,fn,minimum in [
    ("cherrycook",collect.cherrycook,35),
    ("pavlovu",collect.pavlovu,15),
]:
    rows=fn()
    links=[row["original_url"] for row in rows]
    assert len(rows)>=minimum, (key,"undercollected",len(rows))
    assert len(links)==len(set(links)), (key,"duplicates")
    assert all(row["apply_deadline"] or row.get("open_verified") for row in rows)
    print("PASSED",key,len(rows),"verified open campaigns",flush=True)

# Does not write campaign data or bypass access controls.
