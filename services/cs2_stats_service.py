import re
from services.faceit_service import FaceitService
from services.steam_service import SteamService


class CS2StatsService:

    @staticmethod
    def extract_steam_id(steam_url: str) -> str:
        import re
        match = re.search(r"(7656119\d{10})", steam_url)
        if match:
            return match.group(1)
        raise ValueError("Link Steam không hợp lệ")

    @staticmethod
    async def get_stats(steam_id: str):
        from services.faceit_service import FaceitService
        from services.steam_service import SteamService

        faceit_data = await FaceitService.get_player(steam_id)
        steam_data = await SteamService.get_player(steam_id)

        faceit = FaceitService.parse_faceit(faceit_data)

        return {
            "name": steam_data.get("personaname") if steam_data else "Unknown",
            "avatar": steam_data.get("avatarfull") if steam_data else None,
            "profile": steam_data.get("profileurl") if steam_data else None,

            "faceit_level": faceit["level"],
            "faceit_elo": faceit["elo"],

            "region": faceit_data.get("country") if faceit_data else "N/A",
            "matches": faceit_data.get("games", {}).get("cs2", {}).get("games", "N/A") if faceit_data else "N/A",
            "winrate": faceit_data.get("games", {}).get("cs2", {}).get("winrate", "N/A") if faceit_data else "N/A",
        }