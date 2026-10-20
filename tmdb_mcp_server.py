import json
import os
from typing import Any

import requests
from mcp.server import MCPServer

TMDB_API_TOKEN = os.getenv("TMDB_API_TOKEN", "").strip()
TMDB_BASE_URL = "https://api.themoviedb.org/3"

mcp = MCPServer(
    "TMDB Movie MCP",
    instructions="Use TMDB tools for movie discovery and details."
)


def tmdb_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    if not TMDB_API_TOKEN:
        raise RuntimeError("TMDB_API_TOKEN is missing.")
    headers = {
        "Authorization": f"Bearer {TMDB_API_TOKEN}",
        "accept": "application/json",
    }
    response = requests.get(
        f"{TMDB_BASE_URL}{path}",
        headers=headers,
        params=params or {},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


@mcp.tool()
def search_movies(query: str, language: str = "en-US", page: int = 1) -> str:
    """Search TMDB for movies by title."""
    query = query.strip()
    if not query:
        return json.dumps({"success": False, "message": "Movie query is required."})
    data = tmdb_get(
        "/search/movie",
        {
            "query": query,
            "language": language,
            "page": max(1, min(page, 10)),
            "include_adult": "false",
        },
    )
    results = []
    for item in data.get("results", [])[:8]:
        results.append({
            "id": item.get("id"),
            "title": item.get("title"),
            "original_title": item.get("original_title"),
            "release_date": item.get("release_date"),
            "overview": item.get("overview"),
            "vote_average": item.get("vote_average"),
            "vote_count": item.get("vote_count"),
            "poster_path": item.get("poster_path"),
            "backdrop_path": item.get("backdrop_path"),
            "original_language": item.get("original_language"),
        })
    return json.dumps({"success": True, "query": query, "results": results}, ensure_ascii=False)


@mcp.tool()
def get_movie_details(movie_id: int, language: str = "en-US") -> str:
    """Get full TMDB details for a movie by its TMDB movie ID."""
    data = tmdb_get(
        f"/movie/{int(movie_id)}",
        {"language": language, "append_to_response": "videos"},
    )
    result = {
        "id": data.get("id"),
        "title": data.get("title"),
        "original_title": data.get("original_title"),
        "tagline": data.get("tagline"),
        "overview": data.get("overview"),
        "release_date": data.get("release_date"),
        "runtime": data.get("runtime"),
        "status": data.get("status"),
        "original_language": data.get("original_language"),
        "genres": [g.get("name") for g in data.get("genres", [])],
        "vote_average": data.get("vote_average"),
        "vote_count": data.get("vote_count"),
        "poster_path": data.get("poster_path"),
        "backdrop_path": data.get("backdrop_path"),
        "homepage": data.get("homepage"),
    }
    return json.dumps({"success": True, "movie": result}, ensure_ascii=False)


@mcp.tool()
def get_movie_credits(movie_id: int, language: str = "en-US") -> str:
    """Get cast and crew information for a TMDB movie ID."""
    data = tmdb_get(f"/movie/{int(movie_id)}/credits", {"language": language})
    cast = [
        {"name": c.get("name"), "character": c.get("character"), "order": c.get("order")}
        for c in data.get("cast", [])[:15]
    ]
    crew = [
        {"name": c.get("name"), "job": c.get("job"), "department": c.get("department")}
        for c in data.get("crew", [])
        if c.get("job") in {"Director", "Writer", "Screenplay", "Producer"}
    ][:20]
    return json.dumps({"success": True, "movie_id": movie_id, "cast": cast, "crew": crew}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
