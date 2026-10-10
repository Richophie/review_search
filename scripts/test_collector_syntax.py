#!/usr/bin/env python3
"""Fast offline syntax check before publishing a refreshed data snapshot."""
import ast
from pathlib import Path
p=Path("scripts/collect.py")
ast.parse(p.read_text(encoding="utf-8"),filename=str(p))
print("Collector syntax valid",flush=True)

# Offline only; does not contact platforms.
