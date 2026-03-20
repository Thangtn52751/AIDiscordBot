import os

from bot.paths import PROJECT_ROOT
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")
from bot.bot import bot

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set")

print("Bot is starting...")
bot.run(TOKEN)
