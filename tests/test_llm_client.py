import os
import unittest
from unittest.mock import MagicMock, patch

import httpx

from ai import llm_client


class GeminiClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def client_mock(self):
        constructor = patch.object(llm_client.genai, "Client").start()
        self.addCleanup(patch.stopall)
        client = constructor.return_value.__enter__.return_value
        client.models.generate_content.return_value.text = "  Xin chào!  "
        return constructor, client

    def test_text_uses_gemini_model_and_preserves_target_context(self) -> None:
        constructor, client = self.client_mock()
        os.environ["GEMINI_MODEL"] = "custom-model"
        result = llm_client.ask_ai(
            "My personality",
            "Hello",
            {"user_id": "123", "has_target": "true", "target_display_name": "An"},
        )
        self.assertEqual(result, "Xin chào!")
        kwargs = client.models.generate_content.call_args.kwargs
        self.assertEqual(kwargs["model"], "custom-model")
        self.assertEqual(kwargs["contents"], "Hello")
        self.assertIn("My personality", kwargs["config"].system_instruction)
        self.assertIn("target_display_name: An", kwargs["config"].system_instruction)
        self.assertIsNone(kwargs["config"].temperature)
        self.assertEqual(constructor.call_args.kwargs["api_key"], "test-key")
        options = constructor.call_args.kwargs["http_options"]
        self.assertEqual(options.timeout, 45_000)
        self.assertEqual(options.retry_options.attempts, 1)
        constructor.return_value.__exit__.assert_called_once()

    def test_missing_key_is_lazy_and_does_not_make_request(self) -> None:
        os.environ.pop("GEMINI_API_KEY")
        constructor, _ = self.client_mock()
        with self.assertLogs(llm_client.logger, level="WARNING"):
            result = llm_client.ask_ai("Personality", "Hello")
        constructor.assert_not_called()
        self.assertIn("Gemini đang gặp lỗi", result)

    def test_empty_or_blocked_response_has_user_facing_fallback(self) -> None:
        _, client = self.client_mock()
        for text in [None, "", "   "]:
            with self.subTest(text=text):
                client.models.generate_content.return_value.text = text
                self.assertEqual(llm_client.ask_ai("", "Hi"), llm_client.EMPTY_RESPONSE)

    def test_provider_error_does_not_expose_secrets(self) -> None:
        _, client = self.client_mock()
        client.models.generate_content.side_effect = RuntimeError("secret-key-secret-prompt")
        with self.assertLogs(llm_client.logger, level="WARNING") as logs:
            result = llm_client.ask_ai("", "Hello")
        self.assertNotIn("secret", result + " ".join(logs.output))

    def test_image_passes_inline_bytes_and_context(self) -> None:
        _, client = self.client_mock()
        with patch.object(llm_client, "_download_image", return_value=(b"png-data", "image/png")):
            result = llm_client.ask_ai_with_image("Personality", "Ảnh gì?", "https://cdn.discordapp.com/a.png")
        self.assertEqual(result, "Xin chào!")
        kwargs = client.models.generate_content.call_args.kwargs
        self.assertEqual(kwargs["contents"][0].inline_data.data, b"png-data")
        self.assertEqual(kwargs["contents"][0].inline_data.mime_type, "image/png")
        self.assertIn("Ảnh gì?", kwargs["contents"][1])
        self.assertEqual(kwargs["config"].system_instruction, "Personality")


class ImageDownloadTests(unittest.TestCase):
    url = "https://cdn.discordapp.com/attachments/1/2/image.png?ex=signed"

    def response_mock(self, headers=None, chunks=None):
        response = MagicMock()
        response.headers = headers or {"content-type": "image/png"}
        response.iter_bytes.return_value = chunks if chunks is not None else [b"image-data"]
        return response

    def stream_mock(self, response):
        stream = patch.object(llm_client.httpx, "stream").start()
        self.addCleanup(patch.stopall)
        stream.return_value.__enter__.return_value = response
        return stream

    def test_valid_discord_image_download(self) -> None:
        stream = self.stream_mock(self.response_mock({"content-type": "image/png; charset=binary"}))
        self.assertEqual(llm_client._download_image(self.url), (b"image-data", "image/png"))
        self.assertFalse(stream.call_args.kwargs["follow_redirects"])
        self.assertEqual(stream.call_args.kwargs["timeout"], 15.0)

    def test_rejects_external_or_misleading_urls_before_network(self) -> None:
        with patch.object(llm_client.httpx, "stream") as stream:
            for url in [
                "http://cdn.discordapp.com/a.png",
                "https://localhost/a.png",
                "https://127.0.0.1/a.png",
                "https://cdn.discordapp.com.evil.example/a.png",
                "https://cdn.discordapp.com@evil.example/a.png",
                "https://user@cdn.discordapp.com/a.png",
                "https://cdn.discordapp.com:8080/a.png",
                "https://cdn.discordapp.com:bad/a.png",
            ]:
                with self.subTest(url=url), self.assertRaises(llm_client.InvalidImageError):
                    llm_client._download_image(url)
            stream.assert_not_called()

    def test_rejects_large_header_without_reading_body(self) -> None:
        response = self.response_mock({"content-type": "image/png", "content-length": "99999999"})
        self.stream_mock(response)
        with self.assertRaises(llm_client.InvalidImageError):
            llm_client._download_image(self.url)
        response.iter_bytes.assert_not_called()

    def test_enforces_stream_limit_without_content_length(self) -> None:
        self.stream_mock(self.response_mock(chunks=[b"1234", b"5678"]))
        with patch.object(llm_client, "MAX_IMAGE_BYTES", 6), self.assertRaises(llm_client.InvalidImageError):
            llm_client._download_image(self.url)

    def test_rejects_unsupported_media_and_empty_image(self) -> None:
        for headers, chunks in [({"content-type": "text/html"}, [b"html"]), ({"content-type": "image/png"}, [])]:
            with self.subTest(headers=headers, chunks=chunks):
                response = self.response_mock(headers, chunks)
                with patch.object(llm_client.httpx, "stream") as stream:
                    stream.return_value.__enter__.return_value = response
                    with self.assertRaises(llm_client.InvalidImageError):
                        llm_client._download_image(self.url)

    def test_rejects_redirect_without_following_it(self) -> None:
        response = httpx.Response(302, headers={"location": "https://localhost"}, request=httpx.Request("GET", self.url))
        self.stream_mock(response)
        with self.assertRaises(httpx.HTTPStatusError):
            llm_client._download_image(self.url)

    def test_download_deadline_is_enforced(self) -> None:
        self.stream_mock(self.response_mock())
        with patch.object(llm_client.time, "monotonic", side_effect=[0, 21]):
            with self.assertRaises(TimeoutError):
                llm_client._download_image(self.url)


if __name__ == "__main__":
    unittest.main()
