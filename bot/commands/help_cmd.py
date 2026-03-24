import discord
from discord import app_commands
from discord.ext import commands


class HelpCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="Xem danh sách các lệnh"
    )
    async def help_command(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="Trung tâm lệnh của Bo Béo",
            description=(
                "Danh sách các lệnh của bot.\n"
                "Dùng / trỏ vào Bo Béo để xem tất cả các lệnh."
            ),
            color=discord.Color.from_rgb(88, 101, 242)
        )

        embed.add_field(
            name="Lệnh cơ bản",
            value=(
                "- /help: Xem danh sách các lệnh (Bạn vừa dùng xong)\n"
                "- /ping: Kiểm tra độ trễ của bot\n"
                "- /countdown: Đếm ngược sự kiên"
            ),
            inline=False
        )

        embed.add_field(
            name="Thông tin người dùng",
            value="- /userinfo: Xem thông tin người dùng",
            inline=False
        )

        embed.add_field(
            name="Giải trí",
            value="- /roll: Tung xúc sắc (1-6)",
            inline=False
        )

        embed.add_field(
            name="Quản trị",
            value="- /sync: Đồng bộ lại lệnh trong server",
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
