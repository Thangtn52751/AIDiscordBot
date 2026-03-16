import random
from discord.ext import commands


class Roll(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def roll(self, ctx):

        dice = random.randint(1, 6)

        await ctx.send(f"🎲 Bạn tung được: **{dice}**")


async def setup(bot):
    await bot.add_cog(Roll(bot))