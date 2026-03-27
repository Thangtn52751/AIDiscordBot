import httpx
import os


class SteamService:
    CS2_APP_ID = 730

    @staticmethod
    async def resolve_vanity_url(vanity_url: str) -> str | None:
        key = os.getenv("STEAM_API_KEY")

        if not key:
            return None

        url = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/"

        async with httpx.AsyncClient() as client:
            res = await client.get(
                url,
                params={
                    "key": key,
                    "vanityurl": vanity_url,
                },
            )

        if res.status_code != 200:
            return None

        response = res.json().get("response", {})
        if response.get("success") != 1:
            return None

        steam_id = response.get("steamid")
        return steam_id if isinstance(steam_id, str) else None

    @staticmethod
    async def get_player(steam_id: str):
        key = os.getenv("STEAM_API_KEY")

        if not key:
            return None

        url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"

        async with httpx.AsyncClient() as client:
            res = await client.get(url, params={
                "key": key,
                "steamids": steam_id
            })

        if res.status_code != 200:
            return None

        data = res.json()
        players = data.get("response", {}).get("players", [])

        return players[0] if players else None

    @staticmethod
    async def get_cs2_stats(steam_id: str):
        key = os.getenv("STEAM_API_KEY")

        if not key:
            return None

        url = "https://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v2/"

        async with httpx.AsyncClient() as client:
            res = await client.get(
                url,
                params={
                    "key": key,
                    "steamid": steam_id,
                    "appid": SteamService.CS2_APP_ID,
                },
                timeout=10,
            )

        if res.status_code != 200:
            return None

        data = res.json()
        stats = data.get("playerstats", {}).get("stats", [])
        if not stats:
            return None

        stat_map = {
            item.get("name"): item.get("value")
            for item in stats
            if item.get("name") is not None
        }

        kills = SteamService._safe_int(stat_map.get("total_kills"))
        deaths = SteamService._safe_int(stat_map.get("total_deaths"))
        headshots = SteamService._safe_int(stat_map.get("total_kills_headshot"))
        wins = SteamService._safe_int(stat_map.get("total_wins"))
        mvps = SteamService._safe_int(stat_map.get("total_mvps"))
        time_played = SteamService._safe_int(stat_map.get("total_time_played"))
        damage = SteamService._safe_int(stat_map.get("total_damage_done"))

        kd = "N/A"
        if deaths > 0:
            kd = f"{kills / deaths:.2f}"

        hs_percent = "N/A"
        if kills > 0:
            hs_percent = f"{(headshots / kills) * 100:.1f}"

        hours_played = "N/A"
        if time_played > 0:
            hours_played = f"{time_played / 3600:.1f}"

        return {
            "kills": str(kills),
            "deaths": str(deaths),
            "wins": str(wins),
            "mvps": str(mvps),
            "damage": str(damage),
            "kd": kd,
            "hs_percent": hs_percent,
            "hours_played": hours_played,
            "source": "steam_official",
        }

    @staticmethod
    def _safe_int(value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
