import asyncio
from typing import Any
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
from diskcache import Cache
from .client import CACHE_DIR

scraper_cache = Cache(str(CACHE_DIR / "problems"))


def _parse_problem_html(html: str, contest_id: int, index: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    statement = soup.select_one("div.problem-statement")
    if not statement:
        raise ValueError(f"Could not locate problem statement for {contest_id}{index}.")

    header = statement.select_one("div.header")
    title = header.select_one("div.title").get_text(strip=True) if header else f"{contest_id}{index}"
    time_limit = (
        header.select_one("div.time-limit").get_text(separator=" ", strip=True)
        if header else "Unknown"
    )
    memory_limit = (
        header.select_one("div.memory-limit").get_text(separator=" ", strip=True)
        if header else "Unknown"
    )

    # Extract sample test cases preserving exact newlines
    samples: list[dict[str, str]] = []
    inputs = statement.select("div.sample-test div.input pre")
    outputs = statement.select("div.sample-test div.output pre")

    for inp, out in zip(inputs, outputs):
        in_lines = [div.get_text() for div in inp.select("div.test-example-line")]
        in_text = "\n".join(in_lines) if in_lines else inp.get_text("\n", strip=True)
        out_text = out.get_text("\n", strip=True)
        samples.append({"input": in_text.strip(), "output": out_text.strip()})

    # Extract body paragraphs
    body_parts = []
    for div in statement.find_all("div", recursive=False):
        classes = div.get("class") or []
        if "header" not in classes and "sample-test" not in classes:
            body_parts.append(div.get_text("\n", strip=True))

    return {
        "problem_id": f"{contest_id}{index.upper()}",
        "title": title,
        "time_limit": time_limit,
        "memory_limit": memory_limit,
        "description": "\n\n".join(body_parts),
        "samples": samples,
    }


async def fetch_problem_statement(contest_id: int, index: str) -> dict[str, Any]:
    key = f"prob_{contest_id}_{index.upper()}"
    cached = scraper_cache.get(key)
    if cached is not None:
        return cached

    url = f"https://codeforces.com/contest/{contest_id}/problem/{index.upper()}"
    async with AsyncSession(impersonate="chrome124", timeout=15) as session:
        response = await session.get(url)
        if response.status_code != 200:
            raise RuntimeError(f"Failed to fetch problem page (HTTP {response.status_code})")
        parsed = await asyncio.to_thread(_parse_problem_html, response.text, contest_id, index)
        scraper_cache.set(key, parsed)
        return parsed