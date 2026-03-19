from __future__ import annotations

import asyncio
import os
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import discord
from discord import app_commands
from discord.ext import commands
from yt_dlp import YoutubeDL


if TYPE_CHECKING:
    from bot.bot import BoBeoBot


VOICE_SESSION_RESET_CODES = {4006, 4017}

YTDLP_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "default_search": "ytsearch1",
    "quiet": True,
    "no_warnings": True,
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


@dataclass(slots=True)
class Track:
    title: str
    webpage_url: str
    duration: int | None
    requester_name: str

    @property
    def duration_label(self) -> str:
        if self.duration is None:
            return "Khong ro"

        minutes, seconds = divmod(self.duration, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02}:{seconds:02}"
        return f"{minutes}:{seconds:02}"


class GuildMusicState:
    def __init__(self, bot: "BoBeoBot", guild: discord.Guild) -> None:
        self.bot = bot
        self.guild = guild
        self.queue: deque[Track] = deque()
        self.current: Track | None = None
        self.lock = asyncio.Lock()
        self.text_channel_id: int | None = None
        self.volume = 0.5
        self.ffmpeg_executable = self._resolve_ffmpeg_executable()

    @property
    def voice_client(self) -> discord.VoiceClient | None:
        return self.guild.voice_client

    @property
    def is_active(self) -> bool:
        voice_client = self.voice_client
        if voice_client is None:
            return False
        return voice_client.is_playing() or voice_client.is_paused() or self.current is not None

    async def enqueue(self, track: Track, text_channel_id: int | None) -> tuple[bool, int]:
        self.queue.append(track)
        if text_channel_id is not None:
            self.text_channel_id = text_channel_id

        should_start = not self.is_active
        await self.start_if_idle()
        return should_start, len(self.queue)

    async def start_if_idle(self) -> None:
        async with self.lock:
            await self._play_next_locked()

    async def skip(self) -> bool:
        voice_client = self.voice_client
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            voice_client.stop()
            return True
        return False

    async def stop(self) -> None:
        self.queue.clear()
        self.current = None
        voice_client = self.voice_client
        if voice_client and voice_client.is_connected():
            voice_client.stop()
            await voice_client.disconnect()

    def reset(self) -> None:
        self.queue.clear()
        self.current = None
        self.text_channel_id = None

    async def _play_next_locked(self) -> None:
        voice_client = self.voice_client
        if voice_client is None or not voice_client.is_connected():
            self.current = None
            return

        if voice_client.is_playing() or voice_client.is_paused():
            return

        while self.queue:
            track = self.queue.popleft()
            try:
                source = await self._build_audio_source(track)
            except Exception as exc:
                self.current = None
                await self._notify(
                    f"Khong the tai bai **{track.title}**: `{exc}`. Chuyen sang bai tiep theo."
                )
                continue

            self.current = track

            def after_playback(error: Exception | None) -> None:
                asyncio.run_coroutine_threadsafe(
                    self._handle_track_end(error),
                    self.bot.loop,
                )

            voice_client.play(source, after=after_playback)
            await self._notify(
                f"Dang phat: **{track.title}** ({track.duration_label})"
                f" | yeu cau boi **{track.requester_name}**"
            )
            return

        self.current = None

    async def _handle_track_end(self, error: Exception | None) -> None:
        if error is not None:
            await self._notify(f"Phat nhac gap loi: `{error}`")

        async with self.lock:
            self.current = None
            await self._play_next_locked()

    async def _build_audio_source(
        self,
        track: Track,
    ) -> discord.PCMVolumeTransformer[discord.FFmpegPCMAudio]:
        info = await asyncio.to_thread(self._extract_info, track.webpage_url)
        stream_url = info.get("url")
        if not stream_url:
            raise RuntimeError("Khong lay duoc audio bai hat")

        audio = discord.FFmpegPCMAudio(
            stream_url,
            executable=self.ffmpeg_executable,
            **FFMPEG_OPTIONS,
        )
        return discord.PCMVolumeTransformer(audio, volume=self.volume)

    async def _notify(self, content: str) -> None:
        if self.text_channel_id is None:
            return

        channel = self.bot.get_channel(self.text_channel_id)
        if channel is None:
            return

        try:
            await channel.send(content)
        except discord.DiscordException:
            return

    @staticmethod
    def _extract_info(query: str) -> dict:
        options = GuildMusicState._build_ytdlp_options()

        try:
            with YoutubeDL(options) as ytdl:
                info = ytdl.extract_info(query, download=False)
        except Exception as exc:
            raise RuntimeError(GuildMusicState._format_ytdlp_error(exc)) from exc

        if info is None:
            raise RuntimeError("Khong tim thay ket qua")

        if "entries" in info:
            entries = [entry for entry in info["entries"] if entry]
            if not entries:
                raise RuntimeError("Khong tim thay bai hat phu hop")
            info = entries[0]

        return info

    @staticmethod
    def _build_ytdlp_options() -> dict:
        options = dict(YTDLP_OPTIONS)

        cookiefile = os.getenv("YTDLP_COOKIEFILE")
        if cookiefile:
            options["cookiefile"] = cookiefile

        browser_spec = os.getenv("YTDLP_COOKIES_FROM_BROWSER")
        if browser_spec:
            options["cookiesfrombrowser"] = GuildMusicState._parse_cookies_from_browser(browser_spec)

        options["http_headers"] = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        return options

    @staticmethod
    def _parse_cookies_from_browser(browser_spec: str) -> tuple[str, str | None, str | None, str | None]:
        spec = browser_spec.strip()

        container = None
        if "::" in spec:
            spec, container = spec.split("::", 1)
            container = container.strip() or None

        profile = None
        if ":" in spec:
            spec, profile = spec.split(":", 1)
            profile = profile.strip() or None

        keyring = None
        if "+" in spec:
            spec, keyring = spec.split("+", 1)
            keyring = keyring.strip().upper() or None

        browser = spec.strip().lower()
        if not browser:
            raise RuntimeError("YTDLP_COOKIES_FROM_BROWSER khong hop le")

        return (browser, profile, keyring, container)

    @staticmethod
    def _format_ytdlp_error(exc: Exception) -> str:
        message = str(exc)
        if "Sign in to confirm you’re not a bot" in message or "Sign in to confirm you're not a bot" in message:
            return (
                "YouTube dang yeu cau xac minh. Hay cung cap cookies cho yt-dlp bang "
                "`YTDLP_COOKIEFILE=/duong-dan/cookies.txt` hoac "
                "`YTDLP_COOKIES_FROM_BROWSER=chrome`/`edge`. Tren Railway, nen dung "
                "`YTDLP_COOKIEFILE` thay vi cookies tu browser."
            )
        return message

    @staticmethod
    def _resolve_ffmpeg_executable() -> str:
        env_path = os.getenv("FFMPEG_PATH")
        if env_path:
            return env_path

        bundled = os.path.join("bin", "ffmpeg", "ffmpeg.exe")
        if os.path.exists(bundled):
            return bundled

        return "ffmpeg"


