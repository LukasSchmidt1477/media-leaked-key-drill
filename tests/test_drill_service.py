from typing import Any

from media_key_drill.drill_service import DrillRequest, run_leaked_key_drill


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def report_compromise(self, key_id: str) -> dict[str, Any]:
        self.calls.append(f"report:{key_id}")
        return {"reported": True}

    def search_logs(self) -> dict[str, Any]:
        self.calls.append("search")
        return {
            "entries": [
                {"message": "accepted ingest-a"},
                {"message": "completed job-a"},
                {"message": "unrelated activity"},
            ]
        }

    def rotate_key(self, key_id: str, grace_hours: int) -> dict[str, Any]:
        self.calls.append(f"rotate:{key_id}:{grace_hours}")
        return {"id": key_id}

    def list_keys(self) -> dict[str, Any]:
        self.calls.append("confirm")
        return {"keys": [{"id": "key_media_drill"}]}


def test_drill_reports_blast_radius_before_rotation_and_confirmation() -> None:
    client = RecordingClient()
    request = DrillRequest.model_validate(
        {
            "key_id": "key_media_drill",
            "grace_hours": 2,
            "assets": [
                {
                    "asset_id": "asset-a",
                    "ingestion_id": "ingest-a",
                    "processing_job_id": "job-a",
                    "creator_delivery_id": "delivery-a",
                },
                {
                    "asset_id": "asset-b",
                    "ingestion_id": "ingest-b",
                    "processing_job_id": "job-b",
                    "creator_delivery_id": "delivery-b",
                },
            ],
        }
    )

    result = run_leaked_key_drill(client, request)

    assert result.confirmed is True
    assert [item.model_dump() for item in result.exposures] == [
        {"asset_id": "asset-a", "stages": ["ingestion", "processing"]}
    ]
    assert client.calls == [
        "report:key_media_drill",
        "search",
        "rotate:key_media_drill:2",
        "confirm",
    ]
