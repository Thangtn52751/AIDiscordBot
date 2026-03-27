import unittest

import discord

from bot.commands.cs2stats import CS2StatsCommand


class CS2StatsCommandTests(unittest.TestCase):
    def test_build_csstats_context_prefers_fallback_name_and_faceit_rank(self) -> None:
        stats = {
            "name": "Steam Player",
            "faceit_name": "N/A",
            "faceit_level": 7,
            "faceit_elo": 1543,
            "leetify": {
                "name": "N/A",
                "profile_url": "https://leetify.com/app/profile/76561198000000001",
                "premier_rank": "N/A",
                "faceit_rank": "N/A",
                "status": "not_registered",
                "status_message": "Tai khoan nay chua dang ky Leetify hoac profile khong ton tai.",
                "has_stats": False,
            },
        }

        context = CS2StatsCommand._build_csstats_context(
            "76561198000000001",
            stats,
        )

        self.assertEqual(context["player_name"], "Steam Player")
        self.assertFalse(context["has_leetify_stats"])
        self.assertIn("Unavailable (Leetify not registered)", context["rank_value"])
        self.assertIn("Level 7 (1543 ELO)", context["rank_value"])
        self.assertEqual(context["footer"], "⚡ Leetify unavailable • showing Steam fallback")
        self.assertEqual(context["color"], discord.Color.orange())

    def test_build_csstats_context_prefers_leetify_data_when_available(self) -> None:
        stats = {
            "name": "Steam Player",
            "faceit_name": "Faceit Nick",
            "faceit_level": 9,
            "faceit_elo": 1900,
            "leetify": {
                "name": "Leetify Player",
                "profile_url": "https://leetify.com/app/profile/76561198000000002",
                "premier_rank": "16234",
                "faceit_rank": "8",
                "status": "ok",
                "status_message": "Da lay du lieu tu Leetify API.",
                "has_stats": True,
            },
        }

        context = CS2StatsCommand._build_csstats_context(
            "76561198000000002",
            stats,
        )

        self.assertEqual(context["player_name"], "Leetify Player")
        self.assertTrue(context["has_leetify_stats"])
        self.assertIn("`16234`", context["rank_value"])
        self.assertIn("`8`", context["rank_value"])
        self.assertEqual(context["footer"], "⚡ Data from Leetify")
        self.assertEqual(context["color"], discord.Color.blurple())


if __name__ == "__main__":
    unittest.main()
