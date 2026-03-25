import discord
from discord import app_commands
from discord.ext import commands


class UserInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="userinfo",
        description="Xem thông tin của một thành viên.",
    )
    @app_commands.describe(member="Thành viên bạn muốn xem thông tin")
    async def userinfo(
        self,
        interaction: discord.Interaction,
        member: discord.Member | None = None,
    ) -> None:
        await interaction.response.defer()

        member = member or interaction.user

        # 🧠 Format time đẹp hơn
        created_at = discord.utils.format_dt(member.created_at, style="F")
        joined_at = (
            discord.utils.format_dt(member.joined_at, style="F")
            if member.joined_at else "Không rõ"
        )

        # 🎭 Badge đơn giản
        badges = []
        if member.bot:
            badges.append("🤖 Bot")
        else:
            badges.append("👤 Thành viên")

        if member.guild_permissions.administrator:
            badges.append("🛡️ Admin")

        badge_text = " • ".join(badges)

        # 🎨 Color theo role cao nhất
        color = member.top_role.color if member.top_role.color.value != 0 else discord.Color.blurple()

        # 🎭 Roles
        roles = [role.mention for role in member.roles if role.name != "@everyone"]
        roles_text = self._format_roles(roles)

        embed = discord.Embed(
            title=f"👤 {member.display_name}",
            description=f"{member.mention}\n{badge_text}",
            color=color,
        )

        # 🖼️ Avatar + banner
        embed.set_thumbnail(url=member.display_avatar.url)

        try:
            user = await self.bot.fetch_user(member.id)
            if user.banner:
                embed.set_image(url=user.banner.url)
        except:
            pass

        # 📊 Thông tin chính
        embed.add_field(
            name="📌 Thông tin cơ bản",
            value=(
                f"**Username:** {member}\n"
                f"**User ID:** `{member.id}`"
            ),
            inline=True,
        )

        embed.add_field(
            name="📅 Thời gian",
            value=(
                f"**Tạo tài khoản:**\n{created_at}\n\n"
                f"**Tham gia server:**\n{joined_at}"
            ),
            inline=True,
        )

        # 🎭 Role
        embed.add_field(
            name=f"🎭 Roles ({len(roles)})",
            value=roles_text,
            inline=False,
        )

        # 🏆 Role cao nhất
        embed.add_field(
            name="🏆 Role cao nhất",
            value=member.top_role.mention,
            inline=True,
        )

        embed.set_footer(
            text=f"Yêu cầu bởi {interaction.user}",
            icon_url=interaction.user.display_avatar.url,
        )

        await interaction.followup.send(embed=embed)

    @staticmethod
    def _format_roles(roles: list[str]) -> str:
        if not roles:
            return "Không có role"

        joined = ", ".join(roles)
        if len(joined) <= 1024:
            return joined

        visible_roles: list[str] = []
        current_length = 0

        for role in roles:
            extra_length = len(role) if not visible_roles else len(role) + 2
            if current_length + extra_length > 1000:
                break
            visible_roles.append(role)
            current_length += extra_length

        hidden_count = len(roles) - len(visible_roles)
        suffix = f"\n... và {hidden_count} role khác"
        return ", ".join(visible_roles) + suffix


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UserInfo(bot))