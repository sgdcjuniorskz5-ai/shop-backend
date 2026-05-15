import os
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
# Default WebApp URL (can be overridden via .env)
# Using user-provided ngrok HTTPS URL for WebApp
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://kaila-unappareled-yair.ngrok-free.dev")