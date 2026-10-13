import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collect import media_from_bracketed_title

class ExplicitTitleMediaTest(unittest.TestCase):
    def test_actual_beautyqueen_reels_badge(self):
        self.assertEqual(media_from_bracketed_title("[릴스][스마트에버] 터치톡 뷰티디바이스 SET"),["인스타그램"])
    def test_multiple_prefixes(self):
        self.assertEqual(media_from_bracketed_title("[서울 강남][클립][릴스] 식사권"),["네이버클립","인스타그램"])
    def test_not_a_guess(self):
        self.assertEqual(media_from_bracketed_title("[스마트에버] 터치톡 뷰티디바이스 SET"),[])
        self.assertEqual(media_from_bracketed_title("[뷰티] 클립 모양 액세서리"),[])
        self.assertEqual(media_from_bracketed_title("블로그 꾸미기 강좌"),[])
    def test_exact_media(self):
        self.assertEqual(media_from_bracketed_title("[네이버 블로그][서울] 맛집"),["블로그"])
        self.assertEqual(media_from_bracketed_title("[유튜브 쇼츠] 여행"),["쇼츠"])
        self.assertEqual(media_from_bracketed_title("[릴스][릴스] 제품"),["인스타그램"])

if __name__=="__main__": unittest.main()
