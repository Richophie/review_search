#!/usr/bin/env python3
"""Rate-limited verification of unlabelled Dinnerqueen media from public details."""
import json,math,os,re,time
from pathlib import Path
from collect import OUT,NOW,safe_fetch
from dinnerqueen_media import verified_dinnerqueen_media

rows=json.loads(OUT.read_text(encoding="utf-8"))
pool=[r for r in rows if r.get("source_id")=="dinnerqueen" and not r.get("channels")
      and re.fullmatch(r"https://dinnerqueen\.net/taste/\d+",r.get("original_url") or "")]
pool.sort(key=lambda r:(r.get("apply_deadline") or "",r.get("last_seen_at") or ""),reverse=True)
limit=max(5,min(110,int(os.getenv("DQ_DETAIL_MEDIA_LIMIT","75"))))
rot=max(1,math.ceil(len(pool)/limit))
idx=int(NOW.timestamp()//(12*3600))%rot
selected=list({r["id"]:r for r in (pool[:12]+pool[idx*limit:(idx+1)*limit])}.values())
print("Public Dinnerqueen missing-media candidates",len(pool),
      "checking",len(selected),"rotation",idx+1,"/",rot,flush=True)
matched={}
for n,row in enumerate(selected,1):
    try:
        doc=safe_fetch(row["original_url"])
        if not doc:
            continue
        channel,evidence=verified_dinnerqueen_media(doc)
        if channel and evidence:
            matched[row["id"]]=(channel,evidence)
    except Exception as exc:
        print("Detail unavailable",row["id"],type(exc).__name__,str(exc)[:90],flush=True)
    if n%20==0:
        print("Detail inspected",n,"source-evidenced",len(matched),flush=True)
    time.sleep(0.55)
for row in rows:
    if row["id"] not in matched or row.get("channels"):
        continue
    ch,ev=matched[row["id"]]
    row["channels"]=[ch]
    row["media_evidence"]=ev
    row["search_text"]=" ".join([row.get("search_text") or "",ch]).strip().lower()
if matched:
    OUT.write_text(json.dumps(rows,ensure_ascii=False,indent=0)+"\n",encoding="utf-8")
print("Dinnerqueen official detail media confirmed:",len(matched),
      "byEvidence:",{kind:sum(ev==kind for ch,ev in matched.values()) for kind in
                    sorted({ev for ch,ev in matched.values()})},flush=True)
