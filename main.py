import atexit
import ctypes
import os
import sys
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
        raise OSError("Không tạo được mutex Windows để khóa một instance bot.")

    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(mutex_handle)
        print("Bot đang chạy ở một tiến trình khác. Hãy tắt instance cũ trước khi mở mới.")
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
    raise RuntimeError("Thiếu biến môi trường DISCORD_TOKEN")


def main() -> None:
    if os.getenv(CHILD_GUARD_ENV) == "1":
        print("Phát hiện tiến trình bot bị khởi động lặp. Đang thoát tiến trình con.")
        sys.exit(0)

    os.environ[CHILD_GUARD_ENV] = "1"
    acquire_single_instance_lock()
    atexit.register(release_single_instance_lock)
    print("Bot đang khởi động...")
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
