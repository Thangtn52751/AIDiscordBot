import os
from typing import Any, Mapping
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Create OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


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
        "Use this only to personalize the reply naturally and playfully.",
        "If roast_nickname or roast_profile is present, prioritize it when teasing this user.",
        "Do not invent private information beyond these fields."
    ]
    return "\n".join(lines)


def _build_image_instruction(message: str) -> str:
    user_message = message.strip() or "Xem nhanh anh nay roi tra loi ngan gon."
    lines = [
        "Nhiem vu voi anh:",
        "- Chi mo ta nhung gi thay ro trong anh.",
        "- Tra loi ngan gon, tu nhien, dung tone cua nhan vat.",
        "- Khong phan tich chuyen sau, khong suy dien qua da.",
        "- Khong doan nghe nghiep, benh ly, y do hay boi canh neu anh khong cho thay ro.",
        "- Neu user hoi mot diem cu the trong anh, thi tap trung vao diem do.",
        f"Yeu cau cua user: {user_message}"
    ]
    return "\n".join(lines)


def ask_ai(
    personality: str,
    message: str,
    user_context: Mapping[str, Any] | None = None
) -> str:
    """
    Chat with AI using text only
    """

    try:
        messages = [
            {
                "role": "system",
                "content": personality
            }
        ]
        discord_context = _build_discord_context(user_context)
        if discord_context:
            messages.append(
                {
                    "role": "system",
                    "content": discord_context
                }
            )
        messages.append(
            {
                "role": "user",
                "content": message
            }
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7
        )

        return response.choices[0].message.content

    except Exception as e:
        print("OpenAI text error:", e)
        return "⚠️ AI text error."


def ask_ai_with_image(
    personality: str,
    message: str,
    image_url: str,
    user_context: Mapping[str, Any] | None = None
) -> str:
    """
    Chat with AI using text + image
    """

    try:
        messages = [
            {
                "role": "system",
                "content": personality
            }
        ]
        discord_context = _build_discord_context(user_context)
        if discord_context:
            messages.append(
                {
                    "role": "system",
                    "content": discord_context
                }
            )
        messages.append(
            {
                "role": "system",
                "content": _build_image_instruction(message)
            }
        )
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": message.strip() or "Xem nhanh anh nay."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=250,
            temperature=0.6
        )

        return response.choices[0].message.content

    except Exception as e:
        print("OpenAI image error:", e)
        return "⚠️ AI image analysis error."
