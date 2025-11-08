import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration for Samsariya Admin Bot
# Secrets must be provided via .env; no hardcoded defaults
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_BOT_TOKEN = os.getenv("CLIENT_BOT_TOKEN")  # Token for client bot
SHEETS_WEBHOOK_URL = os.getenv("SHEETS_WEBHOOK_URL")  # Google Apps Script Web App URL

# Parse admin IDs from environment variable
admin_ids_str = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(admin_id.strip()) for admin_id in admin_ids_str.split(",") if admin_id.strip()]

WORK_HOURS = os.getenv("WORK_HOURS", "09:00-21:00")

# MongoDB configuration
MONGODB_URI = os.getenv("MONGODB_URI") 