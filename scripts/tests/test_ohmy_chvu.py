import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from parse_ohmy_chvu import parse_card,safe_image
class TestPublicCards(unittest.TestCase):
 def test_ohmy_card(self):
  r=parse_card(dict(url="https://www.ohmyblog.co.kr/productDetail.apsl?app_seq=437733",
    title="오디데이(5D-DAY) 이벤트 랜덤선정",benefit="프리미엄 과일선물세트 7종",
    status="21일 남음",slots="1명 모집",type="제품체험",
    media=["INSTAGRAM_REELS","NAVER_BLOG_POST"],image="/UPLOAD/CAMPAIGNS/item.png"),"ohmyblog")
  self.assertEqual(r["id"],"ohmyblog:437733")
  self.assertIn("프리미엄 과일선물세트",r["title"])
  self.assertEqual(r["channels"],["인스타그램","블로그"])
  self.assertIsNone(r["competition_ratio"])
  self.assertEqual(r["campaign_type"],"배송형")
 def test_chvu_card(self):
  r=parse_card(dict(url="https://chvu.co.kr/campaign/200224",
    title="[경기/가평]비원식당[6차]",benefit="닭다리탕 or 통삼겹",status="D - 5",
    count="신청 0/5",type="Blog 방문형",media=["Blog"],
    image="https://api.media.smiledragon.co.kr/media/download/abc"),"chvu")
  self.assertEqual(r["id"],"chvu:200224")
  self.assertEqual(r["region_sido"],"경기")
  self.assertEqual(r["competition_ratio"],0)
  self.assertEqual(r["channels"],["블로그"])
 def test_chvu_today(self):
  r=parse_card(dict(url="https://chvu.co.kr/campaign/199818",title="[경북/경주] 제이블링",
    status="D - day",count="신청 0/2",media=["Blog"]),"chvu")
  self.assertEqual(r["apply_deadline"][:10],r["last_seen_at"][:10])
 def test_no_inferred_applicants(self):
  r=parse_card(dict(url="https://www.ohmyblog.co.kr/productDetail.apsl?app_seq=123456",
    title="[서울] 새 체험단",status="오늘 마감",slots="5명 모집",media=[]),"ohmyblog")
  self.assertIsNone(r["applicants"])
  self.assertIsNone(r["competition_ratio"])
 def test_reject_unverified(self):
  self.assertIsNone(parse_card(dict(url="https://chvu.co.kr/campaign/1",title="[서울] 맛집",
    status="D - -1",count="신청 1/3"),"chvu"))
 def test_no_untrusted_images(self):
  self.assertIsNone(safe_image("https://other.example/image.png","chvu"))
  self.assertIsNone(safe_image("/favicon.png","ohmyblog"))
if __name__=="__main__":unittest.main()
