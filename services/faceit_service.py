import os
import time

import httpx

CACHE_TTL = 60
_cache = {}


def _cache_get(key):
    data = _cache.get(key)
    if not data:
        return None
    value, expire = data
    if time.time() > expire:
        _cache.pop(key, None)
        return None
    return value


def _cache_set(key, value):
    _cache[key] = (value, time.time() + CACHE_TTL)


class FaceitService:
    BASE_URL = "https://open.faceit.com/data/v4"

    @staticmethod
    def _default_faceit_stats() -> dict[str, str | None]:
        return {
            "player_id": None,
            "level": "N/A",
            "elo": "N/A",
            "nickname": "N/A",
            "matches": "N/A",
            "winrate": "N/A",
            "kd": "N/A",
            "hs": "N/A",
            "adr": "N/A",
            "kast": "N/A",
        }

    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "Authorization": f"Bearer {os.getenv('FACEIT_API_KEY')}"
        }

    @staticmethod
    async def _request(url: str, params=None):
        cache_key = f"{url}:{params}"

        cached = _cache_get(cache_key)
        if cached:
            return cached

        async with httpx.AsyncClient() as client:
            res = await client.get(
                url,
                params=params,
                headers=FaceitService._headers(),
                timeout=10,
            )

        if res.status_code != 200:
            return None

        data = res.json()
        _cache_set(cache_key, data)
        return data

    @staticmethod
    async def get_player(steam_id: str):
        return await FaceitService._request(
            f"{FaceitService.BASE_URL}/players",
            params={"game": "cs2", "game_player_id": steam_id},
        )

    @staticmethod
    async def get_player_stats(player_id: str):
        return await FaceitService._request(
            f"{FaceitService.BASE_URL}/players/{player_id}/stats/cs2"
        )

    @staticmethod
    async def get_match_history(player_id: str):
        return await FaceitService._request(
            f"{FaceitService.BASE_URL}/players/{player_id}/history",
            params={"game": "cs2", "limit": 5},
        )

    @staticmethod
    def _pick_lifetime_value(lifetime: dict, *keys, default="N/A"):
        for key in keys:
            value = lifetime.get(key)
            if value not in (None, ""):
                return str(value)
        return default

    @staticmethod
    def parse_faceit(data, stats_data=None):
        if not data:
            return FaceitService._default_faceit_stats()

        cs2 = data.get("games", {}).get("cs2", {})
        lifetime = stats_data.get("lifetime", {}) if stats_data else {}

        return {
            **FaceitService._default_faceit_stats(),
            "player_id": data.get("player_id"),
            "level": cs2.get("skill_level", "N/A"),
            "elo": cs2.get("faceit_elo", "N/A"),
            "nickname": data.get("nickname", "N/A"),
            "matches": FaceitService._pick_lifetime_value(lifetime, "Matches"),
            "winrate": FaceitService._pick_lifetime_value(lifetime, "Win Rate %"),
            "kd": FaceitService._pick_lifetime_value(
                lifetime,
                "Average K/D Ratio",
                "K/D Ratio",
            ),
            "hs": FaceitService._pick_lifetime_value(
                lifetime,
                "Average Headshots %",
                "Headshots %",
            ),
            "adr": FaceitService._pick_lifetime_value(lifetime, "ADR"),
            "kast": FaceitService._pick_lifetime_value(lifetime, "KAST %"),
        }
