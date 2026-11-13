import logging
import os
import time
from typing import Any, Mapping
from urllib.parse import urlsplit

import httpx
from bot.paths import PROJECT_ROOT
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Tải biến môi trường
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)
DEFAULT_MODEL = "gemini-3.5-flash-lite"
GEMINI_TIMEOUT_MS = 45_000
MAX_IMAGE_BYTES = 8 * 1024 * 1024
IMAGE_DOWNLOAD_TIMEOUT = 20
ALLOWED_IMAGE_HOSTS = {"cdn.discordapp.com", "media.discordapp.net"}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
EMPTY_RESPONSE = "Gemini chưa trả lời được yêu cầu này. Bạn thử diễn đạt lại nhé."


class InvalidImageError(ValueError):
    """The attachment is not a supported, bounded Discord image."""


def _create_client() -> genai.Client:
    # Defer credentials and network setup until a user actually requests AI.
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Thiếu biến môi trường GEMINI_API_KEY")
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            api_version="v1",
            timeout=GEMINI_TIMEOUT_MS,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )


def _download_image(image_url: str) -> tuple[bytes, str]:
    """Fetch only Discord CDN attachments, without redirects or unbounded reads."""
    try:
        url = urlsplit(image_url)
        allowed = (
            url.scheme == "https"
            and url.hostname in ALLOWED_IMAGE_HOSTS
            and url.port in {None, 443}
            and url.username is None
            and url.password is None
            and not url.fragment
        )
    except ValueError:
        allowed = False
    if not allowed:
        raise InvalidImageError("Chỉ nhận ảnh đính kèm trực tiếp trên Discord.")

    started = time.monotonic()
    with httpx.stream(
        "GET", image_url, timeout=15.0, follow_redirects=False
    ) as response:
        response.raise_for_status()
        mime_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if mime_type not in ALLOWED_IMAGE_TYPES:
            raise InvalidImageError("Hãy gửi ảnh PNG, JPEG, WebP, HEIC hoặc HEIF.")
        content_length = response.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
            except ValueError:
                raise InvalidImageError("Không đọc được kích thước ảnh.") from None
            if size < 0 or size > MAX_IMAGE_BYTES:
                raise InvalidImageError("Ảnh quá lớn. Hãy gửi ảnh nhỏ hơn 8 MB.")
        image = bytearray()
        for chunk in response.iter_bytes(chunk_size=64 * 1024):
            if time.monotonic() - started > IMAGE_DOWNLOAD_TIMEOUT:
                raise TimeoutError("Image download timed out")
            if len(image) + len(chunk) > MAX_IMAGE_BYTES:
                raise InvalidImageError("Ảnh quá lớn. Hãy gửi ảnh nhỏ hơn 8 MB.")
            image.extend(chunk)
        if not image:
            raise InvalidImageError("Ảnh trống hoặc không đọc được.")
    return bytes(image), mime_type


def _system_instruction(
    personality: str, user_context: Mapping[str, Any] | None
) -> str:
    context = _build_discord_context(user_context)
    return "\n\n".join(part for part in [personality, context] if part)


def _generate(contents: Any, instruction: str) -> str:
    with _create_client() as client:
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=instruction,
                max_output_tokens=1200,
            ),
        )
    return (response.text or "").strip() or EMPTY_RESPONSE


def _build_discord_context(user_context: Mapping[str, Any] | None) -> str | None:
    if not user_context:
        return None

    lines = [
        "Discord user context:",
        f"- discord_user_id: {user_context.get('user_id', 'unknown')}",
        f"- discord_username: {user_context.get('username', 'unknown')}",
        f"- discord_display_name: {user_context.get('display_name', 'unknown')}",
        f"- discord_mention: {user_context.get('mention', 'unknown')}",
        f"- roast_nickname: {user_context.get('roast_nickname', '') or 'none'}",
        f"- roast_profile: {user_context.get('roast_profile', '') or 'none'}",
        f"- extra_instructions: {user_context.get('extra_instructions', '') or 'none'}",
        f"- has_target: {user_context.get('has_target', 'false')}",
        f"- target_user_id: {user_context.get('target_user_id', '') or 'none'}",
        f"- target_username: {user_context.get('target_username', '') or 'none'}",
        f"- target_display_name: {user_context.get('target_display_name', '') or 'none'}",
        f"- target_mention: {user_context.get('target_mention', '') or 'none'}",
        f"- target_roast_nickname: {user_context.get('target_roast_nickname', '') or 'none'}",
        f"- target_roast_profile: {user_context.get('target_roast_profile', '') or 'none'}",
        f"- target_extra_instructions: {user_context.get('target_extra_instructions', '') or 'none'}",
        "Use this only to personalize the reply naturally and playfully.",
        "If has_target is true, direct the playful roast primarily at the target user instead of the requester.",
        "If target_roast_nickname or target_roast_profile is present, prioritize it for the target.",
        "If roast_nickname or roast_profile is present, prioritize it when teasing this user.",
        "Do not invent private information beyond these fields.",
    ]
    return "\n".join(lines)


def _build_image_instruction(message: str) -> str:
    user_message = message.strip() or "Xem nhanh ảnh này rồi trả lời ngắn gọn."
    lines = [
        "Nhiệm vụ:",
        "- Mô tả nhanh những thứ trong ảnh.",
        "- Trả lời ngắn gọn, đúng tone nhân vật.",
        "- Không phân tích quá chuyên sâu, chỉ cần súc tích.",
        "- Nếu user hỏi đoán nghề nghiệp trong ảnh, hãy chú ý quần áo, vật dụng và bối cảnh xung quanh rồi đưa ra phán đoán có chừng mực.",
        "- Nếu user hỏi về địa điểm, hãy chú ý công trình, cảnh vật và chi tiết xung quanh để đưa ra phán đoán.",
        f"Yêu cầu của user: {user_message}",
    ]
    return "\n".join(lines)


def ask_ai(
    personality: str,
    message: str,
    user_context: Mapping[str, Any] | None = None,
) -> str:
    """
    Trò chuyện với AI bằng văn bản.
    """

    try:
        return _generate(
            message.strip() or "Chào bạn!",
            _system_instruction(personality, user_context),
        )

    except Exception as error:
        # SDK errors may contain credentials, prompt text or signed URLs.
        logger.warning("Gemini text request failed (%s)", type(error).__name__)
        return "Gemini đang gặp lỗi. Bạn thử lại sau nhé."


def ask_ai_with_image(
    personality: str,
    message: str,
    image_url: str,
    user_context: Mapping[str, Any] | None = None,
) -> str:
    """
    Trò chuyện với AI bằng văn bản và ảnh.
    """

    try:
        image, mime_type = _download_image(image_url)
        return _generate(
            [
                types.Part.from_bytes(data=image, mime_type=mime_type),
                _build_image_instruction(message),
            ],
            _system_instruction(personality, user_context),
        )

    except InvalidImageError as error:
        return str(error)
    except Exception as error:
        logger.warning("Gemini image request failed (%s)", type(error).__name__)
        return "Gemini phân tích ảnh đang gặp lỗi. Bạn thử lại sau nhé."
