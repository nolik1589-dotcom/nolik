import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

# Limits and configuration
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "60"))
RATE_LIMIT_SECONDS = int(os.getenv("RATE_LIMIT_SECONDS", "3"))

# Storage paths
BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = BASE_DIR / os.getenv("DOWNLOAD_DIR", "downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# API Endpoints
TIKWM_API_URL = "https://tikwm.com/api/"

def validate_config():
    """Verify that required settings are configured."""
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print(
            "\n[!] ERROR: TELEGRAM_BOT_TOKEN is not set in the .env file!\n"
            "Please create a bot via @BotFather on Telegram, copy the token,\n"
            "and set TELEGRAM_BOT_TOKEN in your .env file.\n",
            file=sys.stderr
        )
        return False
    return True
