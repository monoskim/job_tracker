# job_tracker

Daily Python workflow that uses SerpApi to search Google for fresh job postings matching data-focused queries.

## What it does

- Runs a Google search through SerpApi.
- Applies Google's last-24-hours freshness filter with `tbs=qdr:d`.
- Runs multiple site-specific queries (Greenhouse, Ashby, Lever).
- Writes a JSON export and a Markdown report to `output/`.
- Supports running locally or on a daily GitHub Actions schedule.

## Default queries

```text
site:boards.greenhouse.io/ ("first data" OR "founding data" OR "analytics engineer" OR "data engineer") (Snowflake OR dbt OR Airflow) -"Power BI" -"PowerBI"
site:jobs.ashbyhq.com/ ("first data" OR "founding data" OR "analytics engineer" OR "data engineer") (Snowflake OR dbt OR Airflow) -"Power BI" -"PowerBI"
site:jobs.lever.co/ ("first data" OR "founding data" OR "analytics engineer" OR "data engineer") (Snowflake OR dbt OR Airflow) -"Power BI" -"PowerBI"
```

## Local setup

1. Create a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and set `SERPAPI_API_KEY`.
4. Run `python search_jobs.py`.

The script writes:

- `output/latest_jobs.json`
- `output/latest_jobs.md`

## GitHub Actions setup

The workflow is defined in `.github/workflows/daily-job-search.yml` and supports both manual runs and scheduled runs.

Configure these repository settings:

- Repository secret: `SERPAPI_API_KEY`
- Optional repository variable: `JOB_QUERY`
- Optional repository variable: `JOB_QUERIES` (preferred for multiple queries; separate queries with `||`)
- Optional repository variable: `JOB_SEARCH_GL`
- Optional repository variable: `JOB_SEARCH_HL`

`JOB_QUERIES` takes precedence over `JOB_QUERY`. If neither is provided, the three default queries above are used.

The workflow is set up to execute at 8:00 AM Pacific year-round. Because GitHub cron is UTC-based, it uses `0 16 * * *` and `0 17 * * *` plus a Pacific-time gate step so only the true 8:00 AM PT scheduled run continues. Manual `workflow_dispatch` runs bypass the time gate so you can test anytime.

Each run publishes:

- A job summary in the GitHub Actions run summary
- The generated `output/` files as an artifact