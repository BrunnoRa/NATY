from __future__ import annotations

import json
from uuid import uuid4

from sync.models import ConflictRecord


class SyncStateRepository:
    def __init__(self, db):
        self.db = db

    def applied(self, event_id: str) -> bool:
        return self.db.one("SELECT 1 FROM sync_applied_events WHERE event_id=?", (event_id,)) is not None

    def mark_applied(self, event_id: str) -> None:
        self.db.execute("INSERT OR IGNORE INTO sync_applied_events(event_id) VALUES (?)", (event_id,))

    def state(self, entity: str, sync_id: str) -> dict | None:
        row = self.db.one("SELECT * FROM sync_entity_state WHERE entity=? AND sync_id=?", (entity, sync_id))
        return dict(row) if row else None
    def set_state(self, event, tombstone: bool = False) -> None:
        self.db.execute("""INSERT INTO sync_entity_state(entity,sync_id,last_event_id,last_device_id,last_timestamp,payload_json,tombstone)
          VALUES(?,?,?,?,?,?,?) ON CONFLICT(entity,sync_id) DO UPDATE SET last_event_id=excluded.last_event_id,
          last_device_id=excluded.last_device_id,last_timestamp=excluded.last_timestamp,payload_json=excluded.payload_json,tombstone=excluded.tombstone""",
          (event.entity, event.entity_id, event.event_id, event.device_id, event.timestamp,
           json.dumps(event.payload, ensure_ascii=False), int(tombstone)))

    def sync_id(self, entity: str, local_id: str) -> str | None:
        row = self.db.one("SELECT sync_id FROM sync_entity_map WHERE entity=? AND local_id=?", (entity,str(local_id)))
        return str(row["sync_id"]) if row else None
    def local_id(self, entity: str, sync_id: str) -> str | None:
        row = self.db.one("SELECT local_id FROM sync_entity_map WHERE entity=? AND sync_id=?", (entity,sync_id))
        return str(row["local_id"]) if row else None
    def map(self, entity: str, sync_id: str, local_id: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO sync_entity_map(entity,sync_id,local_id) VALUES(?,?,?)", (entity,sync_id,str(local_id)))
    def add_conflict(self, event, current: dict) -> ConflictRecord:
        record = ConflictRecord(str(uuid4()), event.entity, event.entity_id, current["last_event_id"], event.event_id,
            json.loads(current["payload_json"]), event.payload)
        self.db.execute("INSERT INTO sync_conflicts VALUES(?,?,?,?,?,?,?,?,?)", (record.conflict_id,record.entity,record.entity_id,
            record.local_event_id,record.incoming_event_id,json.dumps(record.local_payload,ensure_ascii=False),
            json.dumps(record.incoming_payload,ensure_ascii=False),record.created_at,record.status))
        return record

    def conflicts(self) -> list[dict]:
        return [dict(row) for row in self.db.query("SELECT * FROM sync_conflicts WHERE status='open' ORDER BY created_at")]
