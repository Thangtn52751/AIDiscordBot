import base64
import os
from pathlib import Path
import tempfile

from dotenv import load_dotenv

load_dotenv()

from bot.bot import bot


def configure_runtime_cookiefile() -> None:
    if os.getenv("YTDLP_COOKIEFILE"):
        return

    cookie_base64 = os.getenv("YTDLP_COOKIE_BASE64")
    if not cookie_base64:
        return

    cookie_bytes = base64.b64decode(cookie_base64)
    cookie_dir = Path(tempfile.gettempdir()) / "bobeo-runtime"
    cookie_dir.mkdir(parents=True, exist_ok=True)
    cookie_path = cookie_dir / "cookies.txt"
    cookie_path.write_bytes(cookie_bytes)
    os.environ["YTDLP_COOKIEFILE"] = str(cookie_path)


configure_runtime_cookiefile()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set")

bot.run(TOKEN)
