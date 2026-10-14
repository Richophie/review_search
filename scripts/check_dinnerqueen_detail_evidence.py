#!/usr/bin/env python3
"""Source-backed regression checks against public Dinnerqueen detail examples."""
from collect import safe_fetch
from dinnerqueen_media import verified_dinnerqueen_media
cases={
    "1545823":None, # generic 'if posting on blog' language is insufficient
    "1545846":"블로그", # official mission explicitly requires blog title keywords
    "1597713":"인스타그램", # official campaign-specific reels banner
}
for cid,expected in cases.items():
    page=safe_fetch("https://dinnerqueen.net/taste/"+cid)
    if not page:
        raise AssertionError("Official detail unavailable: "+cid)
    media,evidence=verified_dinnerqueen_media(page)
    print("DETAIL_EXPLICIT_MEDIA",cid,"expected",expected,"actual",media,
          "evidence",evidence,flush=True)
    if media!=expected:
        raise AssertionError("Unexpected classification: "+cid)
print("Official campaign media examples all passed",flush=True)
