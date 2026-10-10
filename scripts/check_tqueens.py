#!/usr/bin/env python3
"""Read-only verification of public Parcel Queen campaign list extraction."""
import sys
sys.path.insert(0,"scripts")
import collect
items=collect.tqueens()
ids={x["id"] for x in items}
urls={x["original_url"] for x in items}
assert len(items)>=20, "Unexpectedly few Parcel Queen public listings"
assert len(ids)==len(items)==len(urls), "Duplicate Parcel Queen listings"
for item in items:
    assert item["title"] and item["apply_deadline"] and item["original_url"].startswith("https://tqueens.net/taste/")
    assert item["competition_ratio"] is None, "Unpublished competition ratio must not be fabricated"
print(f"Verified {len(items)} distinct Parcel Queen public campaign listings",flush=True)

# Only publicly permitted source pages.
