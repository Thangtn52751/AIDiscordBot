from __future__ import annotations

import asyncio
import os
from collections import deque
from dataclasses import dataclass, field

import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "default_search": "ytsearch",
    "noplaylist": True,
    "quiet": True,
}

FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5"
    ),
    "options": "-vn",
}
FFMPEG_EXECUTABLE = os.getenv("FFMPEG_PATH", "ffmpeg")


@dataclass(slots=True)
class Track:
    title: str
    stream_url: str
    webpage_url: str
    duration: int | None
    requested_by: str

    @property
    def duration_text(self) -> str:
        if not self.duration:
            return "Không rõ"

        minutes, seconds = divmod(self.duration, 60)
        hours, minutes = divmod(minutes, 60)

        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"


@dataclass(slots=True)
class GuildMusicState:
    queue: deque[Track] = field(default_factory=deque)
    current: Track | None = None
    text_channel_id: int | None = None


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.states: dict[int, GuildMusicState] = {}

    def get_state(self, guild_id: int) -> GuildMusicState:
        return self.states.setdefault(guild_id, GuildMusicState())

    def format_voice_error(self, error: Exception) -> str:
        message = str(error)
        lowered = message.lower()

        if "library needed in order to use voice" in lowered:
            return (
                "Bot chưa sẵn sàng cho voice trên máy này. "
                "Cần cài thêm dependency voice của `discord.py` rồi khởi động lại bot."
            )

        if isinstance(error, discord.Forbidden):
            return "Bot không có quyền vào hoặc nói trong voice channel này."

        if isinstance(error, discord.ClientException):
            return f"Không thể kết nối voice lúc này: {message}"

        return f"Lỗi khi kết nối voice: {message}"

    async def send_music_message(self, guild: discord.Guild, content: str) -> None:
        state = self.get_state(guild.id)
        if not state.text_channel_id:
            return

        channel = guild.get_channel(state.text_channel_id)
        if isinstance(channel, discord.abc.Messageable):
            await channel.send(content)

    async def ensure_voice(
        self,
        interaction: discord.Interaction,
    ) -> tuple[discord.VoiceClient | None, discord.VoiceChannel | None]:
        if not interaction.guild or not interaction.user:
            return None, None

        voice_state = getattr(interaction.user, "voice", None)
        if not voice_state or not voice_state.channel:
            return None, None

        channel = voice_state.channel
        voice_client = interaction.guild.voice_client

        if voice_client and voice_client.channel != channel:
            await voice_client.move_to(channel)
            return voice_client, channel

        if voice_client:
            return voice_client, channel

        try:
            connected_client = await channel.connect()
        except Exception as error:
            raise RuntimeError(self.format_voice_error(error)) from error
        return connected_client, channel

    async def extract_track(self, query: str, requested_by: str) -> Track:
        def _extract() -> Track:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(query, download=False)

            if "entries" in info:
                info = next((entry for entry in info["entries"] if entry), None)

            if not info:
                raise ValueError("Không tìm thấy bài nào phù hợp.")

            stream_url = info.get("url")
            if not stream_url:
                raise ValueError("Không lấy được luồng phát cho bài hát.")

            return Track(
                title=info.get("title", "Không rõ tiêu đề"),
                stream_url=stream_url,
                webpage_url=info.get("webpage_url") or query,
                duration=info.get("duration"),
                requested_by=requested_by,
            )

        return await asyncio.to_thread(_extract)

    async def create_source(self, track: Track) -> discord.AudioSource:
        refreshed_track = await self.extract_track(track.webpage_url, track.requested_by)
        track.stream_url = refreshed_track.stream_url
        return await discord.FFmpegOpusAudio.from_probe(
            track.stream_url,
            executable=FFMPEG_EXECUTABLE,
            **FFMPEG_OPTIONS,
        )

    async def play_next(self, guild: discord.Guild) -> None:
        state = self.get_state(guild.id)
        voice_client = guild.voice_client

        if not voice_client:
            state.current = None
            state.queue.clear()
            return

        if not state.queue:
            state.current = None
            return

        track = state.queue.popleft()
        try:
            source = await self.create_source(track)
        except Exception as error:
            state.current = None
            await self.send_music_message(
                guild,
                f"Không phát được **{track.title}**: {error}",
            )
            await self.play_next(guild)
            return
        state.current = track

        def after_playback(error: Exception | None) -> None:
            if error:
                print(f"[Music] Playback error in guild {guild.id}: {error}")
            future = asyncio.run_coroutine_threadsafe(
                self.play_next(guild),
                self.bot.loop,
            )
            try:
                future.result()
            except Exception as callback_error:
                print(f"[Music] Failed to continue queue in guild {guild.id}: {callback_error}")

        voice_client.play(source, after=after_playback)
        await self.send_music_message(
            guild,
            f"🎶 Đang phát: **{track.title}** (`{track.duration_text}`)",
        )

    @app_commands.command(
        name="join",
        description="Cho bot vào voice channel của bạn."
    )
    async def join(self, interaction: discord.Interaction) -> None:
        try:
            voice_client, channel = await self.ensure_voice(interaction)
        except RuntimeError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        if not voice_client or not channel:
            await interaction.response.send_message(
                "Bạn cần vào voice channel trước đã.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Đã vào voice channel **{channel.name}**."
        )

    @app_commands.command(
        name="play",
        description="Phát nhạc từ YouTube bằng link hoặc từ khóa tìm kiếm."
    )
    @app_commands.describe(query="Link YouTube hoặc từ khóa tìm kiếm")
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "Lệnh này chỉ dùng được trong server.",
                ephemeral=True,
            )
            return

        try:
            voice_client, channel = await self.ensure_voice(interaction)
        except RuntimeError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        if not voice_client or not channel:
            await interaction.response.send_message(
                "Bạn cần vào voice channel trước đã.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        try:
            track = await self.extract_track(query, interaction.user.display_name)
        except Exception as error:
            await interaction.followup.send(
                f"Không mở được bài hát này: {error}"
            )
            return

        state = self.get_state(interaction.guild.id)
        state.text_channel_id = interaction.channel_id
        state.queue.append(track)

        message = (
            f"Đã thêm **{track.title}** vào hàng chờ"
            f" (`{track.duration_text}`)."
        )

        if voice_client.is_playing() or voice_client.is_paused():
            await interaction.followup.send(message)
            return

        await self.play_next(interaction.guild)
        await interaction.followup.send(
            f"{message} Bắt đầu phát trong **{channel.name}**."
        )

    @app_commands.command(
        name="skip",
        description="Bỏ qua bài đang phát."
    )
    async def skip(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not interaction.guild.voice_client:
            await interaction.response.send_message(
                "Hiện bot chưa phát gì cả.",
                ephemeral=True,
            )
            return

        voice_client = interaction.guild.voice_client
        if not voice_client.is_playing() and not voice_client.is_paused():
            await interaction.response.send_message(
                "Hiện bot chưa phát gì cả.",
                ephemeral=True,
            )
            return

        current = self.get_state(interaction.guild.id).current
        voice_client.stop()
        await interaction.response.send_message(
            f"Đã bỏ qua: **{current.title if current else 'bài hiện tại'}**."
        )

    @app_commands.command(
        name="queue",
        description="Xem bài đang phát và các bài tiếp theo."
    )
    async def queue(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "Lệnh này chỉ dùng được trong server.",
                ephemeral=True,
            )
            return

        state = self.get_state(interaction.guild.id)
        if not state.current and not state.queue:
            await interaction.response.send_message("Hàng chờ đang trống.")
            return

        lines = []
        if state.current:
            lines.append(
                f"**Đang phát:** {state.current.title} (`{state.current.duration_text}`)"
            )

        upcoming = list(state.queue)[:10]
        if upcoming:
            for index, track in enumerate(upcoming, start=1):
                lines.append(
                    f"`{index}.` {track.title} (`{track.duration_text}`) - {track.requested_by}"
                )

        remaining = len(state.queue) - len(upcoming)
        if remaining > 0:
            lines.append(f"... và còn **{remaining}** bài nữa trong hàng chờ.")

        embed = discord.Embed(
            title="Hàng chờ âm nhạc",
            description="\n".join(lines),
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="leave",
        description="Dừng nhạc, xóa hàng chờ và rời voice channel."
    )
    async def leave(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not interaction.guild.voice_client:
            await interaction.response.send_message(
                "Bot chưa ở trong voice channel nào.",
                ephemeral=True,
            )
            return

        state = self.get_state(interaction.guild.id)
        state.queue.clear()
        state.current = None
        state.text_channel_id = None

        voice_client = interaction.guild.voice_client
        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()
        await voice_client.disconnect()

        await interaction.response.send_message("Đã rời voice channel và xóa hàng chờ.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Music(bot))
