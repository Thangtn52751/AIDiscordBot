import atexit
import ctypes
import os
import sys
import tempfile
from ctypes import wintypes
from pathlib import Path

from bot.paths import PROJECT_ROOT
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from bot.bot import bot


MUTEX_NAME = "Local\\BoBeoDSBotMain"
ERROR_ALREADY_EXISTS = 183
MUTEX_HANDLE = None
LOCK_FILE_HANDLE = None
LOCK_FILE_PATH = Path(tempfile.gettempdir()) / "bobeodsbot.lock"
CHILD_GUARD_ENV = "BOBEO_BOT_ACTIVE"


def acquire_single_instance_lock() -> None:
    global MUTEX_HANDLE, LOCK_FILE_HANDLE

    if os.name == "nt":
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.GetLastError.restype = wintypes.DWORD

        mutex_handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        if not mutex_handle:
            raise OSError("Khong tao duoc mutex Windows de khoa mot instance bot.")

        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(mutex_handle)
            print("Bot dang chay o mot tien trinh khac. Hay tat instance cu truoc khi mo moi.")
            sys.exit(1)

        MUTEX_HANDLE = mutex_handle
        return

    import fcntl

    lock_file = LOCK_FILE_PATH.open("w", encoding="utf-8")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock_file.close()
        print("Bot dang chay o mot tien trinh khac. Hay tat instance cu truoc khi mo moi.")
        sys.exit(1)

    lock_file.write(str(os.getpid()))
    lock_file.flush()
    LOCK_FILE_HANDLE = lock_file


def release_single_instance_lock() -> None:
    global MUTEX_HANDLE, LOCK_FILE_HANDLE

    if os.name == "nt":
        if MUTEX_HANDLE is None:
            return

        ctypes.windll.kernel32.CloseHandle(MUTEX_HANDLE)
        MUTEX_HANDLE = None
        return

    if LOCK_FILE_HANDLE is None:
        return

    import fcntl

    fcntl.flock(LOCK_FILE_HANDLE.fileno(), fcntl.LOCK_UN)
    LOCK_FILE_HANDLE.close()
    LOCK_FILE_HANDLE = None


TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("Thiếu biến môi trường DISCORD_TOKEN")


def main() -> None:
    if os.getenv(CHILD_GUARD_ENV) == "1":
        print("Phát hiện tiến trình bot đang bị lặp. Đang thoát...")
        sys.exit(0)

    os.environ[CHILD_GUARD_ENV] = "1"
    acquire_single_instance_lock()
    atexit.register(release_single_instance_lock)
    print(f"Bot đang khởi động... pid={os.getpid()}")
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
