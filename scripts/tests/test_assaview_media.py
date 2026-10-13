import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collect import assaview_media_icons

class AssaviewMediaIconTest(unittest.TestCase):
    def test_official_public_blog_and_reels_icons(self):
        card = ('<img src="./img/icon/blog_icon.png" class="review_type_icon">'
                '<img src="./img/icon/reels_icon.png" class="review_type_icon">')
        self.assertEqual(assaview_media_icons(card),
                         (["블로그","인스타그램"],["blog_icon.png","reels_icon.png"]))
    def test_shop_is_not_a_social_medium(self):
        card='<img src="./img/icon/shop_icon.png" class="review_type_icon">'
        self.assertEqual(assaview_media_icons(card),([],[]))
    def test_unrelated_product_picture_is_not_media(self):
        card='<img src="./img/icon/blog_icon.png" class="product_thumb">'
        self.assertEqual(assaview_media_icons(card),([],[]))

if __name__=="__main__":unittest.main()
