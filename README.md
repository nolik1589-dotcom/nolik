# 🎬 Media Downloader Telegram Bot (TikTok & Instagram)

A fast, modern, and asynchronous Telegram bot that downloads videos without watermarks from **TikTok** and **Instagram** (Reels, Posts, Carousels, Stories), extracts audio (MP3), and downloads photo albums directly into Telegram chats.

---

## ✨ Features

- **📱 TikTok Downloader:**
  - ⚡ Watermark-free HD MP4 videos with streaming support (`supports_streaming=True`).
  - 🎵 Extract original background audio as MP3 track with title & artist tags.
  - 📸 Multi-photo slideshow & carousel album downloads.
- **📸 Instagram Downloader:**
  - 🎬 Instagram Reels download directly into Telegram.
  - 🖼️ Single photo and video post download.
  - 📚 Carousel / Album support (multiple photos & videos sent as media groups).
- **📊 Rich Captions:** Formatted with creator handle, post caption, likes, comments, and direct links.
- **🛡️ 50MB File Guard:** If any media file exceeds Telegram's 50MB bot limit, the bot provides a direct browser download button.
- **⏱️ Anti-Spam Rate Limiter:** Per-user cooldown protects the bot from spam and flooding.
- **👥 Group & Private Chat Support:** Works in direct messages and in group chats.
- **🐳 Docker Ready:** Includes `Dockerfile` and `docker-compose.yml` for instant deployment.

---

## 🚀 Quick Start Guide

### 1. Get a Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts to choose a name and username for your bot.
3. Copy the HTTP API token provided by BotFather (e.g. `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`).

### 2. Configure Environment Variables

Open `.env` and set your bot token:

```env
TELEGRAM_BOT_TOKEN=8558838917:AAHCozMN1QeSOI0K3ufXLwTA6vjjxz1NcaE
MAX_FILE_SIZE_MB=50
DOWNLOAD_TIMEOUT=60
RATE_LIMIT_SECONDS=3
DOWNLOAD_DIR=downloads
```

### 3. Run Locally

```bash
# 1. Activate the virtual environment
source venv/bin/activate

# 2. Run the bot
python bot.py
```

---

## 🐳 Running with Docker

```bash
# Build and run in background
docker compose up -d --build

# View logs
docker compose logs -f

# Stop the bot
docker compose down
```

---

## 🔗 Supported Links

- **TikTok:**
  - `https://www.tiktok.com/@username/video/7106594312292453678`
  - `https://vm.tiktok.com/ZM8abcDEF/`
  - `https://vt.tiktok.com/...`
- **Instagram:**
  - Reels: `https://www.instagram.com/reel/C5WTtLuPrkq/`
  - Posts: `https://www.instagram.com/p/C5WTtLuPrkq/`
  - Share links: `https://www.instagram.com/share/reel/...`

---

## 🧪 Running Tests

```bash
source venv/bin/activate
python -m unittest tests/test_components.py
```
