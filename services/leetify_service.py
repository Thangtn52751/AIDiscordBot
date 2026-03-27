import os
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

try:
    from ddgs import DDGS
except ImportError:  
    from duckduckgo_search import DDGS


class LeetifyService:
    BASE_URL = "https://leetify.com/app/profile"
    PUBLIC_API_BASE_URL = "https://api-public.cs-prod.leetify.com"
    REQUEST_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/136.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    @staticmethod
    async def get_player_stats(steam_id: str) -> dict[str, Any] | None:
        profile_url = f"{LeetifyService.BASE_URL}/{steam_id}"
        has_api_key = bool(os.getenv("LEETIFY_API_KEY"))

        api_result = await LeetifyService._fetch_api_player_stats(steam_id, profile_url)
        if api_result:
            return api_result

        html = await LeetifyService._fetch_profile_html(profile_url)
        if html:
            parsed = LeetifyService.parse_profile_html(html, profile_url)
            if parsed:
                return parsed

        search_result = await LeetifyService._search_profile_stats(steam_id)
        if search_result:
            return search_result

        return LeetifyService._build_unavailable_profile(
            profile_url=profile_url,
            status="unavailable",
            status_message=(
                "Không lấy được dữ liệu từ Leetify. Thêm LEETIFY_API_KEY để gọi API đầy đủ."
                if not has_api_key
                else "Không lấy được dữ liệu từ Leetify API/profile cho tài khoản này."
            ),
        )

    @staticmethod
    async def _fetch_api_player_stats(
        steam_id: str,
        profile_url: str,
    ) -> dict[str, Any] | None:
        api_key = os.getenv("LEETIFY_API_KEY")

        headers = {**LeetifyService.REQUEST_HEADERS}
        if api_key:
            normalized_key = api_key.strip()
            api_key_value = re.sub(r"^bearer\s+", "", normalized_key, flags=re.IGNORECASE)
            bearer = (
                normalized_key
                if normalized_key.lower().startswith("bearer ")
                else f"Bearer {normalized_key}"
            )
            headers["Authorization"] = bearer
            headers["_leetify_key"] = api_key_value

        endpoint_configs = [
            (
                f"{LeetifyService.PUBLIC_API_BASE_URL}/v3/profile",
                [
                    {"steam64_id": steam_id},
                    {"id": steam_id},
                ],
            ),
            (
                f"{LeetifyService.PUBLIC_API_BASE_URL}/v3/profile/matches",
                [{"steam64_id": steam_id}],
            ),
        ]

        saw_rate_limit = False
        saw_not_found = False
        saw_auth_error = False

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                for url, param_sets in endpoint_configs:
                    for params in param_sets:
                        response = await client.get(
                            url,
                            headers=headers,
                            params=params,
                            timeout=10,
                        )

                        if response.status_code == 429:
                            saw_rate_limit = True
                            continue

                        if response.status_code == 404:
                            saw_not_found = True
                            continue

                        if response.status_code == 401:
                            saw_auth_error = True
                            continue

                        if response.status_code != 200:
                            continue

                        payload = response.json()
                        if isinstance(payload, dict) and payload.get("error"):
                            lowered_error = str(payload.get("error")).lower()
                            if "rate limit" in lowered_error:
                                saw_rate_limit = True
                            if "not found" in lowered_error:
                                saw_not_found = True
                            continue

                        parsed = LeetifyService.parse_api_response(
                            payload,
                            profile_url,
                        )
                        if parsed:
                            return parsed
        except httpx.HTTPError:
            return None

        if saw_rate_limit:
            return LeetifyService._build_unavailable_profile(
                profile_url=profile_url,
                status="rate_limited",
                status_message=(
                    "Leetify Public API đang rate limit. Thêm LEETIFY_API_KEY tai https://leetify.com/app/developer để tăng giới hạn."
                ),
            )

        if saw_auth_error and api_key:
            return LeetifyService._build_unavailable_profile(
                profile_url=profile_url,
                status="unauthorized",
                status_message="LEETIFY_API_KEY không hợp lệ.",
            )

        if saw_not_found:
            return LeetifyService._build_unavailable_profile(
                profile_url=profile_url,
                status="not_registered",
                status_message="Tài khoản này chưa đăng ký Leetify",
            )

        return None

    @staticmethod
    async def _fetch_profile_html(profile_url: str) -> str | None:
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    profile_url,
                    headers=LeetifyService.REQUEST_HEADERS,
                    timeout=10,
                )
        except httpx.HTTPError:
            return None

        if response.status_code != 200:
            return None

        return response.text

    @staticmethod
    async def _search_profile_stats(steam_id: str) -> dict[str, Any] | None:
        query = f"site:leetify.com/app/profile/{steam_id} leetify"

        try:
            with DDGS() as ddgs:
                for result in ddgs.text(query, max_results=5):
                    href = result.get("href", "")
                    if steam_id not in href:
                        continue

                    return LeetifyService.parse_search_result(
                        title=result.get("title", ""),
                        snippet=result.get("body", ""),
                        profile_url=href,
                    )
        except Exception:
            return None

        return None

    @staticmethod
    def parse_api_response(
        payload: Any,
        profile_url: str,
    ) -> dict[str, Any] | None:
        public_profile_data = LeetifyService._parse_public_profile_payload(payload, profile_url)
        if public_profile_data:
            return public_profile_data

        name = LeetifyService._search_nested_value(
            payload,
            ["name", "nickname", "displayName", "steamName", "playerName"],
        )
        direct_metrics = LeetifyService._extract_metrics_from_payload(payload)
        recent_match_metrics = LeetifyService._extract_recent_match_metrics(payload)
        metrics = {
            key: direct_metrics.get(key) or recent_match_metrics.get(key) or "N/A"
            for key in ("leetify_rating", "aim", "positioning", "utility", "entrying")
        }

        error_fields = []
        if isinstance(payload, dict):
            error_fields = [
                payload.get("message"),
                payload.get("error"),
                payload.get("detail"),
            ]
        error_text = " ".join(str(value) for value in error_fields if value)
        profile_state = LeetifyService._detect_profile_state(error_text) if error_text else None

        if not any([name, profile_state]) and all(value == "N/A" for value in metrics.values()):
            return None

        using_recent_match = (
            all(value == "N/A" for value in direct_metrics.values())
            and any(value != "N/A" for value in recent_match_metrics.values())
        )

        return {
            "name": str(name) if name else "N/A",
            "profile_url": profile_url,
            "leetify_rating": metrics["leetify_rating"],
            "aim": metrics["aim"],
            "positioning": metrics["positioning"],
            "utility": metrics["utility"],
            "entrying": metrics["entrying"],
            "premier_rank": LeetifyService._normalize_metric_value(
                LeetifyService._search_nested_value(payload, ["premier", "premierRank"])
            ),
            "faceit_rank": LeetifyService._normalize_metric_value(
                LeetifyService._search_nested_value(payload, ["faceit", "faceitRank", "faceitLevel"])
            ),
            "faceit_elo": LeetifyService._normalize_metric_value(
                LeetifyService._search_nested_value(payload, ["faceit_elo", "faceitElo"])
            ),
            "wingman_rank": LeetifyService._normalize_metric_value(
                LeetifyService._search_nested_value(payload, ["wingman", "wingmanRank"])
            ),
            "renown_rank": LeetifyService._normalize_metric_value(
                LeetifyService._search_nested_value(payload, ["renown", "renownRank"])
            ),
            "status": profile_state["status"] if profile_state else "ok",
            "status_message": (
                profile_state["message"]
                if profile_state
                else (
                    "Da lay du lieu tran gan nhat tu Leetify API."
                    if using_recent_match
                    else "Da lay du lieu tu Leetify API."
                )
            ),
            "has_stats": any(value != "N/A" for value in metrics.values()),
        }

    @staticmethod
    def _parse_public_profile_payload(
        payload: Any,
        profile_url: str,
    ) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None

        if not any(key in payload for key in ("privacy_mode", "ranks", "rating")):
            return None

        ranks = payload.get("ranks") if isinstance(payload.get("ranks"), dict) else {}
        rating = payload.get("rating") if isinstance(payload.get("rating"), dict) else {}
        privacy_mode = str(payload.get("privacy_mode") or "").strip().lower()

        profile_state = None
        if privacy_mode == "private":
            profile_state = {
                "status": "private",
                "message": "Profile Leetify dang de private.",
            }

        metrics = {
            "leetify_rating": LeetifyService._normalize_metric_value(ranks.get("leetify")),
            "aim": LeetifyService._normalize_metric_value(rating.get("aim")),
            "positioning": LeetifyService._normalize_metric_value(rating.get("positioning")),
            "utility": LeetifyService._normalize_metric_value(rating.get("utility")),
            "entrying": LeetifyService._normalize_metric_value(rating.get("opening")),
            "premier_rank": LeetifyService._normalize_metric_value(ranks.get("premier")),
            "faceit_rank": LeetifyService._normalize_metric_value(ranks.get("faceit")),
            "faceit_elo": LeetifyService._normalize_metric_value(ranks.get("faceit_elo")),
            "wingman_rank": LeetifyService._normalize_metric_value(ranks.get("wingman")),
            "renown_rank": LeetifyService._normalize_metric_value(ranks.get("renown")),
        }
        has_stats = any(value != "N/A" for value in metrics.values())

        return {
            "name": str(payload.get("name") or "N/A"),
            "profile_url": profile_url,
            "leetify_rating": metrics["leetify_rating"],
            "aim": metrics["aim"],
            "positioning": metrics["positioning"],
            "utility": metrics["utility"],
            "entrying": metrics["entrying"],
            "premier_rank": metrics["premier_rank"],
            "faceit_rank": metrics["faceit_rank"],
            "faceit_elo": metrics["faceit_elo"],
            "wingman_rank": metrics["wingman_rank"],
            "renown_rank": metrics["renown_rank"],
            "status": profile_state["status"] if profile_state else "ok",
            "status_message": (
                profile_state["message"]
                if profile_state
                else (
                    "Da lay du lieu tu Leetify Public API."
                    if has_stats
                    else "Leetify profile khong co du lieu chi tiet."
                )
            ),
            "has_stats": has_stats,
        }

    @staticmethod
    def parse_profile_html(html: str, profile_url: str) -> dict[str, Any] | None:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text("\n", strip=True)
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        return LeetifyService._parse_text_blob(text, title=title, profile_url=profile_url)

    @staticmethod
    def parse_search_result(
        title: str,
        snippet: str,
        profile_url: str,
    ) -> dict[str, Any] | None:
        text = "\n".join([title, snippet])
        return LeetifyService._parse_text_blob(text, title=title, profile_url=profile_url)

    @staticmethod
    def _parse_text_blob(
        text: str,
        *,
        title: str,
        profile_url: str,
    ) -> dict[str, Any] | None:
        if not text and not title:
            return None

        name = LeetifyService._extract_name(title, text)
        rating = LeetifyService._extract_metric(text, "Leetify Rating")
        aim = LeetifyService._extract_metric(text, "Aim")
        positioning = LeetifyService._extract_metric(text, "Positioning")
        utility = LeetifyService._extract_metric(text, "Utility")
        entrying = LeetifyService._extract_metric(text, "Opening")
        profile_state = LeetifyService._detect_profile_state(text)

        if not any([name, rating, aim, positioning, utility, entrying, profile_state]):
            return None

        return {
            "name": name or "N/A",
            "profile_url": profile_url,
            "leetify_rating": rating or "N/A",
            "aim": aim or "N/A",
            "positioning": positioning or "N/A",
            "utility": utility or "N/A",
            "entrying": entrying or "N/A",
            "premier_rank": "N/A",
            "faceit_rank": "N/A",
            "faceit_elo": "N/A",
            "wingman_rank": "N/A",
            "renown_rank": "N/A",
            "status": profile_state["status"] if profile_state else "ok",
            "status_message": (
                profile_state["message"]
                if profile_state
                else "Da lay du lieu tu Leetify."
            ),
            "has_stats": any([rating, aim, positioning, utility, entrying]),
        }

    @staticmethod
    def _extract_name(title: str, text: str) -> str | None:
        title_match = re.search(r"(.+?)\s*\|\s*Leetify", title)
        if title_match:
            return title_match.group(1).strip()

        text_match = re.search(r"Profile\s+for\s+(.+)", text)
        if text_match:
            return text_match.group(1).strip()

        return None

    @staticmethod
    def _extract_metric(text: str, label: str) -> str | None:
        patterns = [
            rf"{re.escape(label)}\s*[:\-]?\s*([+-]?\d+(?:\.\d+)?)",
            rf"{re.escape(label)}\s*\n\s*([+-]?\d+(?:\.\d+)?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _detect_profile_state(text: str) -> dict[str, str] | None:
        lowered = text.lower()

        if "private profile" in lowered or "profile is private" in lowered:
            return {
                "status": "private",
                "message": "Profile Leetify dang de private.",
            }

        if "sign in" in lowered and "leetify" in lowered:
            return {
                "status": "login_required",
                "message": "Leetify yeu cau dang nhap de xem them du lieu.",
            }

        if "not registered" in lowered or "non-users" in lowered:
            return {
                "status": "not_registered",
                "message": "Leetify API chi tra du lieu cho tai khoan da dang ky.",
            }

        return None

    @staticmethod
    def _extract_metrics_from_payload(payload: dict[str, Any]) -> dict[str, str]:
        metric_aliases = {
            "leetify_rating": ["leetifyRating", "leetify_rating", "leetify"],
            "aim": ["aim", "aimRating"],
            "positioning": ["positioning", "positioningRating"],
            "utility": ["utility", "utilityRating"],
            "entrying": ["opening", "openingRating", "entrying", "entryingRating"],
        }
        return {
            key: LeetifyService._normalize_metric_value(
                LeetifyService._search_nested_value(payload, aliases)
            )
            for key, aliases in metric_aliases.items()
        }

    @staticmethod
    def _extract_recent_match_metrics(payload: dict[str, Any]) -> dict[str, str]:
        matches = LeetifyService._find_match_list(payload)
        if not matches:
            return {}

        latest_match = matches[0]
        metric_aliases = {
            "leetify_rating": ["leetifyRating", "leetify_rating", "rating"],
            "aim": ["aim", "aimRating"],
            "positioning": ["positioning", "positioningRating"],
            "utility": ["utility", "utilityRating"],
            "entrying": ["opening", "openingRating", "entrying", "entryingRating"],
        }

        metrics: dict[str, str] = {}
        for metric_name, aliases in metric_aliases.items():
            metrics[metric_name] = LeetifyService._normalize_metric_value(
                LeetifyService._search_nested_value(latest_match, aliases)
            )

        return metrics

    @staticmethod
    def _find_match_list(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            if payload and all(isinstance(item, dict) for item in payload):
                return payload
            return []

        if not isinstance(payload, dict):
            return []

        for key in ("matches", "items", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
                return value
            if isinstance(value, dict):
                nested = LeetifyService._find_match_list(value)
                if nested:
                    return nested

        for value in payload.values():
            nested = LeetifyService._find_match_list(value)
            if nested:
                return nested

        return []

    @staticmethod
    def _search_nested_value(payload: Any, aliases: list[str]):
        if isinstance(payload, dict):
            for key, value in payload.items():
                if key in aliases:
                    return value
                nested = LeetifyService._search_nested_value(value, aliases)
                if nested is not None:
                    return nested

        if isinstance(payload, list):
            for item in payload:
                nested = LeetifyService._search_nested_value(item, aliases)
                if nested is not None:
                    return nested

        return None

    @staticmethod
    def _normalize_metric_value(value: Any) -> str:
        if value in (None, ""):
            return "N/A"

        if isinstance(value, (dict, list, tuple, set)):
            return "N/A"

        if isinstance(value, (int, float)):
            normalized = f"{value:.2f}".rstrip("0").rstrip(".")
            return "0" if normalized in {"-0", "-0.0"} else normalized

        text = str(value).strip()
        if not text:
            return "N/A"

        return text

    @staticmethod
    def _build_unavailable_profile(
        *,
        profile_url: str,
        status: str,
        status_message: str,
    ) -> dict[str, Any]:
        return {
            "name": "N/A",
            "profile_url": profile_url,
            "leetify_rating": "N/A",
            "aim": "N/A",
            "positioning": "N/A",
            "utility": "N/A",
            "entrying": "N/A",
            "premier_rank": "N/A",
            "faceit_rank": "N/A",
            "faceit_elo": "N/A",
            "wingman_rank": "N/A",
            "renown_rank": "N/A",
            "status": status,
            "status_message": status_message,
            "has_stats": False,
        }
