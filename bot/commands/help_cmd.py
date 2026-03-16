import discord
from discord import app_commands
from discord.ext import commands


class HelpCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="Xem danh sach lenh slash hien co cua bot."
    )
    async def help_command(self, interaction: discord.Interaction) -> None:
        help_text = (
            "**Danh sach lenh hien co**\n"
            "/help - Xem danh sach lenh.\n"
            "/ping - Kiem tra do tre cua bot.\n"
            "/userinfo - Xem thong tin co ban cua thanh vien.\n"
            "/roll - Tung xuc xac ngau nhien.\n"
            "/ask - Hoi Bo Beo mot cau."
        )
        await interaction.response.send_message(help_text, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCommand(bot))
