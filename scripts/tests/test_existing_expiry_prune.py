#!/usr/bin/env python3
"""Check that a stale unrelated campaign cannot prevent publishing valid data."""
import json, tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from merge_snapshot import combined

now=datetime.now(timezone(timedelta(hours=9)))
path=Path("public/data/campaigns.json")
rows=json.loads(path.read_text(encoding="utf-8"))
before=len(rows)
after=combined([],rows,now)
print("CURRENT",before,"ACTIVE_AFTER_PRUNE",len(after),"REMOVED",before-len(after),flush=True)
assert after, "Prune must not yield zero campaigns"
assert all((r.get("apply_deadline") is not None or
       now-datetime.fromisoformat(r["last_seen_at"])<=timedelta(hours=48)) for r in after)
assert len(after)<=before
print("STALENESS_PRUNE_TEST_OK",flush=True)
