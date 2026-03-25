import discord
from discord import app_commands
from discord.ext import commands


class HelpCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="Xem danh sach cac lenh",
    )
    async def help_command(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="Trung tam lenh cua Bo Beo",
            description=(
                "Danh sach cac lenh hien co cua bot.\n"
                "Go `/` trong Discord de xem nhanh tung lenh."
            ),
            color=discord.Color.from_rgb(88, 101, 242),
        )

        embed.add_field(
            name="Lenh co ban",
            value=(
                "- /help: Xem danh sach cac lenh\n"
                "- /ping: Kiem tra do tre cua bot\n"
                "- /countdown: Dem nguoc su kien"
            ),
            inline=False,
        )

        embed.add_field(
            name="Thong tin nguoi dung",
            value="- /userinfo: Xem thong tin nguoi dung",
            inline=False,
        )

        embed.add_field(
            name="Sinh nhat",
            value=(
                "- /birthday set: Tu dat ngay sinh cua ban\n"
                "- /birthday info: Xem ngay sinh va kenh thong bao\n"
                "- /birthday remove: Xoa ngay sinh da luu\n"
                "- /birthday channel: Admin set kenh gui thong bao"
            ),
            inline=False,
        )

        embed.add_field(
            name="Giai tri",
            value="- /roll: Tung xuc xac (1-6)",
            inline=False,
        )

        embed.add_field(
            name="Quan tri",
            value="- /sync: Dong bo lai lenh trong server",
            inline=False,
        )

        embed.set_footer(
            text=f"Requested by {interaction.user}",
            icon_url=interaction.user.display_avatar.url,
        )

        if self.bot.user:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            embed.set_author(
                name=self.bot.user.name,
                icon_url=self.bot.user.display_avatar.url,
            )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCommand(bot))
