import os
from dotenv import load_dotenv
from bot.bot import bot

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

bot.run(TOKEN)