class Music(commands.Cog):
    def __init__(self, bot: "BoBeoBot") -> None:
        self.bot = bot
        self.states: dict[int, GuildMusicState] = {}

    def get_state(self, guild: discord.Guild) -> GuildMusicState:
        state = self.states.get(guild.id)
        if state is None:
            state = GuildMusicState(self.bot, guild)
            self.states[guild.id] = state
        return state

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if not self.bot.user or member.id != self.bot.user.id:
            return

        if before.channel is not None and after.channel is None and member.guild.id in self.states:
            self.states[member.guild.id].reset()

    @app_commands.command(
        name="play",
        description="Phat nhac tu ten hoac link."
    )
    @app_commands.describe(query="Ten bai hat hoac link YouTube")
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Lenh nay chi dung duoc trong server.",
                ephemeral=True,
            )
            return

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "Ban can vao voice truoc khi dung lenh nay.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        try:
            voice_client = await self._ensure_voice_client(interaction)
        except RuntimeError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return

        state = self.get_state(interaction.guild)

        try:
            info = await asyncio.to_thread(state._extract_info, query)
        except Exception as exc:
            await interaction.followup.send(
                f"Khong tim duoc bai hat phu hop: `{exc}`",
                ephemeral=True,
            )
            return

        title = info.get("title") or "Khong ro ten bai"
        webpage_url = info.get("webpage_url") or info.get("original_url") or query
        duration = info.get("duration")
        track = Track(
            title=title,
            webpage_url=webpage_url,
            duration=duration,
            requester_name=interaction.user.display_name,
        )

        should_start, queue_size = await state.enqueue(track, interaction.channel_id)

        embed = discord.Embed(
            title="Them nhac thanh cong",
            color=discord.Color.green(),
        )
        embed.add_field(name="Bai", value=track.title, inline=False)
        embed.add_field(name="Thoi luong", value=track.duration_label, inline=True)
        embed.add_field(name="Nguoi yeu cau", value=track.requester_name, inline=True)
        embed.add_field(
            name="Trang thai",
            value=(
                f"Bot da vao **{voice_client.channel}** va dang chuan bi phat."
                if should_start
                else f"Da them bai hat vao hang cho. Con {queue_size} bai trong hang cho."
            ),
            inline=False,
        )
        if is_probable_url(query):
            embed.add_field(name="Nguon", value=track.webpage_url, inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="pause",
        description="Tam dung bai dang phat."
    )
    async def pause(self, interaction: discord.Interaction) -> None:
        voice_client = interaction.guild.voice_client if interaction.guild else None
        if voice_client is None or not voice_client.is_playing():
            await interaction.response.send_message(
                "Hien khong co bai nao dang phat.",
                ephemeral=True,
            )
            return

        voice_client.pause()
        await interaction.response.send_message("Da tam dung bai hat hien tai.")

    @app_commands.command(
        name="resume",
        description="Tiep tuc bai hat dang dung."
    )
    async def resume(self, interaction: discord.Interaction) -> None:
        voice_client = interaction.guild.voice_client if interaction.guild else None
        if voice_client is None or not voice_client.is_paused():
            await interaction.response.send_message(
                "Khong co bai nao dang dung.",
                ephemeral=True,
            )
            return

        voice_client.resume()
        await interaction.response.send_message("Da tiep tuc phat nhac.")

    @app_commands.command(
        name="skip",
        description="Bo qua bai hien tai."
    )
    async def skip(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Lenh nay chi dung duoc trong server.",
                ephemeral=True,
            )
            return

        state = self.get_state(interaction.guild)
        skipped = await state.skip()
        if not skipped:
            await interaction.response.send_message(
                "Khong co bai hat nao can bo qua.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message("Da bo qua bai hien tai.")

    @app_commands.command(
        name="stop",
        description="Dung phat nhac va thoat voice."
    )
    async def stop(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Lenh nay chi dung duoc trong server.",
                ephemeral=True,
            )
            return

        state = self.get_state(interaction.guild)
        if state.voice_client is None:
            await interaction.response.send_message(
                "Bot chua o voice nao.",
                ephemeral=True,
            )
            return

        await state.stop()
        await interaction.response.send_message("Da dung nhac va roi khoi voice.")

    @app_commands.command(
        name="queue",
        description="Xem bai dang phat va hang cho."
    )
    async def queue(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Lenh nay chi dung duoc trong server.",
                ephemeral=True,
            )
            return

        state = self.get_state(interaction.guild)
        if state.current is None and not state.queue:
            await interaction.response.send_message("Hang cho hien dang trong.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Danh sach nhac",
            color=discord.Color.blurple(),
        )

        if state.current is not None:
            embed.add_field(
                name="Dang phat",
                value=(
                    f"**{state.current.title}**"
                    f" ({state.current.duration_label})"
                    f" | yeu cau boi **{state.current.requester_name}**"
                ),
                inline=False,
            )

        if state.queue:
            upcoming = []
            for index, track in enumerate(list(state.queue)[:10], start=1):
                upcoming.append(
                    f"`{index}.` {track.title} ({track.duration_label}) - {track.requester_name}"
                )
            embed.add_field(
                name=f"Ke tiep ({len(state.queue)})",
                value="\n".join(upcoming),
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    async def _ensure_voice_client(
        self,
        interaction: discord.Interaction,
    ) -> discord.VoiceClient:
        assert interaction.guild is not None
        assert isinstance(interaction.user, discord.Member)

        target_channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        try:
            if voice_client is None:
                voice_client = await target_channel.connect()
            elif voice_client.channel != target_channel:
                await voice_client.move_to(target_channel)
        except (discord.ClientException, discord.DiscordException) as exc:
            raise RuntimeError(self._build_voice_connection_error(exc)) from exc

        return voice_client

    @staticmethod
    def _build_voice_connection_error(exc: Exception) -> str:
        close_code = getattr(exc, "code", None)
        if close_code in VOICE_SESSION_RESET_CODES:
            return (
                "Bot khong the vao voice chat vi discord.py hien tai khong con "
                f"tuong thich voi Discord voice handshake (websocket {close_code}). "
                "Hay cap nhat dependency va khoi dong lai bot."
            )

        return (
            "Bot khong the vao voice. Hay kiem tra quyen Connect/Speak, "
            "voice dependency, va FFmpeg."
        )


def is_probable_url(value: str) -> bool:
    parsed = urlparse(value)
    return bool(parsed.scheme and parsed.netloc)


async def setup(bot: "BoBeoBot") -> None:
    await bot.add_cog(Music(bot))
