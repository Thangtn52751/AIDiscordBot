import discord
from discord import app_commands
from discord.ext import commands


class HelpCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="Xem danh sach cac lenh"
    )
    async def help_command(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="Trung tam tro giup - Bo Beo",
            description=(
                "Danh sach lenh hien co cua bot.\n"
                "Dung / de xem nhanh tat ca lenh."
            ),
            color=discord.Color.from_rgb(88, 101, 242)
        )

        embed.add_field(
            name="Lenh co ban",
            value=(
                "- /help: Xem danh sach lenh\n"
                "- /ping: Kiem tra do tre bot"
            ),
            inline=False
        )

        embed.add_field(
            name="Thong tin nguoi dung",
            value="- /userinfo: Xem thong tin thanh vien",
            inline=False
        )

        embed.add_field(
            name="Giai tri",
            value="- /roll: Tung xuc xac (1-6)",
            inline=False
        )

        embed.add_field(
            name="Quan tri",
            value="- /sync: Dong bo lenh trong server",
            inline=False
        )

        embed.set_footer(
            text=f"Requested by {interaction.user}",
            icon_url=interaction.user.display_avatar.url
        )

        if self.bot.user:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            embed.set_author(
                name=f"{self.bot.user.name}",
                icon_url=self.bot.user.display_avatar.url
            )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCommand(bot))
