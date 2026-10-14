import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from parse_cherivu import parse_card
class CherivuTests(unittest.TestCase):
 def test_actual_public_recruiting_card(self):
  row=parse_card(dict(url="https://cherivu.co.kr/campaigns/1457",
     title="[스페셜캠페인] 신라호텔 1박 숙박권 무료 체험단 모집",
     benefit="신라호텔 1박 숙박권",status="D-7",
     image="https://d6ctpjljlg7e8.cloudfront.net/7351/blob",
     icons=["/images/main/popularity_campaign/blog.svg"]))
  self.assertEqual(row["id"],"cherivu:1457")
  self.assertEqual(row["channels"],["블로그"])
  self.assertTrue(row["image_url"].startswith("https://d6ctpjljlg7e8.cloudfront.net/"))
  self.assertIsNone(row["applicants"])
  self.assertIsNone(row["competition_ratio"])
 def test_unconfirmed_date_not_invented(self):
  row=parse_card(dict(url="https://cherivu.co.kr/campaigns/1458",
     title="[MOCO] 프리미엄 웰컴키트 D",status="마감임박",icons=[]))
  self.assertTrue(row["open_verified"])
  self.assertIsNone(row["apply_deadline"])
 def test_unknown_no_status_rejected(self):
  self.assertIsNone(parse_card(dict(url="https://cherivu.co.kr/campaigns/1457",
      title="공개 체험 공고",status="")))
 def test_closed_and_untrusted_url_rejected(self):
  self.assertIsNone(parse_card(dict(url="https://cherivu.co.kr/campaigns/1457",
      title="공개 체험 공고",status="신청 마감")))
  self.assertIsNone(parse_card(dict(url="https://fake.co.kr/campaigns/1457",
      title="공개 체험 공고",status="D-7")))
 def test_region_not_inferred_from_brand(self):
  row=parse_card(dict(url="https://cherivu.co.kr/campaigns/1595",
      title="[기자단] 참치락",status="D-7",icons=["/images/main/popularity_campaign/blog.svg"]))
  self.assertEqual(row["campaign_type"],"기자단")
  self.assertIsNone(row["region_sido"])
if __name__=="__main__":unittest.main()
