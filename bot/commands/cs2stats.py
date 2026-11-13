import discord
from discord import app_commands
from discord.ext import commands

from services.cs2_stats_service import CS2StatsService
from services.faceit_service import FaceitService


class CS2StatsCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="faceitstats",
        description="Xem stats Faceit CS2",
    )
    async def cs2stats(self, interaction: discord.Interaction, steam_url: str):
        await self._safe_defer(interaction)

        try:
            steam_id = await CS2StatsService.extract_steam_id(steam_url)
            stats = await CS2StatsService.get_stats(steam_id)

            color = self._get_level_color(stats["faceit_level"])

            embed = discord.Embed(
                title=f"🎮 {stats['name']}",
                url=stats["profile"],
                description=(
                    f"🆔 `{steam_id}` • 🌍 {stats['region']}\n"
                    f"🔗 [Faceit Profile]({stats['profile']})"
                ),
                color=color,
            )

            if stats["avatar"]:
                embed.set_thumbnail(url=stats["avatar"])

            embed.add_field(
                name="🏆 FACEIT",
                value=(
                    f"Level: **{stats['faceit_level']}**\n"
                    f"ELO: **{stats['faceit_elo']}**\n"
                    f"Nick: `{stats['faceit_name']}`"
                ),
                inline=False,
            )

            embed.add_field(
                name="📊 MATCH",
                value=(
                    f"Matches: `{stats['matches']}`\n"
                    f"Winrate: `{self._format_percent(stats['winrate'])}`"
                ),
                inline=True,
            )

            embed.add_field(
                name="💥 COMBAT",
                value=(
                    f"K/D: `{stats['kd']}`\n"
                    f"HS: `{self._format_percent(stats['hs'])}`"
                ),
                inline=True,
            )

            embed.add_field(
                name="⚙️ ADVANCED",
                value=(
                    f"ADR: `{stats.get('adr', 'N/A')}`\n"
                    f"KAST: `{self._format_percent(stats.get('kast', 'N/A'))}`"
                ),
                inline=True,
            )

            embed.set_footer(
                text="⚡ CS2 Tracker • Powered by BOBEODSBOT"
            )
            embed.timestamp = discord.utils.utcnow()

            await self._send_message(interaction, embed=embed)

        except Exception as error:
            await self._send_message(
                interaction,
                f"❌ Lỗi: {error}",
                ephemeral=True,
            )


    @app_commands.command(
        name="cs2history",
        description="Xem 5 trận gần nhất",
    )
    async def cs2history(self, interaction: discord.Interaction, steam_url: str):
        await self._safe_defer(interaction)

        try:
            steam_id = await CS2StatsService.extract_steam_id(steam_url)
            player = await FaceitService.get_player(steam_id)

            if not player:
                return await self._send_message(
                    interaction,
                    "❌ Không thấy player",
                    ephemeral=True,
                )

            history = await FaceitService.get_match_history(player["player_id"])
            items = (history or {}).get("items", [])

            if not items:
                return await self._send_message(
                    interaction,
                    "⚠️ Không có lịch sử",
                    ephemeral=True,
                )

            embed = discord.Embed(
                title="📜 Match History (5 trận gần nhất)",
                color=discord.Color.blurple(),
            )

            for match in items:
                finished = match.get("finished_at", "N/A")
                winner = match.get("results", {}).get("winner")
                teams = match.get("teams", {})
                status = "N/A"

                try:
                    for team_name, team_data in teams.items():
                        for member in team_data.get("players", []):
                            if member.get("player_id") != player["player_id"]:
                                continue
                            status = "W" if team_name == winner else "L"
                            break
                except Exception:
                    status = "N/A"

                result_icon = "🟢 WIN" if status == "W" else "🔴 LOSE"

                embed.add_field(
                    name=f"🎮 {match.get('game_mode', 'CS2')}",
                    value=(
                        f"📅 {finished}\n"
                        f"Result: **{result_icon}**"
                    ),
                    inline=True,
                )

            embed.set_footer(text="⚡ Faceit History")
            embed.timestamp = discord.utils.utcnow()

            await self._send_message(interaction, embed=embed)

        except Exception as error:
            await self._send_message(
                interaction,
                f"❌ Lỗi: {error}",
                ephemeral=True,
            )

    @staticmethod
    def _format_percent(value: str) -> str:
        if value == "N/A":
            return value
        return value if str(value).endswith("%") else f"{value}%"


    @staticmethod
    def _get_level_color(level):
        if level == "N/A":
            return discord.Color.dark_gray()

        try:
            level = int(level)
        except Exception:
            return discord.Color.dark_gray()

        if level >= 10:
            return discord.Color.red()
        if level >= 7:
            return discord.Color.orange()
        if level >= 4:
            return discord.Color.gold()
        return discord.Color.green()

    async def _send_message(
        self,
        interaction: discord.Interaction,
        content: str | None = None,
        *,
        embed: discord.Embed | None = None,
        ephemeral: bool = False,
    ):
        if interaction.response.is_done():
            await interaction.followup.send(
                content=content,
                embed=embed,
                ephemeral=ephemeral,
            )
            return

        try:
            await interaction.response.send_message(
                content=content,
                embed=embed,
                ephemeral=ephemeral,
            )
        except discord.HTTPException as error:
            if getattr(error, "code", None) not in {40060, 10062}:
                raise

            await interaction.followup.send(
                content=content,
                embed=embed,
                ephemeral=ephemeral,
            )

    async def _safe_defer(self, interaction: discord.Interaction):
        if interaction.response.is_done():
            return

        try:
            await interaction.response.defer(thinking=True)
        except discord.HTTPException as error:
            if getattr(error, "code", None) not in {40060, 10062}:
                raise


async def setup(bot):
    await bot.add_cog(CS2StatsCommand(bot))
