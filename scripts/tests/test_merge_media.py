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
    def test_future_deadline_only(self):
        t=NOW.isoformat()
        a=row("old",[],t)
        a["apply_deadline"]=(NOW-timedelta(days=1)).date().isoformat()
        self.assertEqual(combined([a],[],NOW),[])

if __name__=="__main__":
    unittest.main()
