import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from bot.commands.cs2stats import CS2StatsCommand


class CS2StatsCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_faceit_only_commands_registered(self):
        cog = CS2StatsCommand(MagicMock())
        self.assertEqual({cmd.name for cmd in cog.get_app_commands()}, {'faceitstats', 'cs2history'})

    async def test_history_unavailable_is_handled(self):
        cog = CS2StatsCommand(MagicMock())
        cog._safe_defer = AsyncMock()
        cog._send_message = AsyncMock()
        with patch('bot.commands.cs2stats.FaceitService.get_player', new=AsyncMock(return_value={'player_id': 'abc'})), patch('bot.commands.cs2stats.FaceitService.get_match_history', new=AsyncMock(return_value=None)):
            await cog.cs2history.callback(cog, MagicMock(), '76561198000000000')
        self.assertIn('Không có lịch sử', cog._send_message.call_args.args[1])
