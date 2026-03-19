import os
from dotenv import load_dotenv
load_dotenv()
from bot.bot import bot

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set")

cookiefile = os.getenv("YTDLP_COOKIEFILE")
if cookiefile:
    if os.path.isdir(cookiefile):
        print(f"[COOKIE] ERROR: {cookiefile} is a directory, not a file")
    elif os.path.isfile(cookiefile):
        print(f"[COOKIE] Using cookie file at {cookiefile}")
    else:
        print(f"[COOKIE] WARNING: cookie file does not exist yet: {cookiefile}")
else:
    print("[COOKIE] YTDLP_COOKIEFILE is not set")

print("Bot is starting...")
bot.run(TOKEN)
