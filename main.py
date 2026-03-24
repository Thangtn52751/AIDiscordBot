import os
import sys
import atexit
from pathlib import Path

try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None

from bot.paths import PROJECT_ROOT
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")
from bot.bot import bot


LOCK_FILE: Path = PROJECT_ROOT / ".bot.lock"
LOCK_HANDLE = None


def acquire_single_instance_lock() -> None:
    global LOCK_HANDLE

    if msvcrt is None:
        return

    LOCK_FILE.touch(exist_ok=True)
    lock_handle = LOCK_FILE.open("r+")

    try:
        msvcrt.locking(lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        print("Bot is already running. Stop the other instance before starting a new one.")
        lock_handle.close()
        sys.exit(1)

    LOCK_HANDLE = lock_handle


def release_single_instance_lock() -> None:
    global LOCK_HANDLE

    if LOCK_HANDLE is None:
        return

    try:
        if msvcrt is not None:
            LOCK_HANDLE.seek(0)
            msvcrt.locking(LOCK_HANDLE.fileno(), msvcrt.LK_UNLCK, 1)
    except OSError:
        pass
    finally:
        LOCK_HANDLE.close()
        LOCK_HANDLE = None

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set")


def main() -> None:
    acquire_single_instance_lock()
    atexit.register(release_single_instance_lock)
    print("Bot is starting...")
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
