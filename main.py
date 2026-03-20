import os

from bot.paths import PROJECT_ROOT, resolve_cookiefile_path
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")
from bot.bot import bot

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set")

configured_cookiefile = os.getenv("YTDLP_COOKIEFILE")
resolved_cookiefile = resolve_cookiefile_path(configured_cookiefile)
if configured_cookiefile:
    if os.path.isdir(configured_cookiefile):
        print(f"[COOKIE] ERROR: {configured_cookiefile} is a directory, not a file")
    elif resolved_cookiefile is not None:
        if str(resolved_cookiefile) == configured_cookiefile:
            print(f"[COOKIE] Using cookie file at {resolved_cookiefile}")
        else:
            print(
                f"[COOKIE] WARNING: configured cookie file not found: {configured_cookiefile}. "
                f"Using fallback at {resolved_cookiefile}"
            )
    else:
        print(f"[COOKIE] WARNING: cookie file does not exist yet: {configured_cookiefile}")
elif resolved_cookiefile is not None:
    print(f"[COOKIE] Using default cookie file at {resolved_cookiefile}")
else:
    print("[COOKIE] YTDLP_COOKIEFILE is not set")

print("Bot is starting...")
bot.run(TOKEN)
