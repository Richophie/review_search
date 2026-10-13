#!/usr/bin/env python3
"""Read-only explain public snapshot contraction between two known commits."""
import collections,json,subprocess
from datetime import datetime,timedelta,timezone
from pathlib import Path

KST=timezone(timedelta(hours=9))
now=datetime.now(KST)
old_sha="ab701c27ea00a519b5b13816eb6caac7e2ad5d99"
old=json.loads(subprocess.check_output(["git","show",old_sha+":public/data/campaigns.json"]))
current=json.loads(Path("public/data/campaigns.json").read_text(encoding="utf-8"))
by_old={r["id"]:r for r in old}
by_new={r["id"]:r for r in current}
removed=[r for k,r in by_old.items() if k not in by_new]
added=[r for k,r in by_new.items() if k not in by_old]
print("OLD",len(old),"NEW",len(current),"REMOVED",len(removed),"ADDED",len(added),flush=True)
def ts(value):
 try:return datetime.fromisoformat(value.replace("Z","+00:00")).astimezone(KST)
 except:return datetime.min.replace(tzinfo=KST)
def why(r):
 deadline=r.get("apply_deadline")
 seen=ts(r.get("last_seen_at") or "")
 if deadline is not None and deadline<now.date().isoformat():return "deadline expired"
 if deadline is None and seen<now-timedelta(hours=48):return "unknown deadline stale"
 if deadline is not None and seen<now-timedelta(days=21):return "21-day stale"
 return "STILL ACTIVE / suspicious disappearance"
for name,rows in [("removed",removed),("added",added)]:
 by_source=collections.defaultdict(list)
 for r in rows:by_source[r["source_id"]].append(r)
 for source,items in sorted(by_source.items(),key=lambda p:-len(p[1])):
  reasons=collections.Counter(why(x) for x in items)
  dls=collections.Counter((x.get("apply_deadline") or "-")[:7] for x in items)
  seen=collections.Counter(str(x.get("last_seen_at") or "")[:10] for x in items)
  print(name,source,len(items),"REASONS",dict(reasons),"DEADLINE_MONTHS",dls.most_common(5),"LAST_SEEN_DAYS",seen.most_common(5),flush=True)
for r in removed:
 if r["source_id"]=="dinnerqueen" and why(r)=="STILL ACTIVE / suspicious disappearance":
  print("EXAMPLE_SUSPICIOUS",r["id"],r.get("apply_deadline"),r.get("last_seen_at"),r["original_url"],flush=True)
  break
