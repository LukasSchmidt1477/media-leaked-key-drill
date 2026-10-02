from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from .drill_service import DrillRequest, DrillResult, run_leaked_key_drill
from .infrai_client import InfraiClient, InfraiError

service = FastAPI(title="Media leaked-key drill")


@service.post("/drills/leaked-key", response_model=DrillResult)
def leaked_key_drill(request: DrillRequest) -> DrillResult:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is required")

    try:
        with InfraiClient(api_key) as client:
            return run_leaked_key_drill(client, request)
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=client_status, detail=exc.detail) from exc

