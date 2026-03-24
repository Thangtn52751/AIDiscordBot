from datetime import date
import unittest
from unittest.mock import patch

from bot.countdown import (
    SearchDocument,
    _extract_date_candidates_from_text,
    build_countdown,
    parse_custom_date,
    resolve_dynamic_event,
    resolve_event,
    suggest_event_names,
)


class CountdownTests(unittest.TestCase):
    def test_resolve_tet_with_basic_alias(self) -> None:
        event = resolve_event("Tet")

        self.assertIsNotNone(event)
        self.assertEqual(event.name, "Tet")

    def test_build_countdown_uses_next_tet_date(self) -> None:
        result = build_countdown("Tet", today=date(2026, 3, 24))

        self.assertEqual(result.target_date, date(2027, 2, 6))
        self.assertEqual(result.days_remaining, (date(2027, 2, 6) - date(2026, 3, 24)).days)

    def test_parse_custom_date_supports_multiple_formats(self) -> None:
        self.assertEqual(parse_custom_date("24/03/2026"), date(2026, 3, 24))
        self.assertEqual(parse_custom_date("2026-03-24"), date(2026, 3, 24))

    def test_build_countdown_for_custom_event(self) -> None:
        result = build_countdown(
            "Sinh nhật",
            today=date(2026, 3, 24),
            custom_date=date(2026, 5, 1),
        )

        self.assertTrue(result.is_custom)
        self.assertEqual(result.days_remaining, 38)

    def test_suggest_event_names_returns_matches(self) -> None:
        self.assertEqual(suggest_event_names("hal"), ["Halloween"])

    def test_extract_date_candidates_parses_recurring_month_day(self) -> None:
        candidates = _extract_date_candidates_from_text(
            "Pi Day is celebrated on March 14 every year.",
            date(2026, 3, 24),
            "Pi Day",
            "https://example.com/pi-day",
            "snippet",
            5,
        )

        self.assertTrue(candidates)
        self.assertEqual(candidates[0].event_date, date(2027, 3, 14))

    def test_extract_date_candidates_parses_exact_date(self) -> None:
        candidates = _extract_date_candidates_from_text(
            "The event takes place on July 14, 2026.",
            date(2026, 3, 24),
            "Example Event",
            "https://example.com/event",
            "snippet",
            5,
        )

        self.assertTrue(candidates)
        self.assertEqual(candidates[0].event_date, date(2026, 7, 14))

    @patch("bot.countdown._collect_search_documents")
    def test_resolve_dynamic_event_from_search_documents(self, mock_collect_search_documents) -> None:
        mock_collect_search_documents.return_value = [
            SearchDocument(
                title="Pi Day",
                link="https://example.com/pi-day",
                snippet="Pi Day is celebrated on March 14 every year.",
                kind="snippet",
            )
        ]

        result = resolve_dynamic_event("Pi Day", date(2026, 3, 24))

        self.assertIsNotNone(result)
        self.assertEqual(result.event_name, "Pi Day")
        self.assertEqual(result.target_date, date(2027, 3, 14))
        self.assertEqual(result.source_url, "https://example.com/pi-day")


if __name__ == "__main__":
    unittest.main()
