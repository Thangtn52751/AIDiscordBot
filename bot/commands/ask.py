import asyncio
import discord
from discord import app_commands
from discord.ext import commands

from ai.llm_client import ask_ai
from bot.user_context import build_user_context


class Ask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="ask",
        description="Hoi Bo Beo mot cau va nhan cau tra loi ca khia."
    )
    @app_commands.describe(question="Cau hoi hoac yeu cau ban muon Bo Beo tra loi")
    async def ask(self, interaction: discord.Interaction, question: str) -> None:
        await interaction.response.defer(thinking=True)

        user_context = build_user_context(
            interaction.user,
            getattr(self.bot, "user_profiles", {})
        )
        response = await asyncio.to_thread(
            ask_ai,
            getattr(self.bot, "personality", ""),
            question,
            user_context
        )

        await interaction.followup.send(response)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Ask(bot))
