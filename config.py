import os
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://kaila-unappareled-yair.ngrok-free.dev")
KASPI_NUMBER = os.getenv("KASPI_NUMBER", "+77051234567")