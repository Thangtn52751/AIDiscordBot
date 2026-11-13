import unittest
from unittest.mock import AsyncMock, patch

from services.cs2_stats_service import CS2StatsService


class CS2StatsServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_game_identifier_parsed_without_network(self):
        identifier = '76561198000000000'
        self.assertEqual(await CS2StatsService.extract_steam_id(identifier), identifier)
        self.assertEqual(await CS2StatsService.extract_steam_id(f'https://steamcommunity.com/profiles/{identifier}/'), identifier)
        for value in ['https://steamcommunity.com/id/name', f'https://evil.example/steamcommunity.com/profiles/{identifier}', 'invalid']:
            with self.assertRaises(ValueError):
                await CS2StatsService.extract_steam_id(value)

    async def test_stats_come_only_from_faceit(self):
        player = {'player_id': 'abc', 'nickname': 'Player', 'avatar': 'https://example.com/avatar.png', 'faceit_url': 'https://www.faceit.com/{lang}/players/Player', 'country': 'vn', 'games': {'cs2': {'skill_level': 6, 'faceit_elo': 1200}}}
        with patch('services.cs2_stats_service.FaceitService.get_player', new=AsyncMock(return_value=player)) as lookup, patch('services.cs2_stats_service.FaceitService.get_player_stats', new=AsyncMock(return_value={'lifetime': {'Matches': '123', 'ADR': '80'}})) as stats:
            result = await CS2StatsService.get_stats('76561198000000000')
        lookup.assert_awaited_once_with('76561198000000000')
        stats.assert_awaited_once_with('abc')
        self.assertEqual(result['name'], 'Player')
        self.assertEqual(result['profile'], 'https://www.faceit.com/en/players/Player')
        self.assertEqual(result['matches'], '123')
        self.assertEqual(result['adr'], '80')
        self.assertNotIn('leetify', result)
        self.assertNotIn('steam_game_stats', result)

    async def test_missing_player_reports_error(self):
        with patch('services.cs2_stats_service.FaceitService.get_player', new=AsyncMock(return_value=None)):
            with self.assertRaises(ValueError):
                await CS2StatsService.get_stats('76561198000000000')
