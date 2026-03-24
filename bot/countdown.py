from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html import unescape
import json
import re
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from tools.web_search import search_web


VIETNAM_TIMEZONE = timezone(timedelta(hours=7), name="Asia/Ho_Chi_Minh")
REQUEST_TIMEOUT = 8
SEARCH_RESULT_LIMIT = 5
USER_AGENT = "BoBeoDSBot/1.0"

MONTH_NAMES = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

MONTH_PATTERN = (
    "january|february|march|april|may|june|july|august|"
    "september|october|november|december"
)


@dataclass(frozen=True)
class CountdownEvent:
    name: str
    aliases: tuple[str, ...]
    emoji: str
    description: str
    color: int
    month: int | None = None
    day: int | None = None
    yearly_dates: dict[int, date] | None = None

    def next_occurrence(self, today: date) -> date:
        if self.yearly_dates:
            for year in sorted(self.yearly_dates):
                event_date = self.yearly_dates[year]
                if event_date >= today:
                    return event_date
            raise ValueError(f"Chưa có dữ liệu: {self.name}.")

        if self.month is None or self.day is None:
            raise ValueError(f"Sự kiên {self.name} chưa đủ thông tin ngày tháng.")

        candidate = date(today.year, self.month, self.day)
        if candidate < today:
            candidate = date(today.year + 1, self.month, self.day)
        return candidate


@dataclass(frozen=True)
class CountdownResult:
    event_name: str
    target_date: date
    days_remaining: int
    emoji: str
    description: str
    color: int
    is_custom: bool = False
    source_title: str | None = None
    source_url: str | None = None


@dataclass(frozen=True)
class SearchDocument:
    title: str
    link: str
    snippet: str
    kind: str = "snippet"


@dataclass(frozen=True)
class DateCandidate:
    event_date: date
    source_title: str
    source_url: str
    source_kind: str
    exact_year: bool
    relevance_score: int


TET_DATES = {
    2020: date(2020, 1, 25),
    2021: date(2021, 2, 12),
    2022: date(2022, 2, 1),
    2023: date(2023, 1, 22),
    2024: date(2024, 2, 10),
    2025: date(2025, 1, 29),
    2026: date(2026, 2, 17),
    2027: date(2027, 2, 6),
    2028: date(2028, 1, 26),
    2029: date(2029, 2, 13),
    2030: date(2030, 2, 3),
    2031: date(2031, 1, 23),
    2032: date(2032, 2, 11),
    2033: date(2033, 1, 31),
    2034: date(2034, 2, 19),
    2035: date(2035, 2, 8),
    2036: date(2036, 1, 28),
    2037: date(2037, 2, 15),
    2038: date(2038, 2, 4),
    2039: date(2039, 1, 24),
    2040: date(2040, 2, 12),
    2041: date(2041, 2, 1),
    2042: date(2042, 1, 22),
    2043: date(2043, 2, 10),
    2044: date(2044, 1, 30),
    2045: date(2045, 2, 17),
    2046: date(2046, 2, 6),
    2047: date(2047, 1, 26),
    2048: date(2048, 2, 14),
    2049: date(2049, 2, 2),
}


SUPPORTED_EVENTS = (
    CountdownEvent(
        name="Tet",
        aliases=("tet nguyen dan", "tet am", "tet lunar"),
        emoji="🧧",
        description="Tết nguyên đán",
        color=0xE53935,
        yearly_dates=TET_DATES,
    ),
    CountdownEvent(
        name="New Year",
        aliases=("nam moi", "tet duong", "duong lich"),
        emoji="🎆",
        description="Năm mới",
        color=0x1E88E5,
        month=1,
        day=1,
    ),
    CountdownEvent(
        name="Noel",
        aliases=("giáng sinh"),
        emoji="🎄",
        description="Giáng sinh",
        color=0x2E7D32,
        month=12,
        day=25,
    ),
    CountdownEvent(
        name="Valentine",
        aliases=("tình nhân"),
        emoji="💘",
        description="Ngày lễ tình nhân",
        color=0xD81B60,
        month=2,
        day=14,
    ),
    CountdownEvent(
        name="Halloween",
        aliases=("hóa trang, kinh dị"),
        emoji="🎃",
        description="Hóa trang/Kinh dị",
        color=0xEF6C00,
        month=10,
        day=31,
    ),
)


