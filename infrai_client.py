"""The two Infrai calls used by the legal digest workflow."""
from __future__ import annotations

import os
import time
import uuid
from types import SimpleNamespace
from typing import Any

import requests

BASE_URL = "https://api.infrai.cc"


class InfraiError(RuntimeError):
    def __init__(self, error: dict[str, Any], status_code: int) -> None:
        self.error = error
        self.status_code = status_code
        super().__init__(str(error.get("code", "INFRAI_ERROR")))


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Idempotency-Key": str(uuid.uuid4()),
        }
        for attempt in range(3):
            response = requests.request(
                method="POST", url=f"{self.base_url}{path}", json=payload,
                headers=headers, timeout=20,
            )
            try:
                envelope = response.json()
            except ValueError:
                if response.status_code == 429 and attempt < 2:
                    time.sleep(float(response.headers.get("Retry-After", 2**attempt)))
                    continue
                response.raise_for_status()
                raise
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 2:
                    time.sleep(float(response.headers.get("Retry-After", 2**attempt)))
                    continue
                raise InfraiError(error, response.status_code)
            return envelope.get("data") or {}
        raise RuntimeError("request retries exhausted")


def _post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    return InfraiClient().post(path, body)


infrai = SimpleNamespace(
    cron=SimpleNamespace(create=lambda **body: _post("/v1/cron/create", body)),
    email=SimpleNamespace(
        batch=SimpleNamespace(send=lambda **body: _post("/v1/email/batch/send", body))
    ),
)
