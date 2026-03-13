from discord.ext import commands
from ai.llm_client import ask_ai

class Ask(commands.Cog):

    def __init__(self, bot, personality):
        self.bot = bot
        self.personality = personality

    @commands.command()
    @commands.cooldown(3, 10, commands.BucketType.user)
    async def ask(self, ctx, *, question):

        response = ask_ai(self.personality, question)

        await ctx.send(response)

def setup(bot, personality):
    bot.add_cog(Ask(bot, personality))