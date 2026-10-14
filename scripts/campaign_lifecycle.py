"""Conservative per-source campaign lifecycle. No network calls."""
from datetime import datetime

def reconcile(previous, observed, *, source_id, complete, observed_at, missing_threshold=2):
    """Return new source ledger and events. Missing records never mean closed."""
    if missing_threshold < 2 or not source_id:
        raise ValueError("Source and threshold >=2 required")
    dt = datetime.fromisoformat(observed_at.replace("Z","+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Timezone required")
    before = {}
    for row in previous:
        if row.get("source_id") != source_id or not row.get("id") or row["id"] in before:
            raise ValueError("Invalid or duplicate previous row")
        before[row["id"]] = dict(row)
    seen = {}
    for row in observed:
        if row.get("source_id") != source_id or not row.get("id") or not row.get("original_url") or row["id"] in seen:
            raise ValueError("Invalid or duplicate observation")
        seen[row["id"]] = dict(row)
    updated, events = {}, []
    for cid, row in seen.items():
        old = before.get(cid)
        item = {**(old or {}), **row}
        item.update(lifecycle_state="open", missing_complete_scans=0, last_seen_at=observed_at)
        item["first_seen_at"] = (old or {}).get("first_seen_at") or observed_at
        updated[cid] = item
        if old is None:
            events.append({"id":cid,"event":"started"})
        elif old.get("lifecycle_state") in ("closed","uncertain"):
            events.append({"id":cid,"event":"reappeared"})
        elif any(old.get(k)!=item.get(k) for k in ("apply_deadline","slots","applicants")):
            events.append({"id":cid,"event":"updated"})
    for cid, old in before.items():
        if cid in seen:
            continue
        old = dict(old)
        if complete and old.get("lifecycle_state") != "closed":
            count = int(old.get("missing_complete_scans") or 0) + 1
            old["missing_complete_scans"] = count
            if count >= missing_threshold:
                old["lifecycle_state"] = "uncertain"
                if count == missing_threshold:
                    events.append({"id":cid,"event":"missing_from_complete_scan"})
        updated[cid] = old
    return sorted(updated.values(), key=lambda r:r["id"]), events
