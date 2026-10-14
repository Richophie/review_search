import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from popomon_revu_cards import parse_card,original_image

class PublicCardTests(unittest.TestCase):
    def test_popomon_verified_card(self):
        c=dict(url="https://popomon.com/next/campaign/315741",
          title="[부산/해운대구]트레블로지 스위트 부산 센텀",
          text="릴스\n방문형\n[부산/해운대구]트레블로지 스위트 부산 센텀\n7일 남음20만원 상당 숙박권\n신청 256/1",
          status="7일 남음",benefit="20만원 상당 숙박권",image="/next/_next/image?url=https%3A%2F%2Fd17jwiodubhsh2.cloudfront.net%2FUPLOAD%2FCAMPAIGN_THUMB%2Ffile.jpg&w=640&q=75",
          badges=["릴스","방문형"],type="방문형")
        v=parse_card(c,"popomon")
        self.assertEqual(v["id"],"popomon:315741")
        self.assertEqual(v["channels"],["인스타그램"])
        self.assertEqual(v["apply_deadline"][-2:],v["apply_deadline"][-2:])
        self.assertEqual(v["slots"],1)
        self.assertEqual(v["applicants"],256)
        self.assertEqual(v["region_sido"],"부산")
        self.assertTrue(v["image_url"].startswith("https://d17jwiodubhsh2.cloudfront.net/"))
    def test_revu_unknown_date_does_not_invent_deadline(self):
        c=dict(url="https://webview.revu.net/campaign/1414610",
          title="[틸아이다이] 26FW 4차 컬렉션",
          status="마감 임박",benefit="상의 1개",
          text="[틸아이다이] 26FW 4차 컬렉션\n상의 1개\n마감 임박\n신청 1,937 / 10명",
          image="https://files.weble.net/campaign/data/1414610/thumb200.webp",
          mediaIcons=["/assets/icons/media/naver-color.svg"])
        v=parse_card(c,"revu")
        self.assertIsNone(v["apply_deadline"])
        self.assertTrue(v["open_verified"])
        self.assertEqual(v["channels"],["블로그"])
        self.assertEqual(v["competition_ratio"],193.7)
    def test_closed_or_unproven_rejected(self):
        c=dict(url="https://webview.revu.net/campaign/123456",
          title="[해운대] 방문형 숙박 캠페인",status="신청 마감",
          text="신청 마감\n신청 2 / 3명")
        self.assertIsNone(parse_card(c,"revu"))
        c["status"]="선정 완료"
        self.assertIsNone(parse_card(c,"revu"))
    def test_untrusted_image_not_adopted(self):
        self.assertIsNone(original_image("/next/_next/image?url=https%3A%2F%2Fbad.example%2Fx.jpg","popomon"))
    def test_bare_no_apply_information_rejected(self):
        c=dict(url="https://popomon.com/next/campaign/99",title="[서울/강남구] 테스트",
              text="신청 1/2",status="",badges=[])
        self.assertIsNone(parse_card(c,"popomon"))

if __name__=="__main__":unittest.main()
