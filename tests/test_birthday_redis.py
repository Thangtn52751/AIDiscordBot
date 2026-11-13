import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from bot.birthday import BirthdayStore
from redis.exceptions import WatchError


class BirthdayRedisTests(unittest.TestCase):
    def test_vercel_requires_durable_storage(self):
        with patch.dict(os.environ, {'BOT_HOST': 'vercel'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'REDIS_URL'):
                BirthdayStore()

    def test_existing_redis_data_wins_and_updates_merge_latest_snapshot(self):
        data = {'users': {'1': {'day': 2, 'month': 3}}, 'guilds': {}}
        client = MagicMock()
        client.get.side_effect = lambda key: json.dumps(data)
        transaction = client.pipeline.return_value.__enter__.return_value
        transaction.get.side_effect = lambda key: json.dumps(data)
        def write(key, value):
            data.clear()
            data.update(json.loads(value))
        transaction.set.side_effect = write
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'REDIS_URL': 'redis://test'}, clear=True), patch('redis.Redis.from_url', return_value=client):
            path = Path(tmp) / 'birthdays.json'
            first, second = BirthdayStore(path), BirthdayStore(path)
            first.set_birthday(2, 4, 5)
            second.set_birthday(3, 6, 7)
            self.assertEqual(set(data['users']), {'1', '2', '3'})
            self.assertFalse(path.exists())
            self.assertTrue(client.set.call_args.kwargs['nx'])
            transaction.execute.side_effect = [WatchError(), None]
            second.set_announcement_channel(10, 20)
            self.assertEqual(second.get_announcement_channel_id(10), 20)

    def test_missing_redis_document_does_not_silently_reset(self):
        with self.assertRaises(RuntimeError):
            BirthdayStore._decode_redis(None)
