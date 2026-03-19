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
            title="Trung tam tro giup",
            description=(
                "Day la cac lenh hien co cua Bo Beo.\n"
                "Ban co the dung de giai tri hoac phat nhac."
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Lenh co ban",
            value=(
                "`/help` - Xem cac lenh hien co cua bot.\n"
                "`/ping` - Kiem tra do tre cua bot."
            ),
            inline=False
        )

        embed.add_field(
            name="Thong tin nguoi dung",
            value="`/userinfo` - Xem thong tin co ban cua mot thanh vien.",
            inline=False
        )

        embed.add_field(
            name="Giai tri",
            value="`/roll` - Tung xuc xac ngau nhien tu 1-6.",
            inline=False
        )

        embed.add_field(
            name="Am nhac",
            value=(
                "`/play` - Phat nhac tu ten bai hat hoac link.\n"
                "`/queue` - Xem bai dang phat va hang cho.\n"
                "`/pause` - Tam dung.\n"
                "`/resume` - Tiep tuc bai hat.\n"
                "`/skip` - Bo qua bai hat dang phat.\n"
                "`/stop` - Dung nhac, roi khoi voice."
            ),
            inline=False
        )

        embed.add_field(
            name="Quan tri bot",
            value="`/sync` - Dong bo lai slash command trong server.",
            inline=False
        )

        embed.set_footer(
            text=f"Yeu cau boi {interaction.user}",
            icon_url=interaction.user.display_avatar.url
        )

        if self.bot.user and self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            embed.set_author(
                name=self.bot.user.name,
                icon_url=self.bot.user.display_avatar.url
            )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCommand(bot))
