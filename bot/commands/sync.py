import discord
from discord import app_commands
from discord.ext import commands


class Sync(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="sync",
        description="Dong bo lai slash command trong server."
    )
    @app_commands.default_permissions(administrator=True)
    async def sync(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await self._send_message(
                interaction,
                "Lenh nay chi duoc dung trong server.",
                ephemeral=True,
            )
            return

        await self._safe_defer(interaction)
        guild = discord.Object(id=interaction.guild.id)
        self.bot.tree.copy_global_to(guild=guild)
        synced = await self.bot.tree.sync(guild=guild)

        await self._send_message(
            interaction,
            f"Da dong bo {len(synced)} slash command cho server nay.",
            ephemeral=True,
        )

    async def _send_message(
        self,
        interaction: discord.Interaction,
        content: str,
        *,
        ephemeral: bool = False,
    ) -> None:
        if interaction.response.is_done():
            await interaction.followup.send(content, ephemeral=ephemeral)
            return

        try:
            await interaction.response.send_message(content, ephemeral=ephemeral)
        except discord.HTTPException as error:
            error_code = getattr(error, "code", None)
            if error_code not in {40060, 10062}:
                raise
            await interaction.followup.send(content, ephemeral=ephemeral)

    async def _safe_defer(self, interaction: discord.Interaction) -> None:
        if interaction.response.is_done():
            return

        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
        except discord.HTTPException as error:
            error_code = getattr(error, "code", None)
            if error_code not in {40060, 10062}:
                raise


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Sync(bot))
