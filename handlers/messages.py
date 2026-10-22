import html
import logging
from typing import List
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
    InputMediaVideo,
    constants
)
from telegram.ext import ContextTypes

from config import RATE_LIMIT_SECONDS
from utils.helpers import (
    extract_tiktok_url,
    extract_instagram_url,
    format_caption,
    format_instagram_caption
)
from utils.rate_limiter import RateLimiter
from tiktok_downloader import TikTokDownloader, cache_media
from instagram_downloader import InstagramDownloader

logger = logging.getLogger(__name__)

tiktok_downloader = TikTokDownloader()
instagram_downloader = InstagramDownloader()
rate_limiter = RateLimiter(cooldown_seconds=RATE_LIMIT_SECONDS)

async def handle_tiktok(message, tiktok_url: str, context: ContextTypes.DEFAULT_TYPE):
    """Handle TikTok video/slideshow download flow."""
    status_msg = await message.reply_text("⏳ <i>Processing TikTok link...</i>", parse_mode="HTML")

    try:
        media = await tiktok_downloader.fetch_media_info(tiktok_url)
        if not media:
            await status_msg.edit_text(
                "❌ <b>Could not download this TikTok.</b>\n"
                "The video might be private, deleted, or restricted.",
                parse_mode="HTML"
            )
            return

        cache_media(media)

        bot_username = context.bot.username
        caption = format_caption(media.raw_data, bot_username)

        # Build inline keyboard buttons
        buttons: List[List[InlineKeyboardButton]] = []
        action_row: List[InlineKeyboardButton] = []

        if media.music_url:
            action_row.append(
                InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"audio:{media.id}")
            )

        if media.hd_video_url and media.hd_video_url != media.video_url:
            action_row.append(
                InlineKeyboardButton("🎬 HD Video", callback_data=f"hd:{media.id}")
            )

        if action_row:
            buttons.append(action_row)

        buttons.append([
            InlineKeyboardButton("🔗 Open in TikTok", url=media.url)
        ])
        reply_markup = InlineKeyboardMarkup(buttons)

        # Photo Slideshow / Carousel
        if media.is_slideshow and media.image_urls:
            await status_msg.edit_text(
                f"📸 <i>Downloading photo album ({len(media.image_urls)} photos)...</i>",
                parse_mode="HTML"
            )

            media_groups = []
            current_group = []

            for i, img_url in enumerate(media.image_urls):
                photo_item = InputMediaPhoto(
                    media=img_url,
                    caption=caption if i == 0 else None,
                    parse_mode="HTML" if i == 0 else None
                )
                current_group.append(photo_item)
                if len(current_group) == 10:
                    media_groups.append(current_group)
                    current_group = []

            if current_group:
                media_groups.append(current_group)

            for group in media_groups:
                await message.reply_media_group(media=group)

            if buttons:
                await message.reply_text(
                    "👇 <b>Options:</b>",
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )

            await status_msg.delete()
            return

        # Regular Video
        download_url = media.video_url or media.hd_video_url
        if not download_url:
            await status_msg.edit_text("❌ No playable video source was found for this link.")
            return

        await status_msg.edit_text("⏳ <i>Downloading video (no watermark)...</i>", parse_mode="HTML")

        filename = f"video_{media.id}.mp4"
        success, filepath, err = await tiktok_downloader.download_file(download_url, filename)

        if not success or not filepath:
            if err and err.startswith("FILE_TOO_LARGE"):
                size_mb = err.split(":")[1]
                large_file_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Download Directly in Browser", url=download_url)],
                    [InlineKeyboardButton("🔗 View on TikTok", url=media.url)]
                ])
                await status_msg.edit_text(
                    f"⚠️ <b>Video file is too large ({size_mb} MB)</b> for Telegram bot upload (50MB limit).\n\n"
                    "👉 You can download it directly using the button below:",
                    parse_mode="HTML",
                    reply_markup=large_file_keyboard
                )
            else:
                await status_msg.edit_text(f"❌ Failed to download video: {err or 'Unknown error'}")
            return

        try:
            with open(filepath, "rb") as video_file:
                await message.reply_video(
                    video=video_file,
                    caption=caption,
                    parse_mode="HTML",
                    supports_streaming=True,
                    duration=media.duration if media.duration > 0 else None,
                    reply_markup=reply_markup
                )
            await status_msg.delete()
        finally:
            TikTokDownloader.cleanup_file(filepath)

    except Exception as e:
        logger.error(f"Error processing TikTok link {tiktok_url}: {e}", exc_info=True)
        try:
            await status_msg.edit_text(
                "❌ An unexpected error occurred while processing your request. Please try again later."
            )
        except Exception:
            pass

