import unittest
from unittest.mock import AsyncMock, patch

from services.cs2_stats_service import CS2StatsService


class CS2StatsServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_extract_steam_id_accepts_direct_steamid64(self) -> None:
        steam_id = "76561198000000000"

        self.assertEqual(await CS2StatsService.extract_steam_id(steam_id), steam_id)

    async def test_extract_steam_id_accepts_profiles_url(self) -> None:
        steam_id = "76561198000000000"

        self.assertEqual(
            await CS2StatsService.extract_steam_id(
                f"https://steamcommunity.com/profiles/{steam_id}/"
            ),
            steam_id,
        )

    async def test_extract_steam_id_resolves_vanity_url(self) -> None:
        steam_id = "76561198000000000"

        with patch(
            "services.cs2_stats_service.SteamService.resolve_vanity_url",
            new=AsyncMock(return_value=steam_id),
        ) as resolve_mock:
            self.assertEqual(
                await CS2StatsService.extract_steam_id("https://steamcommunity.com/id/gaben"),
                steam_id,
            )

        resolve_mock.assert_awaited_once_with("gaben")

    async def test_extract_steam_id_rejects_invalid_input(self) -> None:
        with self.assertRaises(ValueError):
            await CS2StatsService.extract_steam_id("https://example.com/not-steam")

    async def test_get_stats_includes_extra_faceit_metrics(self) -> None:
        faceit_player = {
            "player_id": "faceit-player-id",
            "nickname": "faceit-nick",
            "country": "jp",
            "games": {
                "cs2": {
                    "skill_level": 6,
                    "faceit_elo": 1238,
                }
            },
        }
        faceit_stats = {
            "lifetime": {
                "Matches": "321",
                "Win Rate %": "54",
                "Average K/D Ratio": "1.18",
                "Average Headshots %": "47",
                "ADR": "82.4",
                "KAST %": "71",
            }
        }
        steam_player = {
            "personaname": "Im NTT",
            "avatarfull": "https://example.com/avatar.png",
            "profileurl": "https://steamcommunity.com/profiles/76561198000000000",
        }

        with patch(
            "services.cs2_stats_service.FaceitService.get_player",
            new=AsyncMock(return_value=faceit_player),
        ), patch(
            "services.cs2_stats_service.FaceitService.get_player_stats",
            new=AsyncMock(return_value=faceit_stats),
        ), patch(
            "services.cs2_stats_service.SteamService.get_player",
            new=AsyncMock(return_value=steam_player),
        ):
            stats = await CS2StatsService.get_stats("76561198000000000")

        self.assertEqual(stats["faceit_level"], 6)
        self.assertEqual(stats["faceit_elo"], 1238)
        self.assertEqual(stats["matches"], "321")
        self.assertEqual(stats["winrate"], "54")
        self.assertEqual(stats["kd"], "1.18")
        self.assertEqual(stats["hs"], "47")
        self.assertEqual(stats["adr"], "82.4")
        self.assertEqual(stats["kast"], "71")
        self.assertEqual(stats["faceit_name"], "faceit-nick")


if __name__ == "__main__":
    unittest.main()
