import discord
from discord import app_commands
from discord.ext import commands

from services.cs2_stats_service import CS2StatsService


class CS2StatsCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="cs2stats",
        description="Xem stats CS2 đầy đủ (Faceit + Steam)"
    )
    async def cs2stats(self, interaction: discord.Interaction, steam_url: str):

        try:
            steam_id = CS2StatsService.extract_steam_id(steam_url)
            stats = await CS2StatsService.get_stats(steam_id)

            embed = discord.Embed(
                title=f"🎯 {stats['name']}",
                url=stats["profile"],
                description=f"SteamID: `{steam_id}`",
                color=discord.Color.orange()
            )

            if stats["avatar"]:
                embed.set_thumbnail(url=stats["avatar"])

            embed.add_field(name="🟠 Faceit Level", value=stats["faceit_level"], inline=True)
            embed.add_field(name="🔥 Faceit ELO", value=stats["faceit_elo"], inline=True)
            embed.add_field(name="🌍 Region", value=stats["region"], inline=True)

            # embed.add_field(name="🎮 Matches", value=stats["matches"], inline=True)
            # embed.add_field(name="📊 Winrate", value=f"{stats['winrate']}%", inline=True)

            # embed.add_field(
            #     name="🏆 Premier Rating",
            #     value="N/A (Valve không public API)",
            #     inline=False
            # )

            # embed.set_footer(text="Data từ Faceit API + Steam API")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi: {str(e)}")


async def setup(bot):
    await bot.add_cog(CS2StatsCommand(bot))