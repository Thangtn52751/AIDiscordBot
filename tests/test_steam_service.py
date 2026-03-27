import unittest

from services.steam_service import SteamService


class SteamServiceTests(unittest.TestCase):
    def test_get_cs2_stats_transforms_raw_stats(self) -> None:
        raw_stats = {
            "total_kills": 1000,
            "total_deaths": 800,
            "total_kills_headshot": 450,
            "total_wins": 300,
            "total_mvps": 120,
            "total_time_played": 900000,
            "total_damage_done": 150000,
        }

        kills = SteamService._safe_int(raw_stats.get("total_kills"))
        deaths = SteamService._safe_int(raw_stats.get("total_deaths"))
        headshots = SteamService._safe_int(raw_stats.get("total_kills_headshot"))

        self.assertEqual(kills, 1000)
        self.assertEqual(deaths, 800)
        self.assertEqual(headshots, 450)
        self.assertEqual(f"{kills / deaths:.2f}", "1.25")
        self.assertEqual(f"{(headshots / kills) * 100:.1f}", "45.0")


if __name__ == "__main__":
    unittest.main()
