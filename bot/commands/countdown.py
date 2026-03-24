from __future__ import annotations

import asyncio
from datetime import date

import discord
from bot.countdown import CountdownResult, build_countdown, parse_custom_date, suggest_event_names
from discord import app_commands
from discord.ext import commands


class Countdown(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="countdown",
        description="Đếm ngược 1 sự kiện"
    )
    @app_commands.describe(
        event="Tên sự kiện, VD: Tết, Noel, New Year",
        ngay="Ngày tùy chọn theo định dạng dd/mm/yyyy hoặc yyyy-mm-dd"
    )
    async def countdown(
        self,
        interaction: discord.Interaction,
        event: str,
        ngay: str | None = None,
    ) -> None:
        await self._safe_defer(interaction)

        custom_date: date | None = None
        if ngay:
            custom_date = parse_custom_date(ngay)
            if custom_date is None:
                await self._send_message(
                    interaction,
                    "Nhập ngày không đúng định dạng, đinh dạng đúng: `dd/mm/yyyy` hoac `yyyy-mm-dd`.",
                    ephemeral=True,
                )
                return

        try:
            result = await asyncio.to_thread(
                build_countdown,
                event,
                None,
                custom_date,
            )
        except ValueError:
            supported = ", ".join(suggest_event_names())
            await self._send_message(
                interaction,
                f"Mình không tìm thấy sự kiện `{event}`. "
                f"Bạn có thể tìm mấy sự kiện nổi như: {supported}, "
                "hoặc thêm `ngày` để tự đặt sự kiện.",
                ephemeral=True,
            )
            return

        if result.days_remaining < 0:
            await self._send_message(
                interaction,
                f"Ngày `{result.target_date:%d/%m/%Y}` đã qua rồi. "
                "Hãy chọn một ngày trong tương lai.",
                ephemeral=True,
            )
            return

        embed = self._build_embed(interaction, result)
        await self._send_message(interaction, embed=embed)

    def _build_embed(
        self,
        interaction: discord.Interaction,
        result: CountdownResult,
    ) -> discord.Embed:
        if result.days_remaining == 0:
            description = f"{result.emoji} Hôm nay là **{result.event_name}** rồi!"
        else:
            description = (
                f"{result.emoji} Còn **{result.days_remaining} ngày** nữa đến "
                f"**{result.event_name}**."
            )

        embed = discord.Embed(
            title="Countdown Event",
            description=description,
            color=result.color,
        )
        embed.add_field(name="Sự kiện", value=result.event_name, inline=True)
        embed.add_field(name="Ngày", value=result.target_date.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="Loại", value=result.description, inline=False)
        if result.source_url:
            source_label = result.source_title or result.source_url
            embed.add_field(name="Nguồn", value=f"[{source_label}]({result.source_url})", inline=False)
        embed.set_footer(
            text=f"Yêu cầu bởi {interaction.user}",
            icon_url=interaction.user.display_avatar.url,
        )
        return embed

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
            await interaction.response.send_message(content=content, embed=embed, ephemeral=ephemeral)
        except discord.HTTPException as error:
            error_code = getattr(error, "code", None)
            if error_code not in {40060, 10062}:
                raise
            await interaction.followup.send(content=content, embed=embed, ephemeral=ephemeral)

    async def _safe_defer(self, interaction: discord.Interaction) -> None:
        if interaction.response.is_done():
            return

        try:
            await interaction.response.defer(thinking=True)
        except discord.HTTPException as error:
            error_code = getattr(error, "code", None)
            if error_code not in {40060, 10062}:
                raise


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Countdown(bot))
