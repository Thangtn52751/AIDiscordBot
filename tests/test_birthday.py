from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bot.birthday import (
    BirthdayStore,
    format_birthday,
    get_birthday_timezone,
    is_valid_birthday,
    load_birthday_store,
    save_birthday_store,
)
from zoneinfo import ZoneInfoNotFoundError


class BirthdayTests(unittest.TestCase):
    def test_is_valid_birthday_accepts_leap_day(self) -> None:
        self.assertTrue(is_valid_birthday(29, 2))

    def test_is_valid_birthday_rejects_invalid_day(self) -> None:
        self.assertFalse(is_valid_birthday(31, 4))

    def test_format_birthday_uses_two_digits(self) -> None:
        self.assertEqual(format_birthday(5, 3), "05/03")

    @patch("bot.birthday.ZoneInfo", side_effect=ZoneInfoNotFoundError("missing tz"))
    def test_get_birthday_timezone_falls_back_to_fixed_offset(self, _mock_zone_info) -> None:
        timezone = get_birthday_timezone()

        self.assertEqual(timezone.tzname(None), "Asia/Bangkok")
        self.assertEqual(timezone.utcoffset(None).total_seconds(), 7 * 60 * 60)

    def test_due_birthdays_skip_current_year_after_sent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = BirthdayStore(Path(temp_dir) / "birthdays.json")
            store.set_announcement_channel(123, 456)
            store.set_birthday(789, 25, 3)

            notices = store.due_birthdays(date(2026, 3, 25))
            self.assertEqual(len(notices), 1)
            self.assertEqual(notices[0].channel_id, 456)
            self.assertEqual(notices[0].user_id, "789")

            store.mark_announced(123, 789, 2026)
            self.assertEqual(store.due_birthdays(date(2026, 3, 25)), [])

    def test_remove_birthday_clears_global_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = BirthdayStore(Path(temp_dir) / "birthdays.json")
            store.set_birthday(789, 25, 3)

            self.assertTrue(store.remove_birthday(789))
            self.assertIsNone(store.get_birthday(789))

    def test_set_birthday_is_shared_across_guilds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = BirthdayStore(Path(temp_dir) / "birthdays.json")
            store.set_announcement_channel(123, 456)
            store.set_announcement_channel(999, 888)
            store.set_birthday(789, 25, 3)

            notices = store.due_birthdays(date(2026, 3, 25))

            self.assertEqual(len(notices), 2)
            self.assertEqual({notice.guild_id for notice in notices}, {"123", "999"})

    def test_legacy_store_is_migrated_to_global_users(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "birthdays.json"
            legacy_data = {
                "guilds": {
                    "123": {
                        "announcement_channel_id": 456,
                        "birthdays": {
                            "789": {
                                "day": 25,
                                "month": 3,
                                "last_announced_year": 2026,
                            }
                        },
                    }
                }
            }
            save_birthday_store(legacy_data, path)

            migrated_data = load_birthday_store(path)

            self.assertEqual(migrated_data["users"]["789"]["day"], 25)
            self.assertEqual(migrated_data["guilds"]["123"]["announcement_channel_id"], 456)
            self.assertEqual(migrated_data["guilds"]["123"]["announced_years"]["789"], 2026)


if __name__ == "__main__":
    unittest.main()
