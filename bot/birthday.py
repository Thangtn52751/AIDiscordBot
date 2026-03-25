from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone, tzinfo
import json
import os
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from bot.paths import BIRTHDAYS_PATH


DEFAULT_BIRTHDAY_TIMEZONE = "Asia/Bangkok"
DEFAULT_BIRTHDAY_UTC_OFFSET = timezone(timedelta(hours=7), name=DEFAULT_BIRTHDAY_TIMEZONE)


@dataclass(frozen=True)
class BirthdayNotice:
    guild_id: str
    user_id: str
    channel_id: int
    day: int
    month: int


def get_birthday_timezone() -> tzinfo:
    timezone_name = os.getenv("BIRTHDAY_TIMEZONE", DEFAULT_BIRTHDAY_TIMEZONE)
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        if timezone_name == DEFAULT_BIRTHDAY_TIMEZONE:
            return DEFAULT_BIRTHDAY_UTC_OFFSET

        try:
            return ZoneInfo(DEFAULT_BIRTHDAY_TIMEZONE)
        except ZoneInfoNotFoundError:
            return DEFAULT_BIRTHDAY_UTC_OFFSET


def current_birthday_date() -> date:
    return datetime.now(get_birthday_timezone()).date()


def is_valid_birthday(day: int, month: int) -> bool:
    try:
        date(2000, month, day)
    except ValueError:
        return False
    return True


def format_birthday(day: int, month: int) -> str:
    return f"{day:02d}/{month:02d}"


def _normalize_user_birthdays(raw_birthdays: object) -> dict[str, dict[str, int]]:
    if not isinstance(raw_birthdays, dict):
        return {}

    birthdays: dict[str, dict[str, int]] = {}
    for user_id, entry in raw_birthdays.items():
        if not isinstance(entry, dict):
            continue

        try:
            day = int(entry.get("day"))
            month = int(entry.get("month"))
        except (TypeError, ValueError):
            continue

        if not is_valid_birthday(day, month):
            continue

        birthdays[str(user_id)] = {
            "day": day,
            "month": month,
        }

    return birthdays


def _normalize_announced_years(raw_announced_years: object) -> dict[str, int]:
    if not isinstance(raw_announced_years, dict):
        return {}

    announced_years: dict[str, int] = {}
    for user_id, year in raw_announced_years.items():
        try:
            announced_years[str(user_id)] = int(year)
        except (TypeError, ValueError):
            continue
    return announced_years


def _normalize_guilds(raw_guilds: object) -> dict[str, dict[str, Any]]:
    if not isinstance(raw_guilds, dict):
        return {}

    guilds: dict[str, dict[str, Any]] = {}
    for guild_id, entry in raw_guilds.items():
        if not isinstance(entry, dict):
            continue

        channel_id = entry.get("announcement_channel_id")
        if channel_id is not None:
            try:
                channel_id = int(channel_id)
            except (TypeError, ValueError):
                channel_id = None

        guilds[str(guild_id)] = {
            "announcement_channel_id": channel_id,
            "announced_years": _normalize_announced_years(entry.get("announced_years", {})),
        }

    return guilds


