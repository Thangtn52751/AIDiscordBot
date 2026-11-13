import re
from urllib.parse import urlsplit

from services.faceit_service import FaceitService


class CS2StatsService:
    @staticmethod
    async def extract_steam_id(player_input: str) -> str:
        """Read the game identifier locally; never call the Steam API."""
        value = player_input.strip()
        if re.fullmatch(r'7656119\d{10}', value):
            return value
        parsed = urlsplit(value)
        if parsed.scheme in {'http', 'https'} and parsed.hostname in {'steamcommunity.com', 'www.steamcommunity.com'}:
            match = re.fullmatch(r'/profiles/(7656119\d{10})/?', parsed.path)
            if match:
                return match.group(1)
        raise ValueError('Dùng SteamID64 hoặc link steamcommunity.com/profiles/SteamID64. Link /id/... không còn hỗ trợ.')

    @staticmethod
    async def get_stats(player_id: str):
        player = await FaceitService.get_player(player_id)
        if not player or not player.get('player_id'):
            raise ValueError('Không tìm thấy người chơi FACEIT hoặc không truy cập được FACEIT API.')
        stats = await FaceitService.get_player_stats(player['player_id'])
        faceit = FaceitService.parse_faceit(player, stats)
        return {
            'name': faceit['nickname'],
            'avatar': player.get('avatar'),
            'profile': (player.get('faceit_url') or '').replace('{lang}', 'en') or None,
            'faceit_name': faceit['nickname'],
            'faceit_level': faceit['level'],
            'faceit_elo': faceit['elo'],
            'region': player.get('country', 'N/A'),
            **{key: faceit[key] for key in ('matches', 'winrate', 'kd', 'hs', 'adr', 'kast')},
        }
