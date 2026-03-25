from __future__ import annotations

import asyncio
from datetime import date

import discord
from bot.birthday import BirthdayNotice, BirthdayStore, current_birthday_date, format_birthday, is_valid_birthday
from discord import app_commands
from discord.ext import commands, tasks


class Birthday(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.store = BirthdayStore()
        self.store_lock = asyncio.Lock()
        self.birthday_checker.start()

    def cog_unload(self) -> None:
        self.birthday_checker.cancel()

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            await self._send_message(
                interaction,
                "Bạn cần quyền `Manage Server` để dùng lệnh này.",
                ephemeral=True,
            )
            return

        raise error

    @app_commands.command(name="birthday", description="Đặt ngày sinh của bạn.")
    @app_commands.describe(
        day="Ngày sinh của bạn",
        month="Tháng sinh của bạn",
    )
    async def birthday_set(
        self,
        interaction: discord.Interaction,
        day: app_commands.Range[int, 1, 31],
        month: app_commands.Range[int, 1, 12],
    ) -> None:
        if interaction.guild is None:
            await self._send_message(
                interaction,
                "Lệnh này chỉ có trong server.",
                ephemeral=True,
            )
            return

        if not is_valid_birthday(day, month):
            await self._send_message(
                interaction,
                "Ngày sinh không hợp lệ. VD: 25/03, 29/02.",
                ephemeral=True,
            )
            return

        await self._safe_defer(interaction, ephemeral=True)

        today = current_birthday_date()
        announced_immediately = False

        async with self.store_lock:
            previous_birthday = self.store.get_birthday(interaction.user.id)
            previous_last_announced_year = self.store.get_last_announced_year(
                interaction.guild.id,
                interaction.user.id,
            )
            self.store.set_birthday(interaction.user.id, day, month)
            channel_id = self.store.get_announcement_channel_id(interaction.guild.id)

        should_announce_now = (
            channel_id is not None
            and day == today.day
            and month == today.month
            and not (
                previous_birthday is not None
                and previous_birthday.get("day") == day
                and previous_birthday.get("month") == month
                and previous_last_announced_year == today.year
            )
        )

        if should_announce_now:
            notice = BirthdayNotice(
                guild_id=str(interaction.guild.id),
                user_id=str(interaction.user.id),
                channel_id=channel_id,
                day=day,
                month=month,
            )
            announced_immediately = await self._send_birthday_announcement(notice, today)
            if announced_immediately:
                async with self.store_lock:
                    birthday = self.store.get_birthday(interaction.user.id)
                    if birthday is not None and birthday.get("day") == day and birthday.get("month") == month:
                        self.store.mark_announced(interaction.guild.id, interaction.user.id, today.year)

        if channel_id is None:
            channel_text = (
                "Chưa có kênh thông báo. Admin hãy dùng `/birthday_channel` để set kênh."
            )
        else:
            channel_text = f"<#{channel_id}>"

        extra_message = ""
        if day == today.day and month == today.month:
            if channel_id is None:
                extra_message = "\nHôm nay là ngày sinh nhật của bạn nhưng Admin chưa set thông báo."
            elif announced_immediately:
                extra_message = "\nMình đã gửi thông báo sinh nhật."
            else:
                extra_message = "\nHôm nay kaf sinh nhật của bạn nhưng mình chưa gửi được vào kênh đã set."

        await self._send_message(
            interaction,
            (
                f"Đã lưu SN của bạn: **{format_birthday(day, month)}**.\n"
                f"Kênh thông báo hiện tại: {channel_text}"
                f"{extra_message}"
            ),
            ephemeral=True,
        )

    @app_commands.command(name="birthday_info", description="Xem ngày sinh của bạn.")
    async def birthday_info(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await self._send_message(
                interaction,
                "Lệnh này chỉ được dùng trong SV.",
                ephemeral=True,
            )
            return

        await self._safe_defer(interaction, ephemeral=True)

        async with self.store_lock:
            birthday = self.store.get_birthday(interaction.user.id)
            channel_id = self.store.get_announcement_channel_id(interaction.guild.id)

        birthday_text = (
            format_birthday(int(birthday["day"]), int(birthday["month"]))
            if birthday else
            "Chưa đặt"
        )
        channel_text = f"<#{channel_id}>" if channel_id else "Chua dat"

        embed = discord.Embed(
            title="Thông tin sinh nhật",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Ngày sinh nhật của bạn", value=birthday_text, inline=True)
        embed.add_field(name="Kênh thông báo", value=channel_text, inline=True)
        embed.add_field(name="Bộ nhớ", value="Ngày sinh được lưu theo user.", inline=False)
        embed.set_footer(
            text=f"Yêu cầu bởi {interaction.user}",
            icon_url=interaction.user.display_avatar.url,
        )

        await self._send_message(interaction, embed=embed, ephemeral=True)

    @app_commands.command(name="birthday_remove", description="Xóa ngày sinh nhật đã lưu của bạn.")
    async def birthday_remove(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await self._send_message(
                interaction,
                "Lệnh này chỉ được dùng trong SV.",
                ephemeral=True,
            )
            return

        await self._safe_defer(interaction, ephemeral=True)

        async with self.store_lock:
            removed = self.store.remove_birthday(interaction.user.id)

        if not removed:
            await self._send_message(
                interaction,
                "Bạn chưa set ngày sinh.",
                ephemeral=True,
            )
            return

        await self._send_message(
            interaction,
            "Đã xóa ngày sinh.",
            ephemeral=True,
        )

    @app_commands.command(name="birthday_channel", description="Set kênh gửi thông báo sinh nhật.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channel="Kênh nhận thông báo sinh nhật")
    async def birthday_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ) -> None:
        if interaction.guild is None:
            await self._send_message(
                interaction,
                "Lệnh này chỉ được dùng trong SV.",
                ephemeral=True,
            )
            return

        me = interaction.guild.me or interaction.guild.get_member(self.bot.user.id)
        if me is not None:
            permissions = channel.permissions_for(me)
            missing_permissions: list[str] = []
            if not permissions.send_messages:
                missing_permissions.append("Send Messages")
            if not permissions.embed_links:
                missing_permissions.append("Embed Links")

            if missing_permissions:
                await self._send_message(
                    interaction,
                    f"Bot chưa đủ quyền {channel.mention}: {', '.join(missing_permissions)}.",
                    ephemeral=True,
                )
                return

            mention_everyone_warning = not permissions.mention_everyone
        else:
            mention_everyone_warning = False

        await self._safe_defer(interaction, ephemeral=True)

        async with self.store_lock:
            self.store.set_announcement_channel(interaction.guild.id, channel.id)

        message = f"Đã set kênh thông báo sinh nhật thành {channel.mention}."
        if mention_everyone_warning:
            message += (
                "\nLuu y: bot chưa có quyền `Mention Everyone`,nên `@everyone` có thể sẽ không ping được."
            )

        await self._send_message(interaction, message, ephemeral=True)

    @tasks.loop(minutes=10)
    async def birthday_checker(self) -> None:
        today = current_birthday_date()

        async with self.store_lock:
            due_birthdays = self.store.due_birthdays(today)

        for notice in due_birthdays:
            sent = await self._send_birthday_announcement(notice, today)
            if not sent:
                continue

            async with self.store_lock:
                birthday = self.store.get_birthday(int(notice.user_id))
                if birthday is None:
                    continue
                if birthday.get("day") != notice.day or birthday.get("month") != notice.month:
                    continue
                self.store.mark_announced(notice.guild_id, notice.user_id, today.year)

    @birthday_checker.before_loop
    async def before_birthday_checker(self) -> None:
        await self.bot.wait_until_ready()

    async def _send_birthday_announcement(
        self,
        notice: BirthdayNotice,
        today: date,
    ) -> bool:
        channel = self.bot.get_channel(notice.channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(notice.channel_id)
            except (discord.Forbidden, discord.HTTPException, discord.NotFound):
                return False

        if not isinstance(channel, discord.TextChannel):
            return False

        guild = channel.guild
        member = guild.get_member(int(notice.user_id))
        if member is None:
            try:
                member = await guild.fetch_member(int(notice.user_id))
            except (discord.Forbidden, discord.HTTPException, discord.NotFound):
                member = None

        if member is None:
            return False

        embed = discord.Embed(
            title="Happy Birthday!",
            description=(
                f"Happy Birthday <@{notice.user_id}>!\n"
                "Chúc bạn có 1 ngày thật vui vẻ, nhiều quà và thật nhiều may mắn."
            ),
            color=discord.Color.gold(),
        )
        embed.add_field(name="Ngày sinh", value=format_birthday(notice.day, notice.month), inline=True)
        embed.add_field(name="Server", value=guild.name, inline=True)
        embed.set_footer(text=f"Sinh nhật năm {today.year}")

        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)

        try:
            await channel.send(
                content=f"@everyone Hôm nay là ngày may mắn của <@{notice.user_id}>!",
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    everyone=True,
                    users=True,
                    roles=False,
                ),
            )
        except discord.DiscordException:
            return False

        return True

    async def _send_message(
        self,
        interaction: discord.Interaction,
        content: str | None = None,
        *,
        embed: discord.Embed | None = None,
        ephemeral: bool = False,
    ) -> None:
        if interaction.response.is_done():
            await interaction.followup.send(content=content, embed=embed, ephemeral=ephemeral)
            return

        try:
            await interaction.response.send_message(
                content=content,
                embed=embed,
                ephemeral=ephemeral,
            )
        except discord.HTTPException as error:
            error_code = getattr(error, "code", None)
            if error_code not in {40060, 10062}:
                raise
            await interaction.followup.send(content=content, embed=embed, ephemeral=ephemeral)

    async def _safe_defer(
        self,
        interaction: discord.Interaction,
        *,
        ephemeral: bool = False,
    ) -> None:
        if interaction.response.is_done():
            return

        try:
            await interaction.response.defer(ephemeral=ephemeral, thinking=True)
        except discord.HTTPException as error:
            error_code = getattr(error, "code", None)
            if error_code not in {40060, 10062}:
                raise


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Birthday(bot))
