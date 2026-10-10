#!/usr/bin/env python3
"""Audit publicly permitted DinnerQueen pages beyond the current 48-page window."""
import re,sys,time
sys.path.insert(0,"scripts")
import collect
seen=set()
for page in (120,150,200,250,300,350,400,500):
  url="https://dinnerqueen.net/taste"+(f"?page={page}" if page!=1 else "")
  try:
    text=collect.safe_fetch(url)
    if not text:
      print("PAGE",page,"NO PUBLIC DATA",flush=True)
      continue
    cards=text.split('class="qz-dq-card campaign')[1:]
    ids=set(re.findall(r'href="/taste/(\d+)"',text))
    print("PAGE",page,"cards",len(cards),"uniqueIDs",len(ids),"overlapWithSample",len(ids&seen),"samples",list(sorted(ids))[:4],flush=True)
    seen.update(ids)
  except Exception as e:print("PAGE",page,"ERROR",repr(e)[:180],flush=True)
  time.sleep(1.5)

# Diagnostic only: no storage or production data updates.
