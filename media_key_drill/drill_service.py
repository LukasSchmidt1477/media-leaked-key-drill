from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field


class MediaAsset(BaseModel):
    asset_id: str = Field(min_length=1)
    ingestion_id: str = Field(min_length=1)
    processing_job_id: str = Field(min_length=1)
    creator_delivery_id: str = Field(min_length=1)


class DrillRequest(BaseModel):
    key_id: str = Field(min_length=1)
    assets: list[MediaAsset] = Field(min_length=1)
    grace_hours: int = Field(default=1, ge=0, le=24)


class AssetExposure(BaseModel):
    asset_id: str
    stages: list[Literal["ingestion", "processing", "creator_delivery"]]


class DrillResult(BaseModel):
    key_id: str
    reported: bool
    rotated: bool
    confirmed: bool
    exposures: list[AssetExposure]


class DrillClient(Protocol):
    report_compromise: Callable[[str], dict[str, Any]]
    search_logs: Callable[[], dict[str, Any]]
    rotate_key: Callable[[str, int], dict[str, Any]]
    list_keys: Callable[[], dict[str, Any]]


def run_leaked_key_drill(client: DrillClient, request: DrillRequest) -> DrillResult:
    key_id = request.key_id

    client.report_compromise(key_id)
    log_data = client.search_logs()
    exposures = establish_blast_radius(request.assets, log_data)
    client.rotate_key(key_id, request.grace_hours)
    listed = client.list_keys()
    confirmed = _contains_value(listed, key_id)

    return DrillResult(
        key_id=key_id,
        reported=True,
        rotated=True,
        confirmed=confirmed,
        exposures=exposures,
    )


def establish_blast_radius(
    assets: list[MediaAsset], log_data: dict[str, Any]
) -> list[AssetExposure]:
    searchable_logs = json.dumps(log_data, sort_keys=True)
    exposures: list[AssetExposure] = []
    for asset in assets:
        stages: list[Literal["ingestion", "processing", "creator_delivery"]] = []
        if asset.ingestion_id in searchable_logs:
            stages.append("ingestion")
        if asset.processing_job_id in searchable_logs:
            stages.append("processing")
        if asset.creator_delivery_id in searchable_logs:
            stages.append("creator_delivery")
        if stages:
            exposures.append(AssetExposure(asset_id=asset.asset_id, stages=stages))
    return exposures

def _contains_value(value: Any, expected: str) -> bool:
    if isinstance(value, dict):
        return any(_contains_value(item, expected) for item in value.values())
    if isinstance(value, list):
        return any(_contains_value(item, expected) for item in value)
    return value == expected
