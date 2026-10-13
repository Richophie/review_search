import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from merge_snapshot import combined

NOW=datetime.now(timezone(timedelta(hours=9)))
def row(tag, channels, timestamp):
    return {
        "id":"bqueens:1",
        "source_id":"bqueens",
        "original_url":"https://bqueens.net/taste/1",
        "title":"[릴스][스마트에버] 터치톡 뷰티디바이스 SET",
        "channels":channels,
        "last_seen_at":timestamp,
        "first_seen_at":timestamp,
        "apply_deadline":(NOW+timedelta(days=3)).date().isoformat(),
        "search_text":"스마트에버 터치톡",
    }

class MergeMediaEvidenceTest(unittest.TestCase):
    def test_older_collector_can_not_erase_explicit_media(self):
        recent=NOW.isoformat()
        a=row("old", ["인스타그램"],recent)
        b=row("stale",[],recent)
        merged=combined([a],[b],NOW)
        self.assertEqual(merged[0]["channels"],["인스타그램"])
        self.assertIn("인스타그램",merged[0]["search_text"])
    def test_non_media_brand_name_is_not_assumed(self):
        t=NOW.isoformat()
        a=row("old",[],t)
        a["title"]="[뷰티] 클립 모양의 헤어핀"
        self.assertEqual(combined([a],[],NOW)[0]["channels"],[])
    def test_assaview_icon_evidence_survives_equal_timestamp_merge(self):
        stamp=NOW.isoformat()
        previous=row("source",["블로그"],stamp)
        previous.update({
            "id":"assaview:1","source_id":"assaview",
            "original_url":"https://www.assaview.co.kr/campaign.php?cp_id=1",
            "title":"[서울 관악구] 공식 체험단",
            "media_evidence":"assaview_review_type_icon:blog_icon.png",
        })
        stale=dict(previous)
        stale["channels"]=[]
        stale.pop("media_evidence")
        restored=combined([previous],[stale],NOW)[0]
        self.assertEqual(restored["channels"],["블로그"])
        self.assertEqual(restored["media_evidence"],previous["media_evidence"])

    def test_genuinely_newer_iconless_card_can_update_state(self):
        stamp=NOW.isoformat()
        previous=row("source",["블로그"],stamp)
        previous.update({
            "id":"assaview:1","source_id":"assaview",
            "original_url":"https://www.assaview.co.kr/campaign.php?cp_id=1",
            "title":"[서울 관악구] 공식 체험단",
            "media_evidence":"assaview_review_type_icon:blog_icon.png",
        })
        newer=dict(previous)
        newer["channels"]=[]
        newer.pop("media_evidence")
        newer["last_seen_at"]=(NOW+timedelta(seconds=30)).isoformat()
        merged=combined([previous],[newer],NOW)[0]
        self.assertEqual(merged["channels"],[])

    def test_future_deadline_only(self):
        t=NOW.isoformat()
        a=row("old",[],t)
        a["apply_deadline"]=(NOW-timedelta(days=1)).date().isoformat()
        self.assertEqual(combined([a],[],NOW),[])

if __name__=="__main__":
    unittest.main()
