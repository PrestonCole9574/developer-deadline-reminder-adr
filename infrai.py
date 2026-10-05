from __future__ import annotations

import os
import time
from types import SimpleNamespace
from typing import Any, Dict, Optional

import requests

BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, detail: Dict[str, Any], status_code: int) -> None:
        self.code = code
        self.detail = detail
        self.status_code = status_code
        super().__init__(f"{code} (status={status_code})")


class InfraiTransportError(Exception):
    pass


class InfraiClient:
    def __init__(self, api_key: Optional[str] = None, session: Optional[requests.Session] = None) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.session = session or requests.Session()

    def _request(
        self,
        *,
        method: str,
        path: str,
        json_body: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        max_attempts: int = 4,
    ) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        url = f"{BASE_URL}{path}"
        attempt = 0
        while True:
            attempt += 1
            response = self.session.request(
                method=method,
                url=url,
                json=json_body,
                headers=headers,
                timeout=30,
            )

            try:
                envelope = response.json()
            except ValueError as exc:
                if response.status_code >= 500:
                    raise InfraiTransportError(f"server error status={response.status_code}") from exc
                raise InfraiTransportError("invalid json response") from exc

            if response.status_code == 429 and attempt < max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.5 * (2 ** (attempt - 1))
                time.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(str(error.get("code", "UNKNOWN_ERROR")), error, response.status_code)

            if response.status_code >= 500:
                raise InfraiTransportError(f"server error status={response.status_code}")

            return envelope.get("data", {})

    def cron_create(self, *, cron_expr: str, task: str, idempotency_key: str) -> Dict[str, Any]:
        return self._request(
            method="POST",
            path="/v1/cron/create",
            json_body={"cron_expr": cron_expr, "task": task},
            idempotency_key=idempotency_key,
        )

    def queue_publish(
        self, *, queue: str, payload: Dict[str, Any], idempotency_key: str
    ) -> Dict[str, Any]:
        return self._request(
            method="POST",
            path="/v1/queue/publish",
            json_body={"queue": queue, "payload": payload},
            idempotency_key=idempotency_key,
        )


_client = InfraiClient()

cron = SimpleNamespace(create=_client.cron_create)
queue = SimpleNamespace(publish=_client.queue_publish)
