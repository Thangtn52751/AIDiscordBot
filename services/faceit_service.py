import httpx
import os


class FaceitService:
    BASE_URL = "https://open.faceit.com/data/v4"

    @staticmethod
    async def get_player(steam_id: str):
        headers = {
            "Authorization": f"Bearer {os.getenv('FACEIT_API_KEY')}"
        }

        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{FaceitService.BASE_URL}/players",
                params={"game": "cs2", "game_player_id": steam_id},
                headers=headers,
            )

        if res.status_code != 200:
            return None

        return res.json()

    @staticmethod
    def parse_faceit(data: dict):
        if not data:
            return {"level": "N/A", "elo": "N/A"}

        cs2 = data.get("games", {}).get("cs2", {})

        return {
            "level": cs2.get("skill_level", "N/A"),
            "elo": cs2.get("faceit_elo", "N/A"),
        }