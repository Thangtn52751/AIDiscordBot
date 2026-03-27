import httpx
import os


class SteamService:
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
