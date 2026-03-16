import discord
from discord.ext import commands


class UserInfo(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def userinfo(self, ctx, member: discord.Member = None):

        member = member or ctx.author

        embed = discord.Embed(
            title="👤 Thông tin người dùng",
            color=0x3498db
        )

        embed.add_field(name="Tên", value=member.name)
        embed.add_field(name="ID", value=member.id)
        embed.add_field(name="Ngày tham gia", value=member.joined_at)

        embed.set_thumbnail(url=member.avatar)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(UserInfo(bot))