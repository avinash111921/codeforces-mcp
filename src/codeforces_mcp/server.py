from typing import Any
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from .client import CodeforcesClient
from .scraper import fetch_problem_statement
from .sandbox import run_samples, run_stress_test

mcp = MCPServer("Codeforces-MCP")
cf_client = CodeforcesClient()

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
LOCAL_EXEC = ToolAnnotations(readOnlyHint=False, destructiveHint=False)


@mcp.tool(annotations=READ_ONLY)
async def get_user_profile(handle: str) -> dict[str, Any]:
    """Fetch a Codeforces user's current rating, max rating, rank, and recent verdict breakdown."""
    info = await cf_client.get_user_info(handle)
    submissions = await cf_client.get_user_submissions(handle, count=100)

    verdicts: dict[str, int] = {}
    weak_tags: dict[str, int] = {}

    for sub in submissions:
        v = sub.get("verdict", "UNKNOWN")
        verdicts[v] = verdicts.get(v, 0) + 1
        if v != "OK":
            for tag in sub.get("problem", {}).get("tags", []):
                weak_tags[tag] = weak_tags.get(tag, 0) + 1

    top_weak_tags = sorted(weak_tags.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "handle": info.get("handle"),
        "rating": info.get("rating", "Unrated"),
        "maxRating": info.get("maxRating", "Unrated"),
        "rank": info.get("rank", "Unrated"),
        "recent_100_verdicts": verdicts,
        "most_failed_tags_recently": [t[0] for t in top_weak_tags],
    }


@mcp.tool(annotations=READ_ONLY)
async def get_problem(contest_id: int, index: str) -> dict[str, Any]:
    """Fetch the full problem statement, constraints, and sample test cases for a Codeforces problem."""
    return await fetch_problem_statement(contest_id, index)


@mcp.tool(annotations=READ_ONLY)
async def recommend_upsolve_problems(
    handle: str,
    tag: str | None = None,
    min_rating: int = 1600,
    max_rating: int = 1900,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Recommend unsolved Codeforces problems filtered by rating range and optional topic tag."""
    subs = await cf_client.get_user_submissions(handle, count=500)
    solved = {
        f"{s['problem'].get('contestId')}{s['problem'].get('index')}"
        for s in subs
        if s.get("verdict") == "OK" and "problem" in s
    }

    catalog = await cf_client.get_problemset()
    recommendations = []

    for prob in catalog.get("problems", []):
        pid = f"{prob.get('contestId')}{prob.get('index')}"
        rating = prob.get("rating", 0)
        tags = prob.get("tags", [])

        if pid in solved or not (min_rating <= rating <= max_rating):
            continue
        if tag and tag.lower() not in [t.lower() for t in tags]:
            continue

        recommendations.append({
            "problem_id": pid,
            "name": prob.get("name"),
            "rating": rating,
            "tags": tags,
            "url": f"https://codeforces.com/contest/{prob.get('contestId')}/problem/{prob.get('index')}",
        })
        if len(recommendations) >= limit:
            break

    return recommendations


@mcp.tool(annotations=LOCAL_EXEC)
async def test_local_solution(source_file: str, contest_id: int, index: str) -> dict[str, Any]:
    """Compile and run a local .cpp or .py file against official Codeforces sample test cases."""
    problem = await fetch_problem_statement(contest_id, index)
    return run_samples(source_file, problem["samples"])


@mcp.tool(annotations=LOCAL_EXEC)
async def find_counterexample(
    optimal_file: str,
    brute_file: str,
    generator_file: str,
    iterations: int = 100,
) -> dict[str, Any]:
    """Stress test an optimal solution against a brute-force solution using a generator script."""
    return run_stress_test(optimal_file, brute_file, generator_file, iterations)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()