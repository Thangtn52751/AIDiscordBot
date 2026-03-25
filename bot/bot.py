import asyncio
import os
import traceback

import discord
from ai.llm_client import ask_ai, ask_ai_with_image
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

        if self.guild_id:
            guild = discord.Object(id=int(self.guild_id))
            try:
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                print(
                    f"Đã đồng bộ {len(synced)} slash command cho guild {self.guild_id}: "
                    f"{[cmd.name for cmd in synced]}"
                )
                return
            except discord.Forbidden:
                print(
                    "Thiếu quyền khi đồng bộ slash command cho guild. "
                    f"Hãy kiểm tra DISCORD_GUILD_ID={self.guild_id}, xác nhận bot đang ở trong server đó "
                    "và mời lại bot với scope `bot` + `applications.commands`."
                )

        synced = await self.tree.sync()
        print(f"Đã đồng bộ {len(synced)} global slash command: {[cmd.name for cmd in synced]}")

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        command_name = interaction.command.qualified_name if interaction.command else "unknown"
        print(f"Lỗi slash command /{command_name}: {error}")
        traceback.print_exception(type(error), error, error.__traceback__)

        if self._should_suppress_interaction_error(interaction, error):
            print("Đã bỏ qua thông báo lỗi vì interaction đã được phản hồi trước đó.")
            return

        message = "Bot đang xử lý, bạn thử lại giúp mình nhé."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except discord.DiscordException as notify_error:
            error_code = getattr(notify_error, "code", None)
            if error_code in {10062, 40060}:
                print(
                    "Bỏ qua phản hồi lỗi vì interaction không còn hợp lệ "
                    f"(code={error_code})."
                )
                return
            print(f"Không gửi được thông báo lỗi slash command: {notify_error}")

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
    print(f"Bot đã đăng nhập với tên {bot.user} (pid={os.getpid()})")
    invite_url = bot.get_invite_url()
    if invite_url:
        print(f"Link mời bot: {invite_url}")


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
            print("Lỗi AI:", error)
            await message.channel.send("Đã xảy ra lỗi khi gọi AI.")

    await bot.process_commands(message)


async def load_commands(bot):
    for command_file in COMMANDS_DIR.glob("*.py"):
        if command_file.name != "__init__.py":
            await bot.load_extension(f"bot.commands.{command_file.stem}")
