from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone, tzinfo
import json
import os
from pathlib import Path
from typing import Any, Callable, TypeVar
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from bot.paths import BIRTHDAYS_PATH


DEFAULT_BIRTHDAY_TIMEZONE = "Asia/Bangkok"
DEFAULT_BIRTHDAY_UTC_OFFSET = timezone(timedelta(hours=7), name=DEFAULT_BIRTHDAY_TIMEZONE)
DEFAULT_REDIS_KEY = "aidiscordbot:birthdays:v1"
T = TypeVar("T")


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

    raw_guilds = raw_data.get("guilds", {})
    if "users" in raw_data or any(
        isinstance(entry, dict) and "announced_years" in entry
        for entry in (raw_guilds.values() if isinstance(raw_guilds, dict) else ())
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
    """JSON locally, or a durable Redis document with optimistic transactions.

    Redis is seeded only if the key does not exist. Every update re-reads the
    latest document under WATCH, so simultaneous bot processes cannot overwrite
    unrelated users, channels, or announcement marks with an old snapshot.
    """

    def __init__(self, path: Path = BIRTHDAYS_PATH) -> None:
        self.path = path
        self._redis = None
        self._redis_key = os.getenv("BIRTHDAY_REDIS_KEY", DEFAULT_REDIS_KEY)
        redis_url = os.getenv("REDIS_URL", "").strip()
        hosted = os.getenv("BOT_HOST", "").lower() == "vercel" or bool(
            os.getenv("VERCEL_DEPLOYMENT_ID")
        )
        if not redis_url and hosted:
            raise RuntimeError(
                "Cần REDIS_URL để lưu sinh nhật trên Vercel; ổ đĩa daemon không lưu dữ liệu lâu dài."
            )

        if redis_url:
            from redis import Redis
            from redis.backoff import NoBackoff
            from redis.retry import Retry

            self._redis = Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
                retry=Retry(NoBackoff(), 0),
                retry_on_timeout=False,
            )
            # SET NX makes first-boot migration safe even during overlapping
            # deployments. An existing (even empty) database always wins.
            self._redis.set(
                self._redis_key,
                json.dumps(load_birthday_store(path), ensure_ascii=True),
                nx=True,
            )
            self.data = self._decode_redis(self._redis.get(self._redis_key))
            print("[birthday] lưu trữ bền vững: Redis")
        else:
            self.data = load_birthday_store(path)
            print(f"[birthday] lưu trữ JSON local: {self.path.resolve()}")

    def save(self) -> None:
        if self._redis is not None:
            raise RuntimeError("Dùng các phương thức cập nhật BirthdayStore để ghi Redis nguyên tử.")
        save_birthday_store(self.data, self.path)

    @staticmethod
    def _decode_redis(raw: str | bytes | None) -> dict[str, dict[str, Any]]:
        if raw is None:
            # Do not silently reseed a key that disappeared at runtime: that
            # could resurrect deleted birthdays from an old deployment image.
            raise RuntimeError("Không tìm thấy dữ liệu sinh nhật trong Redis.")
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise RuntimeError("Dữ liệu sinh nhật trong Redis không hợp lệ.") from error
        if not isinstance(data, dict) or not isinstance(data.get("users"), dict) or not isinstance(data.get("guilds"), dict):
            raise RuntimeError("Cấu trúc dữ liệu sinh nhật trong Redis không hợp lệ.")
        return _normalize_birthday_store(data)

    def _refresh(self) -> None:
        if self._redis is not None:
            self.data = self._decode_redis(self._redis.get(self._redis_key))

    def _update(self, change: Callable[[dict[str, dict[str, Any]]], T]) -> T:
        if self._redis is None:
            result = change(self.data)
            self.save()
            return result

        from redis.exceptions import WatchError

        for _attempt in range(5):
            try:
                with self._redis.pipeline() as transaction:
                    transaction.watch(self._redis_key)
                    data = self._decode_redis(transaction.get(self._redis_key))
                    result = change(data)
                    transaction.multi()
                    transaction.set(self._redis_key, json.dumps(data, ensure_ascii=True))
                    transaction.execute()
                self.data = data
                return result
            except WatchError:
                continue
        raise RuntimeError("Dữ liệu sinh nhật đang bận, vui lòng thử lại.")

    def _get_or_create_user(self, user_id: int | str) -> dict[str, int] | None:
        users = self.data.setdefault("users", {})
        user_key = str(user_id)
        birthday = users.get(user_key)
        if birthday is None:
            return None
        if isinstance(birthday, dict):
            return birthday
        return None

    @staticmethod
    def _get_or_create_guild(data: dict[str, dict[str, Any]], guild_id: int | str) -> dict[str, Any]:
        guilds = data.setdefault("guilds", {})
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

    @staticmethod
    def _clear_announcement_marks_for_user(data: dict[str, dict[str, Any]], user_id: int | str) -> None:
        user_key = str(user_id)
        guilds = data.get("guilds", {})
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

        def change(data: dict[str, dict[str, Any]]) -> bool:
            users = data.setdefault("users", {})
            user_key = str(user_id)
            previous_birthday = users.get(user_key)
            date_changed = not (
                isinstance(previous_birthday, dict)
                and previous_birthday.get("day") == day
                and previous_birthday.get("month") == month
            )
            users[user_key] = {"day": day, "month": month}
            if date_changed:
                self._clear_announcement_marks_for_user(data, user_id)
            return date_changed

        return self._update(change)

    def remove_birthday(self, user_id: int) -> bool:
        def change(data: dict[str, dict[str, Any]]) -> bool:
            removed = data.setdefault("users", {}).pop(str(user_id), None)
            if removed is None:
                return False
            self._clear_announcement_marks_for_user(data, user_id)
            return True

        return self._update(change)

    def set_announcement_channel(self, guild_id: int, channel_id: int) -> None:
        def change(data: dict[str, dict[str, Any]]) -> None:
            guild = self._get_or_create_guild(data, guild_id)
            guild["announcement_channel_id"] = int(channel_id)

        self._update(change)

    def get_announcement_channel_id(self, guild_id: int) -> int | None:
        self._refresh()
        guild = self._get_or_create_guild(self.data, guild_id)
        channel_id = guild.get("announcement_channel_id")
        return channel_id if isinstance(channel_id, int) else None

    def get_birthday(self, user_id: int) -> dict[str, int] | None:
        self._refresh()
        return self._get_or_create_user(user_id)

    def get_last_announced_year(self, guild_id: int, user_id: int) -> int | None:
        self._refresh()
        guild = self._get_or_create_guild(self.data, guild_id)
        announced_years = guild.get("announced_years")
        if not isinstance(announced_years, dict):
            return None

        year = announced_years.get(str(user_id))
        return year if isinstance(year, int) else None

    def due_birthdays(self, today: date) -> list[BirthdayNotice]:
        self._refresh()
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
        def change(data: dict[str, dict[str, Any]]) -> None:
            guild = self._get_or_create_guild(data, guild_id)
            guild["announced_years"][str(user_id)] = int(year)

        self._update(change)
