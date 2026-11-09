"""Register the weekday trigger for the FastAPI digest endpoint."""
from __future__ import annotations

import os

from infrai_client import infrai


def register_weekday_digest(task_url: str) -> str:
    job = infrai.cron.create(cron_expr="0 8 * * 1-5", task=task_url)
    return str(job["job_id"])


if __name__ == "__main__":
    task_url = os.environ["DIGEST_TASK_URL"]
    print(f"scheduled legal digest: {register_weekday_digest(task_url)}")
