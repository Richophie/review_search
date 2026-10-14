#!/usr/bin/env python3
"""Apply active-campaign policy before all downstream full-snapshot validation."""
import json
from datetime import datetime,timezone,timedelta
from pathlib import Path
from merge_snapshot import combined
KST=timezone(timedelta(hours=9))
target=Path("public/data/campaigns.json")
items=json.loads(target.read_text(encoding="utf-8"))
if not isinstance(items,list) or not items:
    raise SystemExit("Refusing to prune an empty or malformed snapshot")
active=combined([],items,datetime.now(KST))
if not active:
    raise SystemExit("Refusing to publish an empty live campaign index")
if len(active)>len(items):
    raise SystemExit("Unexpected index expansion during expiry cleanup")
if len(active)!=len(items):
    target.write_text(json.dumps(active,ensure_ascii=False,indent=0)+"\n",encoding="utf-8")
print("Verified active retention:",len(items),"->",len(active),
      "expired removed",len(items)-len(active),flush=True)
