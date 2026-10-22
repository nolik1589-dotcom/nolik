import re
import html
from typing import Optional, Dict, Any

# Regex to detect TikTok and Douyin URLs
TIKTOK_URL_PATTERN = re.compile(
    r"https?://(?:(?:[a-zA-Z0-9-]+\.)?tiktok\.com|(?:www\.)?douyin\.com)/[^\s]+",
    re.IGNORECASE
)

# Regex to detect Instagram URLs (Reels, Posts, IGTV, Share links)
INSTAGRAM_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?instagram\.com/(p|reel|reels|tv|share/(?:reel|p))/([a-zA-Z0-9_-]+)",
    re.IGNORECASE
)

def extract_tiktok_url(text: str) -> Optional[str]:
    """
    Extract first TikTok/Douyin URL from text.
    Handles extra trailing punctuation (like ?, !, .) from user messages.
    """
    if not text:
        return None
    match = TIKTOK_URL_PATTERN.search(text)
    if not match:
        return None
    
    url = match.group(0)
    # Strip common punctuation attached to the end of URLs in natural text
    url = re.sub(r'[\)\]\>,\.;:!?]+$', '', url)
    return url

def extract_instagram_url(text: str) -> Optional[str]:
    """
    Extract first Instagram Reel/Post URL from text.
    Normalizes to clean canonical URL without tracking parameters.
    """
    if not text:
        return None
    match = INSTAGRAM_URL_PATTERN.search(text)
    if not match:
        return None
    
    endpoint = match.group(1)
    shortcode = match.group(2)
    return f"https://www.instagram.com/{endpoint}/{shortcode}/"

def format_number(num: Optional[int]) -> str:
    """Format large numbers into human-readable K/M strings."""
    if num is None:
        return "0"
    try:
        num = int(num)
    except (ValueError, TypeError):
        return "0"
        
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)

def format_caption(data: Dict[str, Any], bot_username: Optional[str] = None) -> str:
    """
    Format rich HTML caption for Telegram media.
    Enforces Telegram's 1024-character caption limit.
    """
    title = data.get("title", "").strip()
    author = data.get("author", {}) or {}
    nickname = author.get("nickname") or "TikTok Creator"
    unique_id = author.get("unique_id") or ""
    music_info = data.get("music_info", {}) or {}
    music_title = music_info.get("title") or data.get("music_title") or "Original Sound"

    likes = format_number(data.get("digg_count"))
    comments = format_number(data.get("comment_count"))
    shares = format_number(data.get("share_count"))
    views = format_number(data.get("play_count"))

    # Escape HTML to prevent injection issues
    safe_nickname = html.escape(nickname)
    safe_unique_id = html.escape(unique_id)
    safe_music = html.escape(music_title)
    
    # Creator link
    if unique_id:
        creator_line = f"👤 <b>Creator:</b> <a href=\"https://www.tiktok.com/@{safe_unique_id}\">{safe_nickname}</a> (@{safe_unique_id})"
    else:
        creator_line = f"👤 <b>Creator:</b> {safe_nickname}"

    stats_line = f"❤️ <b>{likes}</b>  💬 <b>{comments}</b>  🔁 <b>{shares}</b>  👁 <b>{views}</b>"
    music_line = f"🎵 <i>{safe_music}</i>"
    
    footer = f"\n🤖 @{bot_username}" if bot_username else ""

    # Truncate title if needed to stay below 1024 characters
    base_length = len(creator_line) + len(stats_line) + len(music_line) + len(footer) + 50
    max_title_len = max(100, 1024 - base_length)
    
    if len(title) > max_title_len:
        title = title[:max_title_len - 3] + "..."
    safe_title = html.escape(title)

    lines = []
    if safe_title:
        lines.append(f"📝 <b>{safe_title}</b>\n")
    lines.append(creator_line)
    lines.append(music_line)
    lines.append(stats_line)
    if footer:
        lines.append(footer)

    return "\n".join(lines)

def format_instagram_caption(data: Dict[str, Any], bot_username: Optional[str] = None) -> str:
    """
    Format rich HTML caption for Instagram media.
    Enforces Telegram's 1024-character caption limit.
    """
    caption = data.get("caption", "") or data.get("title", "") or ""
    caption = caption.strip()
    author_username = data.get("author_username") or data.get("owner_username") or "instagram"
    likes = format_number(data.get("likes"))
    comments = format_number(data.get("comments"))

    safe_username = html.escape(author_username)
    creator_line = f"👤 <b>Author:</b> <a href=\"https://www.instagram.com/{safe_username}/\">@{safe_username}</a>"
    stats_line = f"❤️ <b>{likes}</b>  💬 <b>{comments}</b>"
    footer = f"\n🤖 @{bot_username}" if bot_username else ""

    base_length = len(creator_line) + len(stats_line) + len(footer) + 50
    max_caption_len = max(100, 1024 - base_length)
    if len(caption) > max_caption_len:
        caption = caption[:max_caption_len - 3] + "..."
    safe_caption = html.escape(caption)

    lines = []
    if safe_caption:
        lines.append(f"📝 <b>{safe_caption}</b>\n")
    lines.append(creator_line)
    lines.append(stats_line)
    if footer:
        lines.append(footer)

    return "\n".join(lines)

def sanitize_filename(name: str) -> str:
    """Sanitize filename to avoid filesystem issues."""
    return re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)
