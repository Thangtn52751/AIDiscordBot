import asyncio
import os
import traceback

import discord
from ai.llm_client import ask_ai
from ai.llm_client import ask_ai_with_image
from bot.paths import COMMANDS_DIR, PERSONALITY_PATH, PROJECT_ROOT
from bot.user_context import build_message_context, load_user_profiles
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

intents = discord.Intents.default()
intents.message_content = True


class BoBeoCommandTree(app_commands.CommandTree):
    async def on_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        await self.client.on_app_command_error(interaction, error)


class BoBeoBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix="!",
            intents=intents,
            tree_cls=BoBeoCommandTree,
        )
        self.personality = PERSONALITY_PATH.read_text(encoding="utf-8")
        self.user_profiles = load_user_profiles()
        self.guild_id = os.getenv("DISCORD_GUILD_ID")

    async def setup_hook(self) -> None:
        await load_commands(self)

        synced = await self.tree.sync()
        print(f"Synced {len(synced)} global slash commands: {[cmd.name for cmd in synced]}")

        if self.guild_id:
            guild = discord.Object(id=int(self.guild_id))
            try:
                self.tree.copy_global_to(guild=guild)
                guild_synced = await self.tree.sync(guild=guild)
                print(
                    f"Synced {len(guild_synced)} guild slash commands to {self.guild_id}: "
                    f"{[cmd.name for cmd in guild_synced]}"
                )
            except discord.Forbidden:
                print(
                    "Missing access while syncing guild slash commands. "
                    f"Check DISCORD_GUILD_ID={self.guild_id}, confirm the bot is in that server, "
                    "and re-invite it with bot + applications.commands scopes."
                )

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        command_name = interaction.command.qualified_name if interaction.command else "unknown"
        print(f"Slash command error in /{command_name}: {error}")
        traceback.print_exception(type(error), error, error.__traceback__)

        if self._should_suppress_interaction_error(interaction, error):
            print(
                "Slash error notification suppressed because the interaction "
                "was already acknowledged elsewhere."
            )
            return

        message = "Đang tính."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except discord.DiscordException as notify_error:
            error_code = getattr(notify_error, "code", None)
            if error_code in {10062, 40060}:
                print(
                    "Slash error response skipped because interaction is no longer valid "
                    f"(code={error_code})."
                )
                return
            print(f"Failed to send slash error response: {notify_error}")

    @staticmethod
    def _extract_error_code(error: BaseException) -> int | None:
        current_error: BaseException | None = error

        while current_error is not None:
            error_code = getattr(current_error, "code", None)
            if isinstance(error_code, int):
                return error_code
            current_error = getattr(current_error, "original", None) or getattr(
                current_error,
                "__cause__",
                None,
            )

        return None

    def _should_suppress_interaction_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> bool:
        error_code = self._extract_error_code(error)
        if error_code in {40060, 10062}:
            return True

        interaction_type = getattr(interaction, "type", None)
        return interaction_type == discord.InteractionType.autocomplete

    def get_invite_url(self) -> str | None:
        client_id = self.application_id or (self.user.id if self.user else None)
        if not client_id:
            return None

        permissions = discord.Permissions(
            view_channel=True,
            send_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            mention_everyone=True,
        )
        return discord.utils.oauth_url(
            client_id,
            permissions=permissions,
            scopes=("bot", "applications.commands"),
        )


bot = BoBeoBot()


@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user} (pid={os.getpid()})")
    invite_url = bot.get_invite_url()
    if invite_url:
        print(f"Invite URL: {invite_url}")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if bot.user in message.mentions:
        content = message.content.replace(f"<@{bot.user.id}>", "").strip()
        user_context = build_message_context(
            message.author,
            list(message.mentions),
            bot.user,
            bot.user_profiles,
        )

        try:
            async with message.channel.typing():
                if message.attachments:
                    image_url = message.attachments[0].url

                    response = await asyncio.to_thread(
                        ask_ai_with_image,
                        bot.personality,
                        content,
                        image_url,
                        user_context,
                    )
                else:
                    response = await asyncio.to_thread(
                        ask_ai,
                        bot.personality,
                        content,
                        user_context,
                    )

            await message.channel.send(response)

        except Exception as error:
            print("ERROR:", error)
            await message.channel.send("AI error occurred.")

    await bot.process_commands(message)


async def load_commands(bot):
    for command_file in COMMANDS_DIR.glob("*.py"):
        if command_file.name != "__init__.py":
            await bot.load_extension(f"bot.commands.{command_file.stem}")
