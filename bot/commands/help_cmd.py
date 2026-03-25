import discord
from discord import app_commands
from discord.ext import commands


class HelpCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="Xem danh sách các lệnh",
    )
    async def help_command(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="📚 Trung Tâm Lệnh - Béo Bot",
            description=(
                "✨ **Danh sách tất cả lệnh của bot**\n"
                "👉 Gõ `/` để xem nhanh từng lệnh trong Discord\n\n"
                "━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.blurple(),
        )

        embed.add_field(
            name="⚙️ Lệnh cơ bản",
            value=(
                "```yaml\n"
                "/help        : Xem danh sách lệnh\n"
                "/ping        : Kiểm tra độ trễ\n"
                "/countdown   : Đếm ngược sự kiện\n"
                "```"
            ),
            inline=False,
        )

        embed.add_field(
            name="👤 Thông tin người dùng",
            value=(
                "```yaml\n"
                "/userinfo    : Xem thông tin người dùng\n"
                "```"
            ),
            inline=False,
        )

        embed.add_field(
            name="🎂 Sinh nhật",
            value=(
                "```yaml\n"
                "/birthday           : Đặt ngày sinh\n"
                "/birthday_info      : Xem thông tin\n"
                "/birthday_remove    : Xóa ngày sinh\n"
                "/birthday_channel   : Đặt kênh thông báo\n"
                "```"
            ),
            inline=False,
        )

        embed.add_field(
            name="🎮 Giải trí",
            value=(
                "```yaml\n"
                "/roll        : Tung xúc xắc\n"
                "```"
            ),
            inline=False,
        )

        embed.add_field(
            name="🛠️ Quản trị",
            value=(
                "```yaml\n"
                "/sync        : Đồng bộ lệnh\n"
                "```"
            ),
            inline=False,
        )

        embed.add_field(
            name="💡 Mẹo",
            value="Dùng `/` + tên lệnh để Discord tự hiện hướng dẫn chi tiết.",
            inline=False,
        )

        embed.set_footer(
            text=f"Yêu cầu bởi {interaction.user}",
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
