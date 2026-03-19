import discord
from discord import app_commands
from discord.ext import commands


class UserInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="userinfo",
        description="Xem thông tin của 1 thành viên."
    )
    @app_commands.describe(member="Thành viên bạn muốn xem thông tin")
    async def userinfo(
        self,
        interaction: discord.Interaction,
        member: discord.Member | None = None
    ) -> None:
        await interaction.response.defer()

        member = member or interaction.user

        joined_at = (
            member.joined_at.strftime("%d/%m/%Y %H:%M")
            if member.joined_at else "Không rõ"
        )
        created_at = member.created_at.strftime("%d/%m/%Y %H:%M")

        roles = [role.mention for role in member.roles if role.name != "@everyone"]
        roles_text = self._format_roles(roles)

        embed = discord.Embed(
            title="Thông tin user",
            description=f"**{member.mention}**",
            color=discord.Color.blurple()
        )

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Username", value=str(member), inline=True)
        embed.add_field(name="User ID", value=str(member.id), inline=True)
        embed.add_field(name="Tạo TK", value=created_at, inline=False)
        embed.add_field(name="Tham gia server", value=joined_at, inline=False)
        embed.add_field(name="Role cao nhất", value=member.top_role.mention, inline=True)
        embed.add_field(name="Số lượng role", value=str(len(roles)), inline=True)
        embed.add_field(name="Danh sách role", value=roles_text, inline=False)

        embed.set_footer(
            text=f"Yêu cầu bởi {interaction.user}",
            icon_url=interaction.user.display_avatar.url
        )
        embed.set_author(
            name=str(member),
            icon_url=member.display_avatar.url
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
        suffix = f" ... và {hidden_count} role khác" if hidden_count > 0 else ""
        return ", ".join(visible_roles) + suffix


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UserInfo(bot))
