import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dinnerqueen_media import verified_dinnerqueen_media

class DinnerqueenMediaEvidenceTest(unittest.TestCase):
    def test_explicit_reels_banner(self):
        h="<div>캠페인 배너 --> 인스타 릴스 방문 캠페인 이에요 동영상을 촬영해요 캠페인 신청 섹션</div>"
        self.assertEqual(verified_dinnerqueen_media(h),
                         ("인스타그램","dinnerqueen_detail:reels_banner"))
    def test_actual_mandatory_blog_title_instruction(self):
        h="<div>리뷰어 미션 ★★ 블로그 제목에 업체명, 지역 키워드를 반드시 기입 바랍니다 추가 안내사항</div>"
        self.assertEqual(verified_dinnerqueen_media(h),
                         ("블로그","dinnerqueen_detail:mandatory_blog_mission"))
    def test_generic_conditional_blog_instructions_are_insufficient(self):
        h="<div>리뷰어 미션 블로그 작성의 경우 사진 15장 이상 영상 1개 필수 첨부 부탁드립니다 추가 안내사항</div>"
        self.assertEqual(verified_dinnerqueen_media(h),(None,None))
    def test_site_wide_nav_and_copy_script_are_insufficient(self):
        h="<div>블로그 위젯 네이버 클립 선정자용 복사 일반딜 리뷰어 미션 키워드 필수 영상 1개</div>"
        self.assertEqual(verified_dinnerqueen_media(h),(None,None))
    def test_campaign_banner_for_unknown_media(self):
        h="<div>캠페인 배너 --> --> [서울 종로] 리향 캠페인 신청 섹션 리뷰어 미션 키워드 필수 블로그 작성의 경우</div>"
        self.assertEqual(verified_dinnerqueen_media(h),(None,None))
    def test_blog_mandatory_section(self):
        h="리뷰어 미션 ★★ 블로그 필수 기재 사항 ★★ 추가 안내사항"
        self.assertEqual(verified_dinnerqueen_media(h),
                         ("블로그","dinnerqueen_detail:mandatory_blog_mission"))
if __name__=="__main__": unittest.main()