def _migrate_legacy_store(raw_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    guild_source = raw_data.get("guilds", raw_data)
    if not isinstance(guild_source, dict):
        return {"users": {}, "guilds": {}}

    users: dict[str, dict[str, int]] = {}
    guilds: dict[str, dict[str, Any]] = {}

    for guild_id, entry in guild_source.items():
        if not isinstance(entry, dict):
            continue

        channel_id = entry.get("announcement_channel_id")
        if channel_id is not None:
            try:
                channel_id = int(channel_id)
            except (TypeError, ValueError):
                channel_id = None

        announced_years: dict[str, int] = {}
        for user_id, birthday in _normalize_user_birthdays(entry.get("birthdays", {})).items():
            users[str(user_id)] = birthday

            last_announced_year = entry.get("birthdays", {}).get(str(user_id), {}).get("last_announced_year")
            try:
                if last_announced_year is not None:
                    announced_years[str(user_id)] = int(last_announced_year)
            except (TypeError, ValueError, AttributeError):
                continue

        guilds[str(guild_id)] = {
            "announcement_channel_id": channel_id,
            "announced_years": announced_years,
        }

    return {
        "users": users,
        "guilds": guilds,
    }


def _normalize_birthday_store(raw_data: object) -> dict[str, dict[str, Any]]:
    if not isinstance(raw_data, dict):
        return {"users": {}, "guilds": {}}

    if "users" in raw_data or any(
        isinstance(entry, dict) and "announced_years" in entry
        for entry in raw_data.get("guilds", {}).values()
        if isinstance(raw_data.get("guilds", {}), dict)
    ):
        return {
            "users": _normalize_user_birthdays(raw_data.get("users", {})),
            "guilds": _normalize_guilds(raw_data.get("guilds", {})),
        }

    return _migrate_legacy_store(raw_data)


def load_birthday_store(path: Path = BIRTHDAYS_PATH) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {"users": {}, "guilds": {}}

    try:
        with path.open("r", encoding="utf-8") as file:
            raw_data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return {"users": {}, "guilds": {}}

    return _normalize_birthday_store(raw_data)


def save_birthday_store(
    data: dict[str, dict[str, Any]],
    path: Path = BIRTHDAYS_PATH,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized_data = _normalize_birthday_store(data)
    with path.open("w", encoding="utf-8") as file:
        json.dump(normalized_data, file, ensure_ascii=True, indent=2)


class BirthdayStore:
    def __init__(self, path: Path = BIRTHDAYS_PATH) -> None:
        self.path = path
        self.data = load_birthday_store(path)
        self._log_storage_path()

    def save(self) -> None:
        save_birthday_store(self.data, self.path)

    def _log_storage_path(self) -> None:
        resolved_path = self.path.resolve()
        running_on_railway = bool(os.getenv("RAILWAY_PROJECT_ID"))
        print(
            "[birthday] đường dẫn lưu trữ: "
            f"{resolved_path} | tồn tại={self.path.exists()} | railway={running_on_railway}"
        )

    def _get_or_create_user(self, user_id: int | str) -> dict[str, int] | None:
        users = self.data.setdefault("users", {})
        user_key = str(user_id)
        birthday = users.get(user_key)
        if birthday is None:
            return None
        if isinstance(birthday, dict):
            return birthday
        return None

    def _get_or_create_guild(self, guild_id: int | str) -> dict[str, Any]:
        guilds = self.data.setdefault("guilds", {})
        guild_key = str(guild_id)
        guild = guilds.get(guild_key)
        if not isinstance(guild, dict):
            guild = {
                "announcement_channel_id": None,
                "announced_years": {},
            }
            guilds[guild_key] = guild

        announced_years = guild.get("announced_years")
        if not isinstance(announced_years, dict):
            announced_years = {}
            guild["announced_years"] = announced_years

        return guild

    def _clear_announcement_marks_for_user(self, user_id: int | str) -> None:
        user_key = str(user_id)
        guilds = self.data.get("guilds", {})
        if not isinstance(guilds, dict):
            return

        for guild in guilds.values():
            if not isinstance(guild, dict):
                continue
            announced_years = guild.get("announced_years")
            if isinstance(announced_years, dict):
                announced_years.pop(user_key, None)

    def set_birthday(self, user_id: int, day: int, month: int) -> bool:
        if not is_valid_birthday(day, month):
            raise ValueError("Ngày sinh không hợp lệ.")

        users = self.data.setdefault("users", {})
        user_key = str(user_id)
        previous_birthday = users.get(user_key)
        date_changed = not (
            isinstance(previous_birthday, dict)
            and previous_birthday.get("day") == day
            and previous_birthday.get("month") == month
        )

        users[user_key] = {
            "day": day,
            "month": month,
        }

        if date_changed:
            self._clear_announcement_marks_for_user(user_id)

        self.save()
        return date_changed

    def remove_birthday(self, user_id: int) -> bool:
        users = self.data.setdefault("users", {})
        removed = users.pop(str(user_id), None)
        if removed is None:
            return False

        self._clear_announcement_marks_for_user(user_id)
        self.save()
        return True

    def set_announcement_channel(self, guild_id: int, channel_id: int) -> None:
        guild = self._get_or_create_guild(guild_id)
        guild["announcement_channel_id"] = int(channel_id)
        self.save()

    def get_announcement_channel_id(self, guild_id: int) -> int | None:
        guild = self._get_or_create_guild(guild_id)
        channel_id = guild.get("announcement_channel_id")
        return channel_id if isinstance(channel_id, int) else None

    def get_birthday(self, user_id: int) -> dict[str, int] | None:
        return self._get_or_create_user(user_id)

    def get_last_announced_year(self, guild_id: int, user_id: int) -> int | None:
        guild = self._get_or_create_guild(guild_id)
        announced_years = guild.get("announced_years")
        if not isinstance(announced_years, dict):
            return None

        year = announced_years.get(str(user_id))
        return year if isinstance(year, int) else None

    def due_birthdays(self, today: date) -> list[BirthdayNotice]:
        notices: list[BirthdayNotice] = []
        users = self.data.get("users", {})
        guilds = self.data.get("guilds", {})
        if not isinstance(users, dict) or not isinstance(guilds, dict):
            return notices

        due_users = {
            user_id: birthday
            for user_id, birthday in users.items()
            if isinstance(birthday, dict)
            and birthday.get("day") == today.day
            and birthday.get("month") == today.month
        }
        if not due_users:
            return notices

        for guild_id, guild in guilds.items():
            if not isinstance(guild, dict):
                continue

            channel_id = guild.get("announcement_channel_id")
            if not isinstance(channel_id, int):
                continue

            announced_years = guild.get("announced_years", {})
            if not isinstance(announced_years, dict):
                announced_years = {}

            for user_id, birthday in due_users.items():
                if announced_years.get(str(user_id)) == today.year:
                    continue

                notices.append(
                    BirthdayNotice(
                        guild_id=str(guild_id),
                        user_id=str(user_id),
                        channel_id=channel_id,
                        day=int(birthday["day"]),
                        month=int(birthday["month"]),
                    )
                )

        return notices

    def mark_announced(self, guild_id: int | str, user_id: int | str, year: int) -> None:
        guild = self._get_or_create_guild(guild_id)
        announced_years = guild["announced_years"]
        announced_years[str(user_id)] = int(year)
        self.save()
