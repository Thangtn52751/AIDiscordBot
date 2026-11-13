import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from core.daemon import run_bot


class DaemonTests(unittest.IsolatedAsyncioTestCase):
    async def test_shutdown_closes_gateway_and_releases_lease(self):
        stop = asyncio.Event()
        async def start(token):
            stop.set()
            await asyncio.Event().wait()
        bot = MagicMock(start=AsyncMock(side_effect=start), close=AsyncMock())
        lease = MagicMock(acquire=AsyncMock(return_value=True), release=AsyncMock())
        client = MagicMock(lock=MagicMock(return_value=lease), aclose=AsyncMock())
        with patch('redis.asyncio.Redis.from_url', return_value=client):
            await run_bot(bot, 'test-token', 'redis://test', stop)
        bot.close.assert_awaited_once()
        lease.release.assert_awaited_once()
        client.aclose.assert_awaited_once()

    async def test_standby_does_not_connect_without_lease(self):
        stop = asyncio.Event()
        async def acquire(**kwargs):
            stop.set()
            return False
        bot = MagicMock(start=AsyncMock(), close=AsyncMock())
        lease = MagicMock(acquire=AsyncMock(side_effect=acquire), release=AsyncMock())
        client = MagicMock(lock=MagicMock(return_value=lease), aclose=AsyncMock())
        with patch('redis.asyncio.Redis.from_url', return_value=client):
            await run_bot(bot, 'test-token', 'redis://test', stop)
        bot.start.assert_not_awaited()
        lease.release.assert_not_awaited()

    async def test_gateway_failure_is_propagated_and_closed(self):
        bot = MagicMock(start=AsyncMock(side_effect=RuntimeError('failed')), close=AsyncMock())
        with self.assertRaisesRegex(RuntimeError, 'failed'):
            await run_bot(bot, 'test-token')
        bot.close.assert_awaited_once()

    async def test_lease_renewal_failure_stops_gateway(self):
        async def start(token):
            await asyncio.Event().wait()
        bot = MagicMock(start=AsyncMock(side_effect=start), close=AsyncMock())
        lease = MagicMock(acquire=AsyncMock(return_value=True),
                          extend=AsyncMock(side_effect=RuntimeError('lease lost')),
                          release=AsyncMock())
        client = MagicMock(lock=MagicMock(return_value=lease), aclose=AsyncMock())
        with patch('redis.asyncio.Redis.from_url', return_value=client), patch('core.daemon.asyncio.sleep', new=AsyncMock()):
            with self.assertRaisesRegex(RuntimeError, 'lease lost'):
                await run_bot(bot, 'test-token', 'redis://test')
        bot.close.assert_awaited_once()
