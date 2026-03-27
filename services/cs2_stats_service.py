import asyncio
import re

from services.faceit_service import FaceitService
from services.leetify_service import LeetifyService
from services.steam_service import SteamService


class CS2StatsService:
    @staticmethod
    async def extract_steam_id(steam_input: str) -> str:
        steam_input = steam_input.strip()

        direct_match = re.fullmatch(r"7656119\d{10}", steam_input)
        if direct_match:
            return steam_input

        profile_match = re.search(r"steamcommunity\.com/profiles/(7656119\d{10})/?", steam_input)
        if profile_match:
            return profile_match.group(1)

        vanity_match = re.search(r"steamcommunity\.com/id/([^/?#]+)/?", steam_input)
        if vanity_match:
            vanity_value = vanity_match.group(1)
            steam_id = await SteamService.resolve_vanity_url(vanity_value)
            if steam_id:
                return steam_id
            raise ValueError("Khong tim thay SteamID tu vanity URL nay")

        raise ValueError(
            "Link Steam khong hop le. Hay dung SteamID64 hoac link steamcommunity.com/id/... hay /profiles/..."
        )

    @staticmethod
    async def get_stats(steam_id: str):
        faceit_task = FaceitService.get_player(steam_id)
        steam_task = SteamService.get_player(steam_id)
        steam_stats_task = SteamService.get_cs2_stats(steam_id)
        leetify_task = LeetifyService.get_player_stats(steam_id)

        faceit_data, steam_data, steam_game_stats, leetify_data = await asyncio.gather(
            faceit_task,
            steam_task,
            steam_stats_task,
            leetify_task,
            return_exceptions=True,
        )

        if isinstance(faceit_data, Exception):
            faceit_data = None
        if isinstance(steam_data, Exception):
            steam_data = None
        if isinstance(steam_game_stats, Exception):
            steam_game_stats = None
        if isinstance(leetify_data, Exception):
            leetify_data = None

        faceit_stats_data = None
        if faceit_data and faceit_data.get("player_id"):
            try:
                faceit_stats_data = await FaceitService.get_player_stats(faceit_data["player_id"])
            except Exception:
                pass

        faceit = FaceitService.parse_faceit(faceit_data, faceit_stats_data)

        return {
            "name": steam_data.get("personaname") if steam_data else "Unknown",
            "avatar": steam_data.get("avatarfull") if steam_data else None,
            "profile": steam_data.get("profileurl") if steam_data else None,
            "faceit_name": faceit["nickname"],
            "faceit_level": faceit["level"],
            "faceit_elo": faceit["elo"],
            "region": faceit_data.get("country") if faceit_data else "N/A",
            "matches": faceit["matches"],
            "winrate": faceit["winrate"],
            "kd": faceit["kd"],
            "hs": faceit["hs"],
            "adr": faceit.get("adr", "N/A"),
            "kast": faceit.get("kast", "N/A"),
            "leetify": leetify_data or {},
            "steam_game_stats": steam_game_stats or {},
        }
