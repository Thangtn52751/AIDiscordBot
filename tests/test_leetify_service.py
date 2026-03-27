import unittest

from services.leetify_service import LeetifyService


class LeetifyServiceTests(unittest.TestCase):
    def test_parse_api_response_extracts_public_profile_metrics(self) -> None:
        stats = LeetifyService.parse_api_response(
            {
                "privacy_mode": "public",
                "name": "Slinky",
                "ranks": {
                    "leetify": 2.12,
                    "premier": 19309,
                    "faceit": 9,
                    "faceit_elo": None,
                    "wingman": 17,
                    "renown": 16482,
                },
                "rating": {
                    "aim": 60.2568,
                    "positioning": 57.1424,
                    "utility": 70.1944,
                    "opening": -0.0024,
                },
            },
            "https://leetify.com/app/profile/76561197969209908",
        )

        assert stats is not None
        self.assertEqual(stats["name"], "Slinky")
        self.assertEqual(stats["leetify_rating"], "2.12")
        self.assertEqual(stats["aim"], "60.26")
        self.assertEqual(stats["positioning"], "57.14")
        self.assertEqual(stats["utility"], "70.19")
        self.assertEqual(stats["entrying"], "0")
        self.assertEqual(stats["premier_rank"], "19309")
        self.assertEqual(stats["faceit_rank"], "9")
        self.assertEqual(stats["faceit_elo"], "N/A")
        self.assertEqual(stats["wingman_rank"], "17")
        self.assertEqual(stats["renown_rank"], "16482")
        self.assertEqual(stats["status"], "ok")
        self.assertEqual(stats["status_message"], "Da lay du lieu tu Leetify Public API.")
        self.assertTrue(stats["has_stats"])

    def test_parse_api_response_extracts_latest_match_metrics(self) -> None:
        stats = LeetifyService.parse_api_response(
            {
                "player": {"displayName": "im_NTT"},
                "matches": [
                    {
                        "performance": {
                            "leetifyRating": 1.1,
                            "aim": 71,
                            "positioning": 60,
                            "utility": 55,
                            "opening": 48,
                        }
                    },
                    {
                        "performance": {
                            "leetifyRating": 1.3,
                            "aim": 73,
                            "positioning": 62,
                            "utility": 57,
                            "opening": 50,
                        }
                    },
                ],
            },
            "https://leetify.com/app/profile/76561198000000000",
        )

        assert stats is not None
        self.assertEqual(stats["name"], "im_NTT")
        self.assertEqual(stats["leetify_rating"], "1.1")
        self.assertEqual(stats["aim"], "71")
        self.assertEqual(stats["positioning"], "60")
        self.assertEqual(stats["utility"], "55")
        self.assertEqual(stats["entrying"], "48")
        self.assertEqual(stats["status_message"], "Da lay du lieu tu Leetify API.")
        self.assertTrue(stats["has_stats"])

    def test_parse_profile_html_extracts_metrics(self) -> None:
        stats = LeetifyService.parse_profile_html(
            """
            <html>
              <head><title>im_NTT | Leetify</title></head>
              <body>
                <div>Leetify Rating</div><div>1.23</div>
                <div>Aim</div><div>72.1</div>
                <div>Positioning</div><div>61.4</div>
                <div>Utility</div><div>55.0</div>
                <div>Opening</div><div>49.8</div>
              </body>
            </html>
            """,
            "https://leetify.com/app/profile/76561198000000000",
        )

        assert stats is not None
        self.assertEqual(stats["name"], "im_NTT")
        self.assertEqual(stats["leetify_rating"], "1.23")
        self.assertEqual(stats["aim"], "72.1")
        self.assertEqual(stats["positioning"], "61.4")
        self.assertEqual(stats["utility"], "55.0")
        self.assertEqual(stats["entrying"], "49.8")
        self.assertEqual(stats["status"], "ok")
        self.assertTrue(stats["has_stats"])

    def test_parse_profile_html_detects_login_requirement(self) -> None:
        stats = LeetifyService.parse_profile_html(
            """
            <html>
              <head><title>Leetify</title></head>
              <body>
                <div>Sign in to Leetify</div>
              </body>
            </html>
            """,
            "https://leetify.com/app/profile/76561198000000000",
        )

        assert stats is not None
        self.assertEqual(stats["status"], "login_required")
        self.assertFalse(stats["has_stats"])

    def test_parse_api_response_handles_private_public_profile(self) -> None:
        stats = LeetifyService.parse_api_response(
            {
                "privacy_mode": "private",
                "name": "Hidden",
                "ranks": {},
                "rating": {},
            },
            "https://leetify.com/app/profile/76561197960287930",
        )

        assert stats is not None
        self.assertEqual(stats["status"], "private")
        self.assertEqual(stats["status_message"], "Profile Leetify dang de private.")
        self.assertFalse(stats["has_stats"])


if __name__ == "__main__":
    unittest.main()
