from pathlib import Path


BOT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BOT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
COMMANDS_DIR = BOT_DIR / "commands"
PERSONALITY_PATH = BOT_DIR / "personality.txt"
USER_PROFILES_PATH = DATA_DIR / "user_profiles.json"
BIRTHDAYS_PATH = DATA_DIR / "birthdays.json"
