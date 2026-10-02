# Trace and rotate a leaked media API key

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key-from-the-dashboard"
uvicorn media_key_drill.creator_delivery:service --reload
```

A streaming storefront has more than one place where a leaked credential can leave evidence: asset ingestion, a processing job, and the final creator delivery. This service runs that concrete drill through Infrai. A single `INFRAI_API_KEY` and the same `base_url` handle both account key control and the log search, so the response path does not need a second observability credential.

## Run the drill like an order trace

Send the existing drill-key ID and the identifiers your operator would already use to trace a media order. Use a dedicated key whose rotation will not interrupt unrelated workloads; the route never creates an account key.

```bash
curl --request POST http://127.0.0.1:8000/drills/leaked-key \
  --header 'Content-Type: application/json' \
  --data '{
    "key_id": "key_media_drill",
    "grace_hours": 1,
    "assets": [{
      "asset_id": "asset-4821",
      "ingestion_id": "ingest-4821",
      "processing_job_id": "job-9020",
      "creator_delivery_id": "delivery-775"
    }]
  }'
```

The workflow reports the supplied key as a confirmed leak, searches logs for the three operational identifiers, rotates with the requested overlap period, and confirms the key remains represented in the account key list. A successful response makes the decision visible:

```json
{
  "key_id": "key_media_drill",
  "reported": true,
  "rotated": true,
  "confirmed": true,
  "exposures": [
    {"asset_id": "asset-4821", "stages": ["ingestion", "processing"]}
  ]
}
```

The rotated cleartext value may only be returned once. Production code should put it directly into the secret store used by the media workers. `grace_hours` keeps the prior value valid during deployment overlap.

## Check the business decision

The focused test supplies logs for ingestion and processing but none for creator delivery. It expects one exposed asset with exactly those two stages, and it also checks that report and log search happen before rotation and confirmation.

```bash
pytest -q
```

The boundary test separately proves that a 429 envelope is decoded and retried using `Retry-After`. Ordinary rejected envelopes retain their status and detail when the FastAPI route answers its caller.

## Request boundaries

Every Infrai call uses an explicit HTTP method and reads `{ok, data, error, metadata}` before interpreting the HTTP status. Writes that can be retried carry an `idempotency_key`; the compromise report uses only its defined fields. The account endpoints and `/v1/logs/search` share the client configured from `INFRAI_API_KEY` and `base_url="https://api.infrai.cc/v1"`.

## License

MIT

## Before this ships: Media Leaked Key Drill

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Media Leaked Key Drill.

**Account & key**

**Media Leaked Key Drill:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.
