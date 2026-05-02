import asyncio

import aiohttp

from database.cache import cache_anime, get_cached_anime

JIKAN_BASE = "https://api.jikan.moe/v4"
RATE_LIMIT_DELAY = 1
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)


async def fetch_jikan(endpoint: str, params: dict | None = None):
    await asyncio.sleep(RATE_LIMIT_DELAY)

    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
        async with session.get(f"{JIKAN_BASE}/{endpoint}", params=params) as resp:
            if resp.status == 429:
                await asyncio.sleep(2)
                return await fetch_jikan(endpoint, params=params)

            if resp.status != 200:
                return None

            return await resp.json()


async def search_anime_api(query: str):
    cached = get_cached_anime(query)
    if cached:
        return cached

    data = await fetch_jikan("anime", params={"q": query, "limit": 1})
    if not data or not data.get("data"):
        return None

    result = data["data"][0]
    cache_anime(query, result)
    return result


async def get_random_anime_api():
    data = await fetch_jikan("random/anime")
    return data.get("data") if data else None


async def get_top_anime_api(limit: int = 10):
    data = await fetch_jikan("top/anime", params={"limit": limit})
    return data.get("data") if data else []
