"""Only explicit, campaign-specific public Dinnerqueen media instructions."""
import re
from collect import plain

BANNER_PATTERNS=(
    (re.compile(r"(?:인스타\s*릴스|인스타그램\s*릴스)\s*(?:방문|배송)?\s*캠페인\s*이에요",re.I),
     "인스타그램","reels_banner"),
    (re.compile(r"(?:네이버\s*)?클립\s*(?:방문|배송)?\s*캠페인\s*이에요",re.I),
     "네이버클립","clip_banner"),
    (re.compile(r"유튜브\s*쇼츠\s*(?:방문|배송)?\s*캠페인\s*이에요",re.I),
     "쇼츠","shorts_banner"),
)
BLOG_REQUIRED=(
    re.compile(r"블로그\s*필수\s*기재\s*사항",re.I),
    re.compile(r"블로그\s*제목\s*에.{0,155}?(?:필수|반드시)",re.I),
    re.compile(r"블로그\s*포스팅\s*(?:을|은|을\s*꼭)?\s*(?:해야|필수|반드시)",re.I),
    re.compile(r"네이버\s*블로그\s*리뷰\s*(?:작성|게시|발행)\s*필수",re.I),
)

def verified_dinnerqueen_media(markup):
    """Return (channel,evidence) or (None,None).

    Only a banner specifically describing this campaign, or a mandatory
    blog-reviewer mission qualifies. Shared nav, copy scripts, brand names,
    and the conditional '블로그 작성의 경우' do NOT qualify.
    """
    text=plain(markup)
    start=text.find("캠페인 배너")
    if start>=0:
        tail=text[start:start+1200]
        end=tail.find("캠페인 신청 섹션")
        banner=tail[:end] if end>=0 else tail[:500]
        found=[(ch,tag) for rx,ch,tag in BANNER_PATTERNS if rx.search(banner)]
        if len(found)==1:
            ch,tag=found[0]
            return ch,"dinnerqueen_detail:"+tag
        if len(found)>1:
            return None,None
    mission_start=text.find("리뷰어 미션")
    if mission_start<0:
        return None,None
    mission=text[mission_start:mission_start+4000]
    end=mission.find("추가 안내사항")
    if end>=0:mission=mission[:end]
    if any(rx.search(mission) for rx in BLOG_REQUIRED):
        return "블로그","dinnerqueen_detail:mandatory_blog_mission"
    return None,None
