import asyncio
import unittest
from pathlib import Path
from utils.helpers import (
    extract_tiktok_url,
    extract_instagram_url,
    format_number,
    format_caption,
    format_instagram_caption
)
from utils.rate_limiter import RateLimiter
from tiktok_downloader import TikTokDownloader, TikTokMedia
from instagram_downloader import InstagramDownloader

class TestBotComponents(unittest.IsolatedAsyncioTestCase):

    def test_extract_tiktok_url(self):
        self.assertEqual(
            extract_tiktok_url("https://www.tiktok.com/@user/video/1234567890"),
            "https://www.tiktok.com/@user/video/1234567890"
        )
        text = "Check this out: https://vm.tiktok.com/ZM8abcDEF/! It is awesome"
        self.assertEqual(
            extract_tiktok_url(text),
            "https://vm.tiktok.com/ZM8abcDEF/"
        )
        self.assertIsNone(extract_tiktok_url("Hello world, no link here"))

    def test_extract_instagram_url(self):
        # Reels
        self.assertEqual(
            extract_instagram_url("https://www.instagram.com/reel/C5WTtLuPrkq/"),
            "https://www.instagram.com/reel/C5WTtLuPrkq/"
        )
        # Post with tracking params
        self.assertEqual(
            extract_instagram_url("Look at this post: https://www.instagram.com/p/C5WTtLuPrkq/?utm_source=ig"),
            "https://www.instagram.com/p/C5WTtLuPrkq/"
        )
        # None
        self.assertIsNone(extract_instagram_url("No link in this message"))

    def test_format_number(self):
        self.assertEqual(format_number(950), "950")
        self.assertEqual(format_number(1500), "1.5K")
        self.assertEqual(format_number(2300000), "2.3M")
        self.assertEqual(format_number(None), "0")

    def test_rate_limiter(self):
        limiter = RateLimiter(cooldown_seconds=1)
        self.assertTrue(limiter.is_allowed(12345))
        self.assertFalse(limiter.is_allowed(12345))

    def test_format_instagram_caption(self):
        data = {
            "caption": "Amazing travel destination!",
            "author_username": "traveler",
            "likes": 50000,
            "comments": 230
        }
        caption = format_instagram_caption(data, "MediaBot")
        self.assertIn("@traveler", caption)
        self.assertIn("50.0K", caption)
        self.assertIn("@MediaBot", caption)
        self.assertTrue(len(caption) <= 1024)

    async def test_tiktok_fetch_and_download(self):
        downloader = TikTokDownloader()
        test_url = "https://www.tiktok.com/@tiktok/video/7460937381265411370"
        media = await downloader.fetch_media_info(test_url)
        
        self.assertIsNotNone(media)
        self.assertTrue(len(media.id) > 0)
        self.assertIsNotNone(media.video_url)
        self.assertEqual(media.author_username, "tiktok")

        caption = format_caption(media.raw_data, "TestBot")
        self.assertIn("TikTok", caption)
        self.assertIn("@TestBot", caption)
        self.assertTrue(len(caption) <= 1024)

    def test_instagram_shortcode_extractor(self):
        downloader = InstagramDownloader()
        self.assertEqual(downloader.extract_shortcode("https://www.instagram.com/reel/C5WTtLuPrkq/"), "C5WTtLuPrkq")
        self.assertEqual(downloader.extract_shortcode("https://www.instagram.com/p/ABC123xyz/?igsh=abc"), "ABC123xyz")

if __name__ == "__main__":
    unittest.main()
