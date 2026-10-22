import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

import aiohttp
from config import TIKWM_API_URL, DOWNLOAD_TIMEOUT, MAX_FILE_SIZE_BYTES, DOWNLOAD_DIR
from utils.helpers import sanitize_filename

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

@dataclass
class TikTokMedia:
    id: str
    url: str
    title: str = ""
    author_name: str = "TikTok Creator"
    author_username: str = ""
    author_avatar: str = ""
    video_url: Optional[str] = None
    hd_video_url: Optional[str] = None
    music_url: Optional[str] = None
    music_title: str = "Original Sound"
    music_author: str = ""
    cover_url: Optional[str] = None
    duration: int = 0
    size_bytes: int = 0
    hd_size_bytes: int = 0
    is_slideshow: bool = False
    image_urls: List[str] = field(default_factory=list)
    likes: int = 0
    comments: int = 0
    shares: int = 0
    views: int = 0
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def best_video_url(self) -> Optional[str]:
        """Return HD video URL if within limits, otherwise standard."""
        return self.hd_video_url or self.video_url

# In-memory cache for recent TikTok media items (max 200 items)
_MEDIA_CACHE: Dict[str, TikTokMedia] = {}

def cache_media(media: TikTokMedia):
    """Store media in cache."""
    if len(_MEDIA_CACHE) > 200:
        # Evict oldest entry
        oldest_key = next(iter(_MEDIA_CACHE))
        _MEDIA_CACHE.pop(oldest_key, None)
    _MEDIA_CACHE[media.id] = media

def get_cached_media(media_id: str) -> Optional[TikTokMedia]:
    """Retrieve media from cache."""
    return _MEDIA_CACHE.get(media_id)

class TikTokDownloader:
    """Handles fetching metadata and downloading TikTok media."""

    def __init__(self):
        self.headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
        }

    async def fetch_media_info(self, tiktok_url: str) -> Optional[TikTokMedia]:
        """Fetch TikTok metadata via TikWM API."""
        params = {
            "url": tiktok_url,
            "hd": 1
        }
        
        timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)
        
        async with aiohttp.ClientSession(headers=self.headers, timeout=timeout) as session:
            try:
                async with session.get(TIKWM_API_URL, params=params) as response:
                    if response.status != 200:
                        logger.error(f"TikWM returned status {response.status}")
                        return None
                    
                    payload = await response.json()
            except Exception as e:
                logger.error(f"Network error querying TikWM API: {e}", exc_info=True)
                return None

        if payload.get("code") != 0:
            msg = payload.get("msg", "Unknown error")
            logger.warning(f"TikWM error message: {msg} for URL: {tiktok_url}")
            return None

        data = payload.get("data", {})
        if not data:
            return None

        # Build absolute URLs if relative URLs are provided
        def make_absolute(path: Optional[str]) -> Optional[str]:
            if not path:
                return None
            if path.startswith("/"):
                return f"https://tikwm.com{path}"
            return path

        images = data.get("images") or []
        is_slideshow = bool(images)
        author = data.get("author") or {}
        music_info = data.get("music_info") or {}

        media = TikTokMedia(
            id=str(data.get("id") or ""),
            url=tiktok_url,
            title=data.get("title") or "",
            author_name=author.get("nickname") or "TikTok Creator",
            author_username=author.get("unique_id") or "",
            author_avatar=author.get("avatar") or "",
            video_url=make_absolute(data.get("play")),
            hd_video_url=make_absolute(data.get("hdplay")),
            music_url=make_absolute(data.get("music")),
            music_title=music_info.get("title") or "Original Sound",
            music_author=music_info.get("author") or "",
            cover_url=make_absolute(data.get("cover")),
            duration=int(data.get("duration") or 0),
            size_bytes=int(data.get("size") or 0),
            hd_size_bytes=int(data.get("hd_size") or 0),
            is_slideshow=is_slideshow,
            image_urls=[make_absolute(img) for img in images if img],
            likes=int(data.get("digg_count") or 0),
            comments=int(data.get("comment_count") or 0),
            shares=int(data.get("share_count") or 0),
            views=int(data.get("play_count") or 0),
            raw_data=data
        )
        return media

    async def download_file(
        self,
        file_url: str,
        filename: str,
        max_bytes: int = MAX_FILE_SIZE_BYTES
    ) -> Tuple[bool, Optional[Path], Optional[str]]:
        """
        Download a file safely to disk with size check and timeout.
        Returns: (success: bool, path: Optional[Path], error_message: Optional[str])
        """
        safe_name = sanitize_filename(filename)
        dest_path = DOWNLOAD_DIR / safe_name

        download_headers = {
            "User-Agent": USER_AGENT,
            "Referer": "https://www.tiktok.com/",
        }

        timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)

        try:
            async with aiohttp.ClientSession(headers=download_headers, timeout=timeout) as session:
                async with session.get(file_url) as response:
                    if response.status != 200:
                        return False, None, f"HTTP error {response.status} when downloading file"

                    # Verify Content-Length header if present
                    content_length = response.headers.get("Content-Length")
                    if content_length and int(content_length) > max_bytes:
                        mb_size = int(content_length) / (1024 * 1024)
                        return False, None, f"FILE_TOO_LARGE:{mb_size:.1f}"

                    downloaded = 0
                    with open(dest_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(64 * 1024):
                            downloaded += len(chunk)
                            if downloaded > max_bytes:
                                f.close()
                                if dest_path.exists():
                                    dest_path.unlink()
                                mb_size = downloaded / (1024 * 1024)
                                return False, None, f"FILE_TOO_LARGE:{mb_size:.1f}"
                            f.write(chunk)

            return True, dest_path, None

        except asyncio.TimeoutError:
            if dest_path.exists():
                dest_path.unlink()
            return False, None, "Download timed out"
        except Exception as e:
            if dest_path.exists():
                dest_path.unlink()
            logger.error(f"Error downloading {file_url}: {e}", exc_info=True)
            return False, None, str(e)

    @staticmethod
    def cleanup_file(path: Optional[Path]):
        """Safely remove temporary file."""
        if path and isinstance(path, Path) and path.exists():
            try:
                path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {path}: {e}")
