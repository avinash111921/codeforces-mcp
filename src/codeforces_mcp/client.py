import asyncio
import time
from pathlib import Path
from typing import Any
import httpx
from diskcache import Cache

CACHE_DIR = Path.home() / ".cache" / "codeforces-mcp"


class CodeforcesClient:
    BASE_URL = "https://codeforces.com/api"

    def __init__(self, rate_limit_delay: float = 2.1) -> None:
        self.rate_limit_delay = rate_limit_delay
        self._lock = asyncio.Lock()
        self._last_call_time = 0.0
        self.cache = Cache(str(CACHE_DIR))
        self._http = httpx.AsyncClient(timeout=15.0)

    async def _request(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        async with self._lock:
            elapsed = time.monotonic() - self._last_call_time
            if elapsed < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - elapsed)

            url = f"{self.BASE_URL}/{endpoint}"
            response = await self._http.get(url, params=params)
            self._last_call_time = time.monotonic()

            response.raise_for_status()
            data = response.json()
            if data.get("status") != "OK":
                raise RuntimeError(data.get("comment", "Unknown Codeforces API error"))
            return data["result"]

    async def get_user_info(self, handle: str) -> dict[str, Any]:
        result = await self._request("user.info", {"handles": handle})
        return result[0]

    async def get_user_submissions(self, handle: str, count: int = 50) -> list[dict[str, Any]]:
        return await self._request("user.status", {"handle": handle, "from": 1, "count": count})

    async def get_problemset(self) -> dict[str, Any]:
        cached = self.cache.get("problemset_all")
        if cached is not None:
            return cached
        result = await self._request("problemset.problems")
        # Cache the 10,000+ problem catalog for 1 hour
        self.cache.set("problemset_all", result, expire=3600)
        return result

    async def get_upcoming_contests(self) -> list[dict[str, Any]]:
        cached = self.cache.get("upcoming_contests")
        if cached is not None:
            return cached
        contests = await self._request("contest.list", {"gym": "false"})
        upcoming = [c for c in contests if c.get("phase") == "BEFORE"]
        upcoming.sort(key=lambda x: x.get("startTimeSeconds", 0))
        self.cache.set("upcoming_contests", upcoming, expire=900)
        return upcoming

    async def close(self) -> None:
        await self._http.aclose()