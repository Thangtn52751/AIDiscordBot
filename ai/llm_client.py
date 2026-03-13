import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Create OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


def ask_ai(personality: str, message: str) -> str:
    """
    Chat with AI using text only
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": personality
                },
                {
                    "role": "user",
                    "content": message
                }
            ],
            temperature=0.7
        )

        return response.choices[0].message.content

    except Exception as e:
        print("OpenAI text error:", e)
        return "⚠️ AI text error."


def ask_ai_with_image(personality: str, message: str, image_url: str) -> str:
    """
    Chat with AI using text + image
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": personality
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": message
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            }
                        }
                    ]
                }
            ],
            max_tokens=500
        )

        return response.choices[0].message.content

    except Exception as e:
        print("OpenAI image error:", e)
        return "⚠️ AI image analysis error."