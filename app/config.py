import os

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

PORT = int(os.getenv("PORT", "10000"))
STORAGE_DIR = os.getenv("STORAGE_DIR", "/app/storage")
DB_PATH = os.getenv("DB_PATH", os.path.join(STORAGE_DIR, "db.json"))

# Safety limits (best-effort; Render disk is limited)
MAX_DOWNLOAD_MB = int(os.getenv("MAX_DOWNLOAD_MB", "4096"))  # 4GB default

OWNER_ONLY = os.getenv("OWNER_ONLY", "0") == "1"
OWNER_ID = int(os.getenv("OWNER_ID", "0"))  # if OWNER_ONLY=1

