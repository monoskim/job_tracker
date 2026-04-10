from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


SERPAPI_URL = "https://serpapi.com/search.json"
DEFAULT_QUERIES = [
    (
        'site:boards.greenhouse.io/ ("first data" OR "founding data" OR '
        '"analytics engineer" OR "data engineer") '
        '(Snowflake OR dbt OR Airflow) -"Power BI" -"PowerBI"'
    ),
    (
        'site:jobs.ashbyhq.com/ ("first data" OR "founding data" OR '
        '"analytics engineer" OR "data engineer") '
        '(Snowflake OR dbt OR Airflow) -"Power BI" -"PowerBI"'
    ),
    (
        'site:jobs.lever.co/ ("first data" OR "founding data" OR '
        '"analytics engineer" OR "data engineer") '
        '(Snowflake OR dbt OR Airflow) -"Power BI" -"PowerBI"'
    ),
]
OUTPUT_DIR = Path("output")
JSON_OUTPUT_PATH = OUTPUT_DIR / "latest_jobs.json"
MARKDOWN_OUTPUT_PATH = OUTPUT_DIR / "latest_jobs.md"


@dataclass(slots=True)
class JobResult:
    query: str
    position: int | None
    title: str
    link: str
    snippet: str | None
    displayed_link: str | None
    detected_date: str | None


def load_settings() -> dict[str, Any]:
    load_dotenv()

    api_key = os.getenv("SERPAPI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("SERPAPI_API_KEY is required.")

    queries_raw = os.getenv("JOB_QUERIES", "").strip()
    if queries_raw:
        normalized_queries_raw = queries_raw.replace("||", "\n")
        queries = [line.strip() for line in normalized_queries_raw.splitlines() if line.strip()]
    else:
        single_query = os.getenv("JOB_QUERY", "").strip()
        queries = [single_query] if single_query else list(DEFAULT_QUERIES)

    return {
        "api_key": api_key,
        "queries": queries,
        "gl": os.getenv("JOB_SEARCH_GL", "us").strip() or "us",
        "hl": os.getenv("JOB_SEARCH_HL", "en").strip() or "en",
    }


def fetch_jobs_for_query(settings: dict[str, Any], query: str) -> list[JobResult]:
    params = {
        "engine": "google",
        "q": query,
        "api_key": settings["api_key"],
        "gl": settings["gl"],
        "hl": settings["hl"],
        "num": "100",
        "tbs": "qdr:d",
    }

    response = requests.get(SERPAPI_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    error_message = payload.get("error")
    if error_message:
        raise RuntimeError(f"SerpApi error: {error_message}")

    organic_results = payload.get("organic_results", [])
    jobs: list[JobResult] = []

    for result in organic_results:
        link = (result.get("link") or "").strip()
        if not link:
            continue

        jobs.append(
            JobResult(
                query=query,
                position=result.get("position"),
                title=(result.get("title") or "Untitled result").strip(),
                link=link,
                snippet=(result.get("snippet") or "").strip() or None,
                displayed_link=(result.get("displayed_link") or "").strip() or None,
                detected_date=(result.get("date") or "").strip() or None,
            )
        )

    return jobs


def fetch_jobs(settings: dict[str, Any]) -> list[JobResult]:
    combined_jobs: list[JobResult] = []
    seen_links: set[str] = set()

    for query in settings["queries"]:
        for job in fetch_jobs_for_query(settings, query):
            if job.link in seen_links:
                continue
            seen_links.add(job.link)
            combined_jobs.append(job)

    return combined_jobs


def build_markdown_report(queries: list[str], jobs: list[JobResult], generated_at: str) -> str:
    lines = [
        "# Daily Job Search Report",
        "",
        f"Generated at: {generated_at}",
        "",
        "Queries:",
        "Google freshness filter: results from the last 24 hours (`tbs=qdr:d`).",
        "",
    ]

    for query in queries:
        lines.append(f"- {query}")
    lines.append("")

    if not jobs:
        lines.append("No matching results were returned for the last 24 hours.")
        return "\n".join(lines) + "\n"

    lines.append(f"Found {len(jobs)} matching result(s).")
    lines.append("")

    for index, job in enumerate(jobs, start=1):
        lines.append(f"## {index}. {job.title}")
        lines.append("")
        lines.append(f"- Link: {job.link}")
        lines.append(f"- Matched query: {job.query}")
        if job.displayed_link:
            lines.append(f"- Displayed link: {job.displayed_link}")
        if job.detected_date:
            lines.append(f"- Result date: {job.detected_date}")
        if job.snippet:
            lines.append(f"- Snippet: {job.snippet}")
        lines.append("")

    return "\n".join(lines)


def write_outputs(queries: list[str], jobs: list[JobResult], generated_at: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "generated_at": generated_at,
        "queries": queries,
        "filters": {
            "tbs": "qdr:d",
            "description": "Google last 24 hours filter",
        },
        "result_count": len(jobs),
        "results": [asdict(job) for job in jobs],
    }

    JSON_OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    markdown_report = build_markdown_report(queries, jobs, generated_at)
    MARKDOWN_OUTPUT_PATH.write_text(markdown_report, encoding="utf-8")

    step_summary_path = os.getenv("GITHUB_STEP_SUMMARY", "").strip()
    if step_summary_path:
        Path(step_summary_path).write_text(markdown_report, encoding="utf-8")


def main() -> None:
    settings = load_settings()
    jobs = fetch_jobs(settings)
    generated_at = datetime.now(UTC).isoformat(timespec="seconds")
    write_outputs(settings["queries"], jobs, generated_at)
    print(f"Wrote {len(jobs)} job result(s) to {JSON_OUTPUT_PATH} and {MARKDOWN_OUTPUT_PATH}.")


if __name__ == "__main__":
    main()
