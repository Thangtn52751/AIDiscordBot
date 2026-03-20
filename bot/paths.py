from pathlib import Path


BOT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BOT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
COMMANDS_DIR = BOT_DIR / "commands"
PERSONALITY_PATH = DATA_DIR / "personality.txt"
USER_PROFILES_PATH = DATA_DIR / "user_profiles.json"
DEFAULT_COOKIE_PATH = DATA_DIR / "cookies.txt"


def resolve_cookiefile_path(configured_path: str | None) -> Path | None:
    if configured_path:
        configured = Path(configured_path).expanduser()
        if configured.is_file():
            return configured

        if not configured.is_absolute():
            repo_relative = (PROJECT_ROOT / configured).resolve()
            if repo_relative.is_file():
                return repo_relative

        if DEFAULT_COOKIE_PATH.is_file():
            return DEFAULT_COOKIE_PATH

        return None

    if DEFAULT_COOKIE_PATH.is_file():
        return DEFAULT_COOKIE_PATH

    return None
