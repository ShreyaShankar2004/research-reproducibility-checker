"""
Code/Repo Discovery Agent
Searches GitHub and Papers With Code for official/unofficial implementations.
"""
import httpx
import os

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")  # optional, raises rate limit from 60/hr to 5000/hr


async def search_github(paper_title: str, arxiv_id: str) -> list[dict]:
    """Search GitHub for repos referencing this paper."""
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    results = []
    queries = [arxiv_id, paper_title[:80]]

    async with httpx.AsyncClient(timeout=20) as client:
        for q in queries:
            try:
                resp = await client.get(
                    "https://api.github.com/search/repositories",
                    params={"q": q, "sort": "stars", "order": "desc", "per_page": 5},
                    headers=headers,
                )
                if resp.status_code == 200:
                    items = resp.json().get("items", [])
                    for item in items:
                        results.append({
                            "name": item["full_name"],
                            "url": item["html_url"],
                            "stars": item["stargazers_count"],
                            "description": item.get("description", ""),
                            "source": "github_search",
                        })
            except Exception:
                continue

    # Dedupe by name
    seen = set()
    deduped = []
    for r in results:
        if r["name"] not in seen:
            seen.add(r["name"])
            deduped.append(r)
    return deduped[:10]


async def search_papers_with_code(arxiv_id: str) -> dict:
    """Query Papers With Code API for official implementations + benchmark results."""
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.get(
                f"https://paperswithcode.com/api/v1/papers/{arxiv_id}/repositories/"
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "found": True,
                    "repositories": [
                        {
                            "url": r["url"],
                            "is_official": r.get("is_official", False),
                            "stars": r.get("stars", 0),
                            "framework": r.get("framework", "unknown"),
                        }
                        for r in data.get("results", [])
                    ],
                }
        except Exception:
            pass
    return {"found": False, "repositories": []}


async def discover_code(paper_title: str, arxiv_id: str) -> dict:
    """Combine GitHub + Papers With Code results."""
    github_results = await search_github(paper_title, arxiv_id)
    pwc_results = await search_papers_with_code(arxiv_id)

    official_found = any(r["is_official"] for r in pwc_results.get("repositories", []))

    return {
        "official_implementation_found": official_found,
        "papers_with_code": pwc_results,
        "github_candidates": github_results,
    }
