try:
    from ddgs import DDGS
except ImportError:  # pragma: no cover
    from duckduckgo_search import DDGS


def search_web(query: str, max_results: int = 5):
    """
    Search the web and return summarized results
    """

    results = []

    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "link": r.get("href", ""),
                    "snippet": r.get("body", "")
                })

        return results

    except Exception as e:
        return [{"error": str(e)}]
