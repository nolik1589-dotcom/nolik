import html
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command."""
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

    await update.message.reply_html(welcome_text, reply_markup=keyboard)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /help command."""
    help_text = (
        "📖 <b>Инструкция по использованию:</b>\n\n"
        "1️⃣ Откройте <b>TikTok</b> или <b>Instagram</b>.\n"
        "2️⃣ Нажмите кнопку <b>Поделиться (Share)</b> на видео или посте.\n"
        "3️⃣ Нажмите <b>Копировать ссылку (Copy Link)</b>.\n"
        "4️⃣ Вставьте ссылку в этот чат и отправьте.\n\n"
        "🔗 <b>Поддерживаемые ссылки:</b>\n"
        "• <b>TikTok:</b> <code>tiktok.com/@...</code>, <code>vm.tiktok.com/...</code>, <code>vt.tiktok.com/...</code>\n"
        "• <b>Instagram:</b> Reels (<code>instagram.com/reel/...</code>), Посты (<code>instagram.com/p/...</code>), IGTV\n\n"
        "👥 <b>Работа в группах:</b>\n"
        "Добавьте бота в любую группу, и он будет автоматически скачивать видео по отправленным ссылкам!"
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            help_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="btn_start")]])
        )
    else:
        await update.message.reply_html(help_text)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /about command."""
    about_text = (
        "🤖 <b>О боте Media Downloader</b>\n\n"
        "• <b>Платформы:</b> TikTok & Instagram\n"
        "• <b>Качество:</b> HD MP4 без водяных знаков\n"
        "• <b>Аудио:</b> Извлечение MP3 трека (TikTok)\n"
        "• <b>Карусели:</b> Поддержка альбомов из нескольких медиа\n"
        "• <b>Лимиты:</b> До 50 МБ прямой загрузкой в Telegram\n\n"
        "⚡ Быстро, удобно и бесплатно."
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            about_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="btn_start")]])
        )
    else:
        await update.message.reply_html(about_text)