def current_local_date() -> date:
    return datetime.now(VIETNAM_TIMEZONE).date()


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.strip().lower())
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    without_separators = re.sub(r"[-_]+", " ", without_marks)
    return re.sub(r"\s+", " ", without_separators).strip()


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def resolve_event(name: str) -> CountdownEvent | None:
    normalized_name = normalize_text(name)
    for event in SUPPORTED_EVENTS:
        aliases = {normalize_text(event.name), *(normalize_text(alias) for alias in event.aliases)}
        if normalized_name in aliases:
            return event
    return None


def suggest_event_names(query: str = "") -> list[str]:
    normalized_query = normalize_text(query)
    names = [event.name for event in SUPPORTED_EVENTS]
    if not normalized_query:
        return names

    matches = [
        event.name
        for event in SUPPORTED_EVENTS
        if normalized_query in normalize_text(event.name)
        or any(normalized_query in normalize_text(alias) for alias in event.aliases)
    ]
    return matches or names


def parse_custom_date(value: str) -> date | None:
    cleaned = value.strip()
    for date_format in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, date_format).date()
        except ValueError:
            continue
    return None


def _build_month_day_candidate(month: int, day: int, today: date) -> date | None:
    try:
        candidate = date(today.year, month, day)
    except ValueError:
        return None

    if candidate < today:
        try:
            candidate = date(today.year + 1, month, day)
        except ValueError:
            return None
    return candidate


def _clean_search_text(value: str) -> str:
    text = unescape(value)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _document_relevance(event_name: str, title: str, snippet: str) -> int:
    query = normalize_text(event_name)
    normalized_title = normalize_text(title)
    normalized_snippet = normalize_text(snippet)
    combined_text = f"{normalized_title} {normalized_snippet}".strip()
    query_tokens = [token for token in query.split() if len(token) >= 2]
    combined_tokens = set(combined_text.split())

    score = 0
    if query and query in combined_text:
        score += 4
    if query and normalized_title == query:
        score += 3
    score += sum(1 for token in query_tokens if token in combined_tokens)
    return score


