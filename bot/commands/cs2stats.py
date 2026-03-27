import traceback
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

            leetify = stats.get("leetify")
            if leetify and (
                leetify.get("has_stats")
                or leetify.get("status") not in {None, "ok", "unavailable"}
            ):
                embed.add_field(
                    name="🧠 LEETIFY",
                    value=(
                        f"Rating: **{leetify.get('leetify_rating', 'N/A')}**\n"
                        f"🎯 Aim: `{leetify.get('aim', 'N/A')}`\n"
                        f"📍 Positioning: `{leetify.get('positioning', 'N/A')}`\n"
                        f"💣 Utility: `{leetify.get('utility', 'N/A')}`\n"
                        f"🚀 Premier: `{leetify.get('premier_rank', 'N/A')}`\n"
                        f"🏅 Faceit Rank: `{leetify.get('faceit_rank', 'N/A')}`\n"
                        f"📌 Status: `{leetify.get('status_message', 'N/A')}`"
                    ),
                    inline=False,
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
        name="csstats",
        description="Xem thông số từ Leetify",
    )
    async def csstats(self, interaction: discord.Interaction, steam_url: str):
        await self._safe_defer(interaction)

        try:
            steam_id = await CS2StatsService.extract_steam_id(steam_url)
            stats = await CS2StatsService.get_stats(steam_id)
            csstats_context = self._build_csstats_context(steam_id, stats)
            leetify = csstats_context["leetify"]

            embed = discord.Embed(
                title=f"🧠 Player stats | {csstats_context['player_name']}",
                url=leetify["profile_url"],
                description=(
                    f"🆔 `{steam_id}`\n"
                    f"🔗 [Leetify Profile]({leetify['profile_url']})"
                ),
                color=csstats_context["color"],
            )

            if stats.get("avatar"):
                embed.set_thumbnail(url=stats["avatar"])

            if csstats_context["has_leetify_stats"]:
                embed.add_field(
                    name="📊 PERFORMANCE",
                    value=(
                        f"Rating: **{leetify.get('leetify_rating', 'N/A')}**\n"
                        f"🎯 Aim: `{leetify.get('aim', 'N/A')}`\n"
                        f"📍 Positioning: `{leetify.get('positioning', 'N/A')}`\n"
                        f"💣 Utility: `{leetify.get('utility', 'N/A')}`\n"
                        f"🚪 Entry: `{leetify.get('entrying', 'N/A')}`"
                    ),
                    inline=False,
                )
            else:
                embed.add_field(
                    name="ℹ️ LEETIFY STATUS",
                    value=csstats_context["status_message"],
                    inline=False,
                )

            embed.add_field(
                name="🏆 RANK",
                value=csstats_context["rank_value"],
                inline=False,
            )
            steam_fallback = stats.get("steam_game_stats")
            if steam_fallback and not leetify.get("has_stats"):
                embed.add_field(
                    name="⚠️ STEAM FALLBACK",
                    value=(
                        f"Kills: `{steam_fallback.get('kills', 'N/A')}`\n"
                        f"Deaths: `{steam_fallback.get('deaths', 'N/A')}`\n"
                        f"K/D: `{steam_fallback.get('kd', 'N/A')}`\n"
                        f"HS: `{self._format_percent(steam_fallback.get('hs_percent', 'N/A'))}`\n"
                        f"Wins: `{steam_fallback.get('wins', 'N/A')}`\n"
                        f"MVPs: `{steam_fallback.get('mvps', 'N/A')}`\n"
                        f"Hours: `{steam_fallback.get('hours_played', 'N/A')}`"
                    ),
                    inline=False,
                )

            embed.set_footer(text=csstats_context["footer"])
            embed.timestamp = discord.utils.utcnow()

            await self._send_message(interaction, embed=embed)

        except Exception as error:
            traceback.print_exc()
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
            items = history.get("items", [])

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
    def _pick_display_value(*values, default: str = "N/A") -> str:
        for value in values:
            if value is None:
                continue

            text = str(value).strip()
            if text and text not in {"N/A", "Unknown"}:
                return text

        return default

    @classmethod
    def _build_faceit_rank_fallback(cls, stats: dict) -> str:
        level = cls._pick_display_value(stats.get("faceit_level"))
        if level == "N/A":
            return "N/A"

        elo = cls._pick_display_value(stats.get("faceit_elo"))
        if elo == "N/A":
            return f"Level {level}"

        return f"Level {level} ({elo} ELO)"

    @classmethod
    def _build_premier_rank_display(cls, leetify: dict) -> str:
        premier_rank = cls._pick_display_value(leetify.get("premier_rank"))
        if premier_rank != "N/A":
            return premier_rank

        status = str(leetify.get("status", "")).strip().lower()
        if status == "not_registered":
            return "Unavailable (Leetify not registered)"
        if status == "private":
            return "Unavailable (Leetify private)"
        if status == "login_required":
            return "Unavailable (Leetify login required)"
        if status == "rate_limited":
            return "Unavailable (Leetify rate limited)"

        return "Unavailable"

    @classmethod
    def _build_csstats_context(cls, steam_id: str, stats: dict) -> dict:
        raw_leetify = stats.get("leetify") or {}
        leetify = {
            "name": raw_leetify.get("name", "N/A"),
            "profile_url": raw_leetify.get("profile_url")
            or f"https://leetify.com/app/profile/{steam_id}",
            "leetify_rating": raw_leetify.get("leetify_rating", "N/A"),
            "aim": raw_leetify.get("aim", "N/A"),
            "positioning": raw_leetify.get("positioning", "N/A"),
            "utility": raw_leetify.get("utility", "N/A"),
            "entrying": raw_leetify.get("entrying", "N/A"),
            "premier_rank": raw_leetify.get("premier_rank", "N/A"),
            "faceit_rank": raw_leetify.get("faceit_rank", "N/A"),
            "status_message": raw_leetify.get("status_message")
            or "Không lấy được dữ liệu từ Leetify.",
            "status": raw_leetify.get("status", "unavailable"),
            "has_stats": bool(raw_leetify.get("has_stats")),
        }

        has_leetify_stats = leetify["has_stats"]
        player_name = cls._pick_display_value(
            leetify.get("name"),
            stats.get("name"),
            stats.get("faceit_name"),
            steam_id,
            default="Unknown",
        )
        premier_rank = cls._build_premier_rank_display(leetify)
        faceit_rank = cls._pick_display_value(
            leetify.get("faceit_rank"),
            cls._build_faceit_rank_fallback(stats),
        )

        return {
            "leetify": leetify,
            "player_name": player_name,
            "has_leetify_stats": has_leetify_stats,
            "status_message": leetify["status_message"],
            "rank_value": (
                f"🚀 Premier: `{premier_rank}`\n"
                f"🏅 Faceit: `{faceit_rank}`\n"
            ),
            "color": (
                discord.Color.blurple()
                if has_leetify_stats
                else discord.Color.orange()
            ),
            "footer": (
                "⚡ Data from Leetify"
                if has_leetify_stats
                else "⚡ Leetify unavailable • showing Steam fallback"
            ),
        }

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
