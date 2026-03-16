import discord
from discord.ext import commands
from ai.llm_client import ask_ai
import asyncio
from ai.llm_client import ask_ai_with_image
from bot.user_context import build_user_context, load_user_profiles

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

with open("data/personality.txt", "r", encoding="utf-8") as f:
    personality = f.read()
user_profiles = load_user_profiles()


@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")


@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if bot.user in message.mentions:

        content = message.content.replace(f"<@{bot.user.id}>", "").strip()
        user_context = build_user_context(message.author, user_profiles)

        try:

            async with message.channel.typing():

                # nếu user gửi ảnh
                if message.attachments:

                    image_url = message.attachments[0].url

                    response = await asyncio.to_thread(
                        ask_ai_with_image,
                        personality,
                        content,
                        image_url,
                        user_context
                    )

                else:
                    response = await asyncio.to_thread(
                        ask_ai,
                        personality,
                        content,
                        user_context
                    )

            await message.channel.send(response)

        except Exception as e:
            print("ERROR:", e)
            await message.channel.send("AI error occurred.")

    await bot.process_commands(message)
