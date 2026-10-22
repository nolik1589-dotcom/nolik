import html
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from tiktok_downloader import TikTokDownloader, get_cached_media
from handlers.commands import help_command, about_command

logger = logging.getLogger(__name__)
downloader = TikTokDownloader()

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Router for all inline button callbacks."""
    query = update.callback_query
    if not query:
        return

    data = query.data or ""

    if data == "btn_start":
        await query.answer()
        user = update.effective_user
        name = html.escape(user.first_name) if user and user.first_name else "there"
        welcome_text = (
            f"👋 <b>Привет, {name}!</b>\n\n"
            "🎬 <b>Media Downloader Bot</b> скачивает видео и фото без водяных знаков из <b>TikTok</b> и <b>Instagram</b>:\n\n"
            "✨ <b>Возможности:</b>\n"
            "• 📱 <b>TikTok:</b> HD видео без водяных знаков, MP3 аудио, фото-слайдшоу\n"
            "• 📸 <b>Instagram:</b> Reels, посты с видео, одиночные фото и карусели (альбомы)\n"
            "• ⚡ Быстрая отправка прямо в Telegram\n\n"
            "👉 <b>Как пользоваться:</b>\n"
            "Просто отправьте сюда ссылку на TikTok или Instagram!\n\n"
            "<i>Примеры:</i>\n"
            "• <code>https://vm.tiktok.com/...</code>\n"
            "• <code>https://www.instagram.com/reel/...</code>"
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📖 Инструкция", callback_data="btn_help"),
                InlineKeyboardButton("ℹ️ О боте", callback_data="btn_about")
            ]
        ])
        await query.edit_message_text(welcome_text, parse_mode="HTML", reply_markup=keyboard)
        return

    if data == "btn_help":
        await help_command(update, context)
        return

    if data == "btn_about":
        await about_command(update, context)
        return

    if data.startswith("audio:"):
        media_id = data.split(":", 1)[1]
        media = get_cached_media(media_id)
        if not media or not media.music_url:
            await query.answer("❌ Audio is no longer available in cache. Please resend the link.", show_alert=True)
            return

        await query.answer("🎵 Downloading audio...")
        status_msg = await query.message.reply_text("⏳ <i>Extracting audio track...</i>", parse_mode="HTML")

        filename = f"audio_{media.id}.mp3"
        success, filepath, err = await downloader.download_file(media.music_url, filename)

        if not success or not filepath:
            await status_msg.edit_text(f"❌ Failed to download audio: {err or 'Unknown error'}")
            return

        try:
            with open(filepath, "rb") as audio_file:
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=audio_file,
                    title=media.music_title or "Original Sound",
                    performer=media.music_author or media.author_name or "TikTok",
                    caption=f"🎵 <b>{html.escape(media.music_title)}</b>\n👤 {html.escape(media.music_author or media.author_name)}",
                    parse_mode="HTML",
                    reply_to_message_id=query.message.message_id
                )
            await status_msg.delete()
        except Exception as e:
            logger.error(f"Error sending audio: {e}", exc_info=True)
            await status_msg.edit_text("❌ Error sending audio to Telegram.")
        finally:
            TikTokDownloader.cleanup_file(filepath)
        return

    if data.startswith("hd:"):
        media_id = data.split(":", 1)[1]
        media = get_cached_media(media_id)
        if not media or not media.hd_video_url:
            await query.answer("❌ HD video is no longer available in cache. Please resend the link.", show_alert=True)
            return

        await query.answer("🎬 Downloading HD video...")
        status_msg = await query.message.reply_text("⏳ <i>Downloading HD version...</i>", parse_mode="HTML")

        filename = f"hd_video_{media.id}.mp4"
        success, filepath, err = await downloader.download_file(media.hd_video_url, filename)

        if not success or not filepath:
            if err and err.startswith("FILE_TOO_LARGE"):
                size_mb = err.split(":")[1]
                await status_msg.edit_text(
                    f"⚠️ HD video size is <b>{size_mb} MB</b>, exceeding Telegram's 50MB upload limit.\n"
                    f"👉 <a href=\"{media.hd_video_url}\">Click here to download HD directly in browser</a>",
                    parse_mode="HTML"
                )
            else:
                await status_msg.edit_text(f"❌ Failed to download HD video: {err or 'Unknown error'}")
            return

        try:
            with open(filepath, "rb") as video_file:
                await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=video_file,
                    caption=f"🎬 <b>HD Version</b>\n👤 {html.escape(media.author_name)}",
                    parse_mode="HTML",
                    supports_streaming=True,
                    reply_to_message_id=query.message.message_id
                )
            await status_msg.delete()
        except Exception as e:
            logger.error(f"Error sending HD video: {e}", exc_info=True)
            await status_msg.edit_text("❌ Error sending HD video.")
        finally:
            TikTokDownloader.cleanup_file(filepath)
        return

    await query.answer()
