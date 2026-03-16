import random

import discord
from discord import app_commands
from discord.ext import commands


class Roll(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="roll",
        description="Tung xuc xac ngau nhien tu 1 den 6."
    )
    async def roll(self, interaction: discord.Interaction) -> None:
        dice = random.randint(1, 6)
        await interaction.response.send_message(f"Ban tung duoc: **{dice}**")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Roll(bot))