def _extract_date_candidates_from_text(
    text: str,
    today: date,
    source_title: str,
    source_url: str,
    source_kind: str,
    relevance_score: int,
) -> list[DateCandidate]:
    cleaned = _clean_search_text(text)
    search_text = _strip_accents(cleaned).lower()
    candidates: list[DateCandidate] = []

    iso_pattern = re.compile(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b")
    month_day_year_pattern = re.compile(
        rf"\b({MONTH_PATTERN})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,)?\s+(20\d{{2}})\b"
    )
    day_month_year_pattern = re.compile(
        rf"\b(\d{{1,2}})\s+({MONTH_PATTERN})\s+(20\d{{2}})\b"
    )
    month_day_pattern = re.compile(
        rf"\b({MONTH_PATTERN})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b"
    )
    day_month_pattern = re.compile(
        rf"\b(\d{{1,2}})\s+({MONTH_PATTERN})\b"
    )
    vietnamese_pattern = re.compile(
        r"\b(?:ngay\s+)?(\d{1,2})\s+thang\s+(\d{1,2})(?:\s+nam\s+(20\d{2}))?\b"
    )

    for year_text, month_text, day_text in iso_pattern.findall(search_text):
        try:
            event_date = date(int(year_text), int(month_text), int(day_text))
        except ValueError:
            continue
        candidates.append(
            DateCandidate(
                event_date=event_date,
                source_title=source_title,
                source_url=source_url,
                source_kind=source_kind,
                exact_year=True,
                relevance_score=relevance_score,
            )
        )

    for month_name, day_text, year_text in month_day_year_pattern.findall(search_text):
        month = MONTH_NAMES[month_name]
        try:
            event_date = date(int(year_text), month, int(day_text))
        except ValueError:
            continue
        candidates.append(
            DateCandidate(
                event_date=event_date,
                source_title=source_title,
                source_url=source_url,
                source_kind=source_kind,
                exact_year=True,
                relevance_score=relevance_score,
            )
        )

    for day_text, month_name, year_text in day_month_year_pattern.findall(search_text):
        month = MONTH_NAMES[month_name]
        try:
            event_date = date(int(year_text), month, int(day_text))
        except ValueError:
            continue
        candidates.append(
            DateCandidate(
                event_date=event_date,
                source_title=source_title,
                source_url=source_url,
                source_kind=source_kind,
                exact_year=True,
                relevance_score=relevance_score,
            )
        )

    for day_text, month_text, year_text in vietnamese_pattern.findall(search_text):
        month = int(month_text)
        day = int(day_text)
        if year_text:
            try:
                event_date = date(int(year_text), month, day)
            except ValueError:
                continue
            candidates.append(
                DateCandidate(
                    event_date=event_date,
                    source_title=source_title,
                    source_url=source_url,
                    source_kind=source_kind,
                    exact_year=True,
                    relevance_score=relevance_score,
                )
            )
            continue

        candidate = _build_month_day_candidate(month, day, today)
        if candidate is None:
            continue
        candidates.append(
            DateCandidate(
                event_date=candidate,
                source_title=source_title,
                source_url=source_url,
                source_kind=source_kind,
                exact_year=False,
                relevance_score=relevance_score,
            )
        )

    for month_name, day_text in month_day_pattern.findall(search_text):
        candidate = _build_month_day_candidate(MONTH_NAMES[month_name], int(day_text), today)
        if candidate is None:
            continue
        candidates.append(
            DateCandidate(
                event_date=candidate,
                source_title=source_title,
                source_url=source_url,
                source_kind=source_kind,
                exact_year=False,
                relevance_score=relevance_score,
            )
        )

    for day_text, month_name in day_month_pattern.findall(search_text):
        candidate = _build_month_day_candidate(MONTH_NAMES[month_name], int(day_text), today)
        if candidate is None:
            continue
        candidates.append(
            DateCandidate(
                event_date=candidate,
                source_title=source_title,
                source_url=source_url,
                source_kind=source_kind,
                exact_year=False,
                relevance_score=relevance_score,
            )
        )

    unique_candidates: list[DateCandidate] = []
    seen = set()
    for candidate in candidates:
        key = (
            candidate.event_date,
            candidate.source_title,
            candidate.source_url,
            candidate.source_kind,
            candidate.exact_year,
        )
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(candidate)
    return unique_candidates


def _score_candidate(candidate: DateCandidate, today: date) -> tuple[int, int, int, int]:
    days_remaining = (candidate.event_date - today).days
    near_future_score = 0 if candidate.event_date.year <= today.year + 1 else 1
    exact_score = 0 if candidate.exact_year else 1
    kind_score = {"title": 0, "snippet": 1, "summary": 2}.get(candidate.source_kind, 3)
    return (-candidate.relevance_score, near_future_score, days_remaining, exact_score, kind_score)


def _pick_best_candidate(candidates: list[DateCandidate], today: date) -> DateCandidate | None:
    future_candidates = [
        candidate
        for candidate in candidates
        if (candidate.event_date - today).days >= 0
    ]
    if not future_candidates:
        return None
    return min(future_candidates, key=lambda candidate: _score_candidate(candidate, today))


def _get_json(url: str, params: dict[str, str] | None = None) -> dict:
    query_string = f"?{urlencode(params)}" if params else ""
    request = Request(
        f"{url}{query_string}",
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return {}


def _search_documents_with_wikipedia(event_name: str, language: str) -> list[SearchDocument]:
    api_base_url = f"https://{language}.wikipedia.org"
    payload = _get_json(
        f"{api_base_url}/w/api.php",
        {
            "action": "query",
            "list": "search",
            "srsearch": event_name,
            "format": "json",
            "utf8": "1",
            "srlimit": "3",
        },
    )
    if not payload:
        return []

    documents: list[SearchDocument] = []
    for item in payload.get("query", {}).get("search", []):
        title = item.get("title", "").strip()
        if not title:
            continue

        wiki_path = quote(title.replace(" ", "_"), safe=":_()'")
        wiki_url = f"{api_base_url}/wiki/{wiki_path}"
        snippet = _clean_search_text(item.get("snippet", ""))
        if snippet:
            documents.append(
                SearchDocument(
                    title=title,
                    link=wiki_url,
                    snippet=snippet,
                    kind="snippet",
                )
            )

        summary_payload = _get_json(f"{api_base_url}/api/rest_v1/page/summary/{wiki_path}")
        extract = _clean_search_text(summary_payload.get("extract", ""))
        if extract:
            documents.append(
                SearchDocument(
                    title=title,
                    link=wiki_url,
                    snippet=extract,
                    kind="summary",
                )
            )

    return documents


def _collect_search_documents(event_name: str, today: date) -> list[SearchDocument]:
    documents: list[SearchDocument] = []
    search_queries = [
        f'"{event_name}" date {today.year}',
        f'"{event_name}" {today.year + 1} date',
    ]

    for query in search_queries:
        try:
            results = search_web(query, max_results=SEARCH_RESULT_LIMIT)
        except Exception:
            results = []

        for result in results:
            if "error" in result:
                continue
            title = _clean_search_text(str(result.get("title", "")))
            link = str(result.get("link", "")).strip()
            snippet = _clean_search_text(str(result.get("snippet", "")))
            if not title and not snippet:
                continue
            documents.append(
                SearchDocument(
                    title=title or event_name,
                    link=link,
                    snippet=snippet,
                    kind="snippet",
                )
            )

    documents.extend(_search_documents_with_wikipedia(event_name, "en"))
    documents.extend(_search_documents_with_wikipedia(event_name, "vi"))

    deduped_documents: list[SearchDocument] = []
    seen = set()
    for document in documents:
        key = (document.title, document.link, document.snippet, document.kind)
        if key in seen:
            continue
        seen.add(key)
        deduped_documents.append(document)
    return deduped_documents


def resolve_dynamic_event(event_name: str, today: date) -> CountdownResult | None:
    documents = _collect_search_documents(event_name, today)
    candidates: list[DateCandidate] = []

    for document in documents:
        relevance_score = _document_relevance(event_name, document.title, document.snippet)
        if relevance_score <= 0:
            continue
        candidates.extend(
            _extract_date_candidates_from_text(
                document.title,
                today,
                document.title,
                document.link,
                "title",
                relevance_score,
            )
        )
        candidates.extend(
            _extract_date_candidates_from_text(
                document.snippet,
                today,
                document.title,
                document.link,
                document.kind,
                relevance_score,
            )
        )

    candidate = _pick_best_candidate(candidates, today)
    if candidate is None:
        return None

    return CountdownResult(
        event_name=event_name.strip(),
        target_date=candidate.event_date,
        days_remaining=(candidate.event_date - today).days,
        emoji="📅",
        description="Tự động tìm ngày sự kiện",
        color=0x546E7A,
        source_title=candidate.source_title,
        source_url=candidate.source_url,
    )


def build_countdown(
    event_name: str,
    today: date | None = None,
    custom_date: date | None = None,
) -> CountdownResult:
    today = today or current_local_date()

    if custom_date is not None:
        return CountdownResult(
            event_name=event_name.strip(),
            target_date=custom_date,
            days_remaining=(custom_date - today).days,
            emoji="📅",
            description="Sự kiện tùy chỉnh",
            color=0x8E24AA,
            is_custom=True,
        )

    event = resolve_event(event_name)
    if event is not None:
        target_date = event.next_occurrence(today)
        return CountdownResult(
            event_name=event.name,
            target_date=target_date,
            days_remaining=(target_date - today).days,
            emoji=event.emoji,
            description=event.description,
            color=event.color,
        )

    resolved_event = resolve_dynamic_event(event_name, today)
    if resolved_event is None:
        raise ValueError("Không tìm thấy ngày của sự kiện này.")
    return resolved_event
