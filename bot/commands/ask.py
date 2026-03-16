from discord.ext import commands
from ai.llm_client import ask_ai
from bot.user_context import build_user_context, load_user_profiles


USER_PROFILES = load_user_profiles()

class Ask(commands.Cog):

    def __init__(self, bot, personality):
        self.bot = bot
        self.personality = personality

    @commands.command()
    @commands.cooldown(3, 10, commands.BucketType.user)
    async def ask(self, ctx, *, question):
        user_context = build_user_context(ctx.author, USER_PROFILES)

        response = ask_ai(self.personality, question, user_context)

        await ctx.send(response)

def setup(bot, personality):
    bot.add_cog(Ask(bot, personality))
