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
            title="Trung tâm trợ giúp",
            description=(
                "Đây là các lệnh đang có của Bo Béo.\n"
                "Bạn có thể dùng giải trí hoặc nghe nhạc."
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Lệnh cơ bản",
            value=(
                "`/help` - Xem các lệnh hiện có của bot.\n"
                "`/ping` - Kiểm tra độ trễ của bot."
            ),
            inline=False
        )

        embed.add_field(
            name="Thông tin user",
            value="`/userinfo` - Xem thông tin cơ bản của 1 thành viên.",
            inline=False
        )

        embed.add_field(
            name="Giai tri",
            value="`/roll` - Tung xúc sắc 1-6.",
            inline=False
        )

        embed.add_field(
            name="Am nhac",
            value=(
                "`/play` - Phát theo tên bài hát hoặc link.\n"
                "`/queue` - Xem bài hát đang phát và hàng chờ.\n"
                "`/pause` - Tạm dừng.\n"
                "`/resume` - Tiếp tục bài hát.\n"
                "`/skip` - Bỏ qua bài hát đang phát.\n"
                "`/stop` - Dừng nhạc."
            ),
            inline=False
        )

        embed.add_field(
            name="Quản trị",
            value="`/sync` - Đồng bộ command trong server này.",
            inline=False
        )

        embed.set_footer(
            text=f"Yêu cầu bởi {interaction.user}",
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
