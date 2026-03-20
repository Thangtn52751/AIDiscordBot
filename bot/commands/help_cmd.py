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
            title="📖 Trung tâm trợ giúp - Bo Béo",
            description=(
                "✨ **Danh sách lệnh hiện có của bot**\n"
                "Sử dụng bot để giải trí 🎮 hoặc nghe nhạc 🎵\n\n"
                "👉 Dùng `/` để xem nhanh tất cả lệnh"
            ),
            color=discord.Color.from_rgb(88, 101, 242)  # màu Discord đẹp hơn blurple mặc định
        )

        # ===== LỆNH CƠ BẢN =====
        embed.add_field(
            name="⚙️ Lệnh cơ bản",
            value=(
                "• `/help` → Xem danh sách lệnh\n"
                "• `/ping` → Kiểm tra độ trễ bot"
            ),
            inline=False
        )

        # ===== USER =====
        embed.add_field(
            name="👤 Thông tin người dùng",
            value="• `/userinfo` → Xem thông tin thành viên",
            inline=False
        )

        # ===== GIẢI TRÍ =====
        embed.add_field(
            name="🎲 Giải trí",
            value="• `/roll` → Tung xúc sắc (1-6)",
            inline=False
        )

        # ===== ÂM NHẠC =====
        embed.add_field(
            name="🎵 Âm nhạc",
            value=(
                "• `/play` → Phát nhạc từ tên/link\n"
                "• `/queue` → Xem hàng chờ\n"
                "• `/pause` → Tạm dừng\n"
                "• `/resume` → Tiếp tục\n"
                "• `/skip` → Bỏ qua\n"
                "• `/stop` → Dừng nhạc"
            ),
            inline=False
        )

        # ===== ADMIN =====
        embed.add_field(
            name="🛠️ Quản trị",
            value="• `/sync` → Đồng bộ lệnh trong server",
            inline=False
        )

        # ===== FOOTER =====
        embed.set_footer(
            text=f"Requested by {interaction.user}",
            icon_url=interaction.user.display_avatar.url
        )

        # ===== AVATAR BOT =====
        if self.bot.user:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            embed.set_author(
                name=f"{self.bot.user.name}",
                icon_url=self.bot.user.display_avatar.url
            )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCommand(bot))