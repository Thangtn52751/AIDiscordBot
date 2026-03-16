import json
from pathlib import Path
from typing import Any


USER_PROFILES_PATH = Path("data/user_profiles.json")


def load_user_profiles() -> dict[str, dict[str, str]]:
    if not USER_PROFILES_PATH.exists():
        return {}

    try:
        with USER_PROFILES_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}

    if not isinstance(data, dict):
        return {}

    profiles: dict[str, dict[str, str]] = {}
    for user_id, profile in data.items():
        if isinstance(profile, dict):
            profiles[str(user_id)] = {
                key: str(value)
                for key, value in profile.items()
                if isinstance(key, str) and value is not None
            }
    return profiles


def build_user_context(
    author: Any,
    user_profiles: dict[str, dict[str, str]] | None = None
) -> dict[str, str]:
    profile = {}
    if user_profiles:
        profile = user_profiles.get(str(author.id), {})

    return {
        "user_id": str(author.id),
        "username": author.name,
        "display_name": getattr(author, "display_name", author.name),
        "mention": author.mention,
        "roast_nickname": profile.get("nickname", ""),
        "roast_profile": profile.get("roast_profile", ""),
        "extra_instructions": profile.get("extra_instructions", "")
    }
