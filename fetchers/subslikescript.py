"""
Fallback fetcher using subslikescript.com
"""
import re
import requests
from bs4 import BeautifulSoup

BASE = "https://subslikescript.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _search(query: str) -> list[dict]:
    """Search for a title and return list of results."""
    url = f"{BASE}/search"
    resp = requests.get(url, params={"q": query}, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    results = []
    for a in soup.select("ul.scripts-list a"):
        href = a.get("href", "")
        title = a.get_text(strip=True)
        if href:
            results.append({"title": title, "url": BASE + href})
    return results


def fetch_script(show: str, season: int, episode_query: str) -> dict:
    """
    Fetch script via subslikescript.com.

    Returns same structure as springfield.fetch_script.
    """
    result = {
        "show": show,
        "season": season,
        "episode_code": "",
        "episode_title": "",
        "script": "",
        "source_url": "",
        "error": None,
    }

    try:
        season_str = f"season {season}"
        ep_lower = episode_query.lower()

        # Build search query
        query = f"{show} season {season} {episode_query}"
        candidates = _search(query)

        if not candidates:
            result["error"] = "No results found on SubsLikeScript."
            return result

        # Pick the best matching candidate
        chosen = None
        for c in candidates:
            t = c["title"].lower()
            if show.lower() in t and season_str in t and ep_lower in t:
                chosen = c
                break
        if not chosen:
            chosen = candidates[0]

        result["episode_title"] = chosen["title"]
        result["source_url"] = chosen["url"]

        resp = requests.get(chosen["url"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        article = soup.find("article", class_="main-article")
        if not article:
            result["error"] = "Could not locate transcript on SubsLikeScript page."
            return result

        for br in article.find_all("br"):
            br.replace_with("\n")

        script_text = article.get_text(separator="\n")
        script_text = re.sub(r"\n{3,}", "\n\n", script_text).strip()
        result["script"] = script_text

    except requests.HTTPError as exc:
        result["error"] = f"HTTP error: {exc}"
    except Exception as exc:
        result["error"] = f"Unexpected error: {exc}"

    return result
