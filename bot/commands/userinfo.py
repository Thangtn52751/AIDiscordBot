import discord
from discord import app_commands
from discord.ext import commands


class UserInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="userinfo",
        description="Xem thong tin co ban cua mot thanh vien."
    )
    @app_commands.describe(member="Thanh vien ban muon xem thong tin")
    async def userinfo(
        self,
        interaction: discord.Interaction,
        member: discord.Member | None = None
    ) -> None:
        member = member or interaction.user

        embed = discord.Embed(
            title="Thong tin nguoi dung",
            color=0x3498DB
        )
        embed.add_field(name="Ten", value=member.name, inline=True)
        embed.add_field(name="ID", value=str(member.id), inline=True)

        joined_at = member.joined_at.strftime("%d/%m/%Y %H:%M") if member.joined_at else "Khong ro"
        embed.add_field(name="Ngay tham gia", value=joined_at, inline=False)

        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UserInfo(bot))
