# Event Contracts

Single source of truth for the Kafka event bus (architecture Section 15).

## Layout

```text
contracts/
  pyproject.toml
  __init__.py
  events/
    __init__.py
    base.py            - BaseEvent envelope + EventSource
    schemas.py         - typed payload models (BlockRequestPayload, ...)
    events.py          - concrete event classes + EVENT_REGISTRY + make_event()
    topics.py          - Kafka topic names + EVENT_TOPIC_MAP
    json_schemas/      - JSON Schema (draft 2020-12) per event type, v1
      block_request.submitted.v1.json
      block_request.updated.v1.json
      optimization.requested.v1.json
      optimization.result.v1.json
      track.status_changed.v1.json
      train.delay.v1.json
```

## Event envelope

Every event carries: `event_id`, `event_type`, `event_version`, `occurred_at`,
`source` (internal/external), `producer`, `entity_type`, `entity_id`,
`correlation_id`, and a typed `payload`. This mirrors the `events` table in
`docs/database_schema.md` (Section 11) so events persist verbatim.

## Using the contracts (Python)

```python
from datetime import datetime, timezone
from contracts.events import BlockRequestSubmitted, make_event

event = make_event(
    BlockRequestSubmitted,
    payload={
        "department_id": "...",
        "requested_by_user_id": "...",
        "request_type": "operational",
        "track_id": "...",
        "requested_start": "2026-09-10T06:00:00Z",
        "requested_end": "2026-09-10T08:00:00Z",
        "operational": {"reason": "TRACK_MAINTENANCE"},
    },
    occurred_at=datetime.now(timezone.utc),
)
event.model_dump_json()  # serialize to publish
```

## Versioning & compatibility

- Schemas are versioned (`event_version`, and `.v1.json` file suffix).
- Changes must be backward-compatible where possible (architecture item 332):
  add optional fields, never remove or retype required ones. Bump the version
  and add a new `.vN.json` file for breaking changes.
- Consumers must not depend on undocumented fields (item 331).

## Note on generation

The JSON Schema files are hand-written to match the Pydantic models in
`schemas.py`/`events.py` (Pydantic is not installed in the authoring
environment). When a service installs `pydantic`, the schemas can be
regenerated with `model.model_json_schema()` and diffed against these files to
catch drift.
