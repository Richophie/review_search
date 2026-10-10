#!/usr/bin/env python3
"""Short read-only verification of newly integrated source adapters."""
import sys
sys.path.insert(0,"scripts")
import collect
for name, fn in (
    ("assaview",collect.assaview),
    ("ringble",collect.ringble),
    ("cometoplay",collect.cometoplay),
    ("cherrycook",collect.cherrycook),
    ("gaboja",collect.gaboja),
    ("bqueens",collect.bqueens),
    ("huki",collect.huki),
    ("openreview",collect.openreview),
    ("pavlovu",collect.pavlovu)
):
 try:
  records=fn()
  unique=len(set(r["original_url"] for r in records))
  accurate=sum(r["deadline_precision"]=="exact" for r in records)
  ratios=sum(r["competition_ratio"] is not None for r in records)
  print("CHECK",name,"total",len(records),"unique",unique,"exact_dates",accurate,"known_ratios",ratios,flush=True)
  for c in records[:2]:
   print("SAMPLE",c["title"][:85],c["apply_deadline"],c["original_url"],flush=True)
  if name == "bqueens": assert len(records) >= 90, (name,"pagination not covered")
  if name == "cherrycook": assert len(records) >= 18, (name,"mission-list parsing incomplete")
  if name == "pavlovu": assert len(records) > 0, "Pavlovu public listings missing"
  assert unique==len(records),(name,"duplicates")
  assert all(r["title"] and r["original_url"] and r["apply_deadline"] for r in records),name
 except Exception as ex:
  print("SOURCE ERROR",name,type(ex).__name__,str(ex),flush=True)

# No writes: checks public source lists and normalized fields only.
