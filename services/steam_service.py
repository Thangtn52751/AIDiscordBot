import httpx
import os


class SteamService:
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