async def handle_instagram(message, ig_url: str, context: ContextTypes.DEFAULT_TYPE):
    """Handle Instagram Reel/Post/Carousel download flow."""
    status_msg = await message.reply_text("⏳ <i>Processing Instagram link...</i>", parse_mode="HTML")

    try:
        media = await instagram_downloader.fetch_media_info(ig_url)
        if not media or (not media.video_url and not media.photo_url and not media.items):
            await status_msg.edit_text(
                "❌ <b>Could not download this Instagram post.</b>\n"
                "The post might be private, deleted, or require login.",
                parse_mode="HTML"
            )
            return

        bot_username = context.bot.username
        caption = format_instagram_caption(media.raw_data, bot_username)

        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Open in Instagram", url=media.url)]
        ])

        # Case 1: Carousel / Album (multiple media)
        if media.is_carousel and media.items:
            await status_msg.edit_text(
                f"📸 <i>Downloading Instagram album ({len(media.items)} items)...</i>",
                parse_mode="HTML"
            )

            # Limit to 10 items per media group as per Telegram limit
            media_group = []
            for i, item in enumerate(media.items[:10]):
                item_caption = caption if i == 0 else None
                if item.media_type == "video":
                    media_group.append(InputMediaVideo(
                        media=item.url,
                        caption=item_caption,
                        parse_mode="HTML" if item_caption else None,
                        supports_streaming=True
                    ))
                else:
                    media_group.append(InputMediaPhoto(
                        media=item.url,
                        caption=item_caption,
                        parse_mode="HTML" if item_caption else None
                    ))

            if media_group:
                await message.reply_media_group(media=media_group)
                await message.reply_text(
                    "👇 <b>Link:</b>",
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
                await status_msg.delete()
                return

        # Case 2: Video (Reel / Video post)
        if media.is_video and media.video_url:
            await status_msg.edit_text("⏳ <i>Downloading Instagram Reel...</i>", parse_mode="HTML")

            filename = f"ig_reel_{media.shortcode}.mp4"
            success, filepath, err = await instagram_downloader.download_file(media.video_url, filename)

            if not success or not filepath:
                if err and err.startswith("FILE_TOO_LARGE"):
                    size_mb = err.split(":")[1]
                    await status_msg.edit_text(
                        f"⚠️ Video size is {size_mb} MB (exceeds Telegram 50MB limit).\n"
                        f"👉 <a href=\"{media.video_url}\">Click here to download directly</a>",
                        parse_mode="HTML"
                    )
                else:
                    await status_msg.edit_text(f"❌ Failed to download Instagram video: {err or 'Unknown error'}")
                return

            try:
                with open(filepath, "rb") as video_file:
                    await message.reply_video(
                        video=video_file,
                        caption=caption,
                        parse_mode="HTML",
                        supports_streaming=True,
                        reply_markup=reply_markup
                    )
                await status_msg.delete()
            finally:
                InstagramDownloader.cleanup_file(filepath)
            return

        # Case 3: Single Photo
        if media.photo_url:
            await status_msg.edit_text("⏳ <i>Sending Instagram photo...</i>", parse_mode="HTML")
            await message.reply_photo(
                photo=media.photo_url,
                caption=caption,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            await status_msg.delete()
            return

    except Exception as e:
        logger.error(f"Error processing Instagram link {ig_url}: {e}", exc_info=True)
        try:
            await status_msg.edit_text(
                "❌ An unexpected error occurred while processing the Instagram link. Please try again later."
            )
        except Exception:
            pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process incoming text messages, detect TikTok or Instagram links, and download media."""
    message = update.effective_message
    if not message or not message.text:
        return

    text = message.text.strip()
    tiktok_url = extract_tiktok_url(text)
    instagram_url = extract_instagram_url(text)

    # If in private chat and no supported link was found, guide the user
    if not tiktok_url and not instagram_url:
        if update.effective_chat.type == constants.ChatType.PRIVATE:
            await message.reply_html(
                "ℹ️ <b>Please send a valid TikTok or Instagram link</b>\n\n"
                "<i>Examples:</i>\n"
                "• <b>TikTok:</b> <code>https://vm.tiktok.com/...</code>\n"
                "• <b>Instagram:</b> <code>https://www.instagram.com/reel/...</code>"
            )
        return

    user_id = update.effective_user.id if update.effective_user else 0
    if not rate_limiter.is_allowed(user_id):
        remaining = rate_limiter.time_remaining(user_id)
        await message.reply_text(
            f"⏳ Please wait <b>{remaining}s</b> before sending another request.",
            parse_mode="HTML"
        )
        return

    if tiktok_url:
        await handle_tiktok(message, tiktok_url, context)
    elif instagram_url:
        await handle_instagram(message, instagram_url, context)
