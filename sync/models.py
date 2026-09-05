from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
from pathlib import Path
import re
from uuid import uuid4


def now_iso() -> str: return datetime.now().astimezone().isoformat(timespec="microseconds")


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


@dataclass(slots=True)
class DeviceIdentity:
    device_id: str
    name: str

    @classmethod
    def load_or_create(cls, path: str | Path, name: str = "") -> "DeviceIdentity":
        target = Path(path)
        if target.is_file():
            raw = json.loads(target.read_text(encoding="utf-8"))
            return cls(str(raw["device_id"]), str(raw.get("name", "device")))
        safe = re.sub(r"[^a-z0-9-]+", "-", name.casefold()).strip("-") or "device"
        identity = cls(f"{safe}-{uuid4()}", name or "device")
        atomic_json(target, asdict(identity))
        return identity


@dataclass(slots=True)
class SyncEvent:
    schema: int
    event_id: str
    device_id: str
    timestamp: str
    entity: str
    entity_id: str
    action: str
    payload: dict = field(default_factory=dict)
    base_event_id: str | None = None

    @classmethod
    def create(cls, device_id: str, entity: str, entity_id: str, action: str,
               payload: dict, base_event_id: str | None = None) -> "SyncEvent":
        return cls(1, str(uuid4()), device_id, now_iso(), entity, entity_id, action, payload, base_event_id)

    @classmethod
    def from_dict(cls, raw: dict) -> "SyncEvent":
        if raw.get("schema") != 1:
            raise ValueError("Schema de sincronização incompatível.")
        if raw.get("entity") not in {"task", "reminder", "automation", "shopping_item", "project", "preference"}:
            raise ValueError("Entidade de sincronização não permitida.")
        if raw.get("action") not in {"create", "update", "complete", "delete"}:
            raise ValueError("Ação de sincronização não permitida.")
        required = ("event_id", "device_id", "timestamp", "entity_id")
        if any(not isinstance(raw.get(key), str) or not raw[key] for key in required):
            raise ValueError("Evento de sincronização incompleto.")
        if not isinstance(raw.get("payload"), dict):
            raise ValueError("Payload de sincronização inválido.")
        return cls(**{key: raw.get(key) for key in cls.__dataclass_fields__})

    def as_dict(self) -> dict: return asdict(self)


@dataclass(slots=True)
class ConflictRecord:
    conflict_id: str
    entity: str
    entity_id: str
    local_event_id: str
    incoming_event_id: str
    local_payload: dict
    incoming_payload: dict
    created_at: str = field(default_factory=now_iso)
    status: str = "open"
