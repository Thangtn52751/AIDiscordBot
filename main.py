import os
import sys
import atexit
import ctypes
from ctypes import wintypes

from bot.paths import PROJECT_ROOT
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")
from bot.bot import bot


MUTEX_NAME = "Local\\BoBeoDSBotMain"
ERROR_ALREADY_EXISTS = 183
MUTEX_HANDLE = None
CHILD_GUARD_ENV = "BOBEO_BOT_ACTIVE"


def acquire_single_instance_lock() -> None:
    global MUTEX_HANDLE

    if os.name != "nt":
        return

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.GetLastError.restype = wintypes.DWORD

    mutex_handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not mutex_handle:
        raise OSError("Failed to create Windows mutex for bot instance lock.")

    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(mutex_handle)
        print("Bot is already running. Stop the other instance before starting a new one.")
        sys.exit(1)

    MUTEX_HANDLE = mutex_handle


def release_single_instance_lock() -> None:
    global MUTEX_HANDLE

    if MUTEX_HANDLE is None or os.name != "nt":
        return

    ctypes.windll.kernel32.CloseHandle(MUTEX_HANDLE)
    MUTEX_HANDLE = None

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set")


def main() -> None:
    if os.getenv(CHILD_GUARD_ENV) == "1":
        print("Detected duplicate bot bootstrap. Exiting child process.")
        sys.exit(0)

    os.environ[CHILD_GUARD_ENV] = "1"
    acquire_single_instance_lock()
    atexit.register(release_single_instance_lock)
    print("Bot is starting...")
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
