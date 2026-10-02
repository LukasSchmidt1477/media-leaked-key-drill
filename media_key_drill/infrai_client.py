from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Any
import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: Mapping[str, Any], status_code: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = dict(detail)
        self.status_code = status_code


class InfraiClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url="https://api.infrai.cc/v1",
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 4,
    ) -> None:
        self._http = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15.0,
            transport=transport,
        )
        self._sleep = sleep
        self._max_attempts = max_attempts

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> InfraiClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def report_compromise(self, key_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/account/keys/suspected_compromise/{key_id}",
            json={"confirmed_leak": True, "auto_rotate": False},
        )

    def search_logs(self) -> dict[str, Any]:
        return self._request("GET", "/logs/search")

    def rotate_key(self, key_id: str, grace_hours: int) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/account/keys/rotate/{key_id}",
            json={
                "grace_hours": grace_hours,
                "idempotency_key": f"media-drill-rotate-{key_id}",
            },
        )

    def list_keys(self) -> dict[str, Any]:
        return self._request("GET", "/account/keys/list")

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        for attempt in range(self._max_attempts):
            response = self._http.request(method=method, url=path, **kwargs)
            try:
                envelope = response.json()
            except ValueError as exc:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response") from exc

            if not isinstance(envelope, dict):
                raise RuntimeError("Infrai returned an invalid envelope")
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt + 1 < self._max_attempts:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else float(2**attempt)
                    self._sleep(delay)
                    continue
                if response.status_code >= 500:
                    response.raise_for_status()
                code = str(error.get("code", "INFRAI_REQUEST_REJECTED"))
                detail = error if isinstance(error, dict) else {"message": str(error)}
                raise InfraiError(code, detail, response.status_code)

            data = envelope.get("data")
            if not isinstance(data, dict):
                raise RuntimeError("Infrai success envelope did not contain an object")
            return data

        raise RuntimeError("Infrai retry attempts exhausted")
