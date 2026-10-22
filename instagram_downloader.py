import asyncio
import logging
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

import aiohttp
import instaloader

from config import DOWNLOAD_TIMEOUT, MAX_FILE_SIZE_BYTES, DOWNLOAD_DIR
from utils.helpers import sanitize_filename

# Filter out urllib3 LibreSSL warning
warnings.filterwarnings("ignore", category=Warning)

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

@dataclass
class InstagramMediaItem:
    media_type: str  # "video" or "photo"
    url: str

@dataclass
class InstagramMedia:
    shortcode: str
    url: str
    caption: str = ""
    author_username: str = ""
    is_video: bool = False
    video_url: Optional[str] = None
    photo_url: Optional[str] = None
    is_carousel: bool = False
    items: List[InstagramMediaItem] = field(default_factory=list)
    likes: int = 0
    comments: int = 0
    raw_data: Dict[str, Any] = field(default_factory=dict)

# In-memory cache for recent Instagram media
_IG_CACHE: Dict[str, InstagramMedia] = {}

def cache_ig_media(media: InstagramMedia):
    """Store media in cache."""
    if len(_IG_CACHE) > 200:
        oldest_key = next(iter(_IG_CACHE))
        _IG_CACHE.pop(oldest_key, None)
    _IG_CACHE[media.shortcode] = media

def get_cached_ig_media(shortcode: str) -> Optional[InstagramMedia]:
    """Retrieve media from cache."""
    return _IG_CACHE.get(shortcode)

class InstagramDownloader:
    """Handles fetching and downloading Instagram Reels, Posts, and Carousels."""

    def __init__(self):
        # Configure Instaloader context without saving any extraneous files
        self.loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True
        )

    @staticmethod
    def extract_shortcode(url: str) -> Optional[str]:
        """Extract shortcode from Instagram URL."""
        match = re.search(r"/(?:p|reel|reels|tv|share/(?:reel|p))/([a-zA-Z0-9_-]+)", url)
        if match:
            return match.group(1)
        return None

    def _fetch_post_sync(self, shortcode: str, original_url: str) -> Optional[InstagramMedia]:
        """Synchronous fetch using Instaloader (to be run in threadpool)."""
        try:
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            
            caption = post.caption or ""
            author_username = post.owner_username or ""
            likes = post.likes or 0
            comments = post.comments or 0
            typename = post.typename

            items: List[InstagramMediaItem] = []
            is_carousel = False
            video_url = None
            photo_url = None

            if typename == "GraphSidecar":
                is_carousel = True
                try:
                    for node in post.get_sidecar_nodes():
                        if node.is_video and node.video_url:
                            items.append(InstagramMediaItem(media_type="video", url=node.video_url))
                        elif node.display_url:
                            items.append(InstagramMediaItem(media_type="photo", url=node.display_url))
                except Exception as e:
                    logger.warning(f"Error fetching sidecar nodes for {shortcode}: {e}")

            elif post.is_video:
                video_url = post.video_url
                if video_url:
                    items.append(InstagramMediaItem(media_type="video", url=video_url))
            else:
                photo_url = post.url
                if photo_url:
                    items.append(InstagramMediaItem(media_type="photo", url=photo_url))

            media = InstagramMedia(
                shortcode=shortcode,
                url=original_url,
                caption=caption,
                author_username=author_username,
                is_video=post.is_video,
                video_url=video_url,
                photo_url=photo_url,
                is_carousel=is_carousel,
                items=items,
                likes=likes,
                comments=comments,
                raw_data={
                    "shortcode": shortcode,
                    "caption": caption,
                    "author_username": author_username,
                    "likes": likes,
                    "comments": comments
                }
            )
            return media

        except Exception as e:
            logger.error(f"Instaloader failed for shortcode {shortcode}: {e}", exc_info=True)
            return None

    async def fetch_media_info(self, url: str) -> Optional[InstagramMedia]:
        """Asynchronously extract Instagram media info."""
        shortcode = self.extract_shortcode(url)
        if not shortcode:
            logger.warning(f"Could not extract Instagram shortcode from {url}")
            return None

        # Check cache first
        cached = get_cached_ig_media(shortcode)
        if cached:
            return cached

        # Run Instaloader in thread pool so it does not block the asyncio event loop
        media = await asyncio.to_thread(self._fetch_post_sync, shortcode, url)
        if media:
            cache_ig_media(media)
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
            "Referer": "https://www.instagram.com/",
        }

        timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)

        try:
            async with aiohttp.ClientSession(headers=download_headers, timeout=timeout) as session:
                async with session.get(file_url) as response:
                    if response.status != 200:
                        return False, None, f"HTTP error {response.status} when downloading file"

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
