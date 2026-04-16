"""
Fetcher for Springfield Springfield (springfieldspringfield.co.uk)
Publicly available TV episode transcripts.
"""
import re
import requests
from bs4 import BeautifulSoup

BASE = "https://www.springfieldspringfield.co.uk"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _slug(text: str) -> str:
    """Convert show name to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text


def _ep_code(season: str | int, episode: str | int) -> str:
    """Return episode code like s01e03."""
    return f"s{int(season):02d}e{int(episode):02d}"


def list_episodes(show: str, season: int) -> list[dict]:
    """
    Return a list of episodes for the given show/season.
    Each item: {"code": "s01e01", "title": "Pilot", "url": "..."}
    """
    slug = _slug(show)
    url = f"{BASE}/episode_scripts.php?tv-show={slug}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    season_code = f"Season {int(season)}"

    episodes = []
    # Episodes are listed under season headings
    for h3 in soup.find_all("h3"):
        if season_code.lower() in h3.get_text(strip=True).lower():
            ul = h3.find_next_sibling("ul")
            if ul:
                for a in ul.find_all("a", href=True):
                    href = a["href"]
                    m = re.search(r"episode=(s\d+e\d+)", href, re.I)
                    code = m.group(1) if m else ""
                    episodes.append({
                        "code": code,
                        "title": a.get_text(strip=True),
                        "url": BASE + "/" + href.lstrip("/"),
                    })
            break

    return episodes


def search_episode(show: str, season: int, episode_query: str) -> dict | None:
    """
    Find an episode matching `episode_query` (episode number OR title keyword).
    Returns {"code", "title", "url"} or None.
    """
    # If query looks like a number, use it directly
    if re.match(r"^\d+$", episode_query.strip()):
        ep_num = int(episode_query.strip())
        slug = _slug(show)
        code = _ep_code(season, ep_num)
        url = f"{BASE}/view_episode_scripts.php?tv-show={slug}&episode={code}"
        return {"code": code, "title": "", "url": url}

    # Otherwise search by title
    episodes = list_episodes(show, season)
    query_lower = episode_query.lower()
    for ep in episodes:
        if query_lower in ep["title"].lower():
            return ep

    return None


def fetch_script(show: str, season: int, episode_query: str) -> dict:
    """
    Fetch the full transcript for an episode.

    Returns:
        {
            "show": str,
            "season": int,
            "episode_code": str,
            "episode_title": str,
            "script": str,       # full text
            "source_url": str,
            "error": str | None,
        }
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
        ep = search_episode(show, season, episode_query)
        if not ep:
            result["error"] = f"Episode '{episode_query}' not found on Springfield Springfield."
            return result

        result["episode_code"] = ep["code"]
        result["episode_title"] = ep["title"]
        result["source_url"] = ep["url"]

        resp = requests.get(ep["url"], headers=HEADERS, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        # The transcript lives inside <div class="scrolling-script-container">
        container = soup.find("div", class_="scrolling-script-container")
        if not container:
            # Fallback: try the main script div
            container = soup.find("div", id="script-page")

        if not container:
            result["error"] = "Could not locate transcript on the page."
            return result

        # Preserve line breaks
        for br in container.find_all("br"):
            br.replace_with("\n")

        script_text = container.get_text(separator="\n")
        # Clean up excessive blank lines
        script_text = re.sub(r"\n{3,}", "\n\n", script_text).strip()
        result["script"] = script_text

    except requests.HTTPError as exc:
        result["error"] = f"HTTP error fetching script: {exc}"
    except Exception as exc:
        result["error"] = f"Unexpected error: {exc}"

    return result
