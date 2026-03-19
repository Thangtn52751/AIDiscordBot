import os
from dotenv import load_dotenv

load_dotenv()

from bot.bot import bot

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set")

cookiefile = os.getenv("YTDLP_COOKIEFILE")
if cookiefile:
    print(f"[COOKIE] Using YTDLP_COOKIEFILE={cookiefile}")
else:
    print("[COOKIE] YTDLP_COOKIEFILE is not set")

print("Bot is starting...")

bot.run(TOKEN)
