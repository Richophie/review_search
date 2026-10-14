import unittest
from campaign_lifecycle import reconcile

T="2026-10-14T14:00:00+09:00"
R={"source_id":"example","id":"example:1","original_url":"https://example.org/1"}

class CampaignLifecycleTests(unittest.TestCase):
    def test_started_and_updated(self):
        rows, events = reconcile([], [R], source_id="example", complete=True, observed_at=T)
        self.assertEqual(events[0]["event"], "started")
        _, events = reconcile(rows, [{**R, "slots":4}], source_id="example", complete=True, observed_at=T)
        self.assertEqual(events[0]["event"], "updated")

    def test_partial_scan_keeps_open(self):
        rows, _ = reconcile([], [R], source_id="example", complete=True, observed_at=T)
        rows, events = reconcile(rows, [], source_id="example", complete=False, observed_at=T)
        self.assertEqual(rows[0]["lifecycle_state"], "open")
        self.assertEqual(events, [])

    def test_two_complete_misses_are_uncertain(self):
        rows, _ = reconcile([], [R], source_id="example", complete=True, observed_at=T)
        rows, _ = reconcile(rows, [], source_id="example", complete=True, observed_at=T)
        self.assertEqual(rows[0]["lifecycle_state"], "open")
        rows, events = reconcile(rows, [], source_id="example", complete=True, observed_at=T)
        self.assertEqual(rows[0]["lifecycle_state"], "uncertain")
        self.assertEqual(events[0]["event"], "missing_from_complete_scan")

    def test_reappearance(self):
        rows, _ = reconcile([{**R,"lifecycle_state":"uncertain","missing_complete_scans":2}], [R],
                            source_id="example", complete=True, observed_at=T)
        self.assertEqual(rows[0]["lifecycle_state"], "open")

    def test_invalid_source(self):
        with self.assertRaises(ValueError):
            reconcile([], [{**R,"source_id":"other"}],source_id="example",complete=True,observed_at=T)

if __name__=="__main__": unittest.main()
