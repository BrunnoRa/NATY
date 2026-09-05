from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import re
import threading
from typing import Callable
from uuid import uuid4

from sync.models import DeviceIdentity, SyncEvent, atomic_json, now_iso
from sync.state import SyncStateRepository


class SyncManager:
    def __init__(self, db, shared_folder: str | Path, identity: DeviceIdentity, interval_seconds: int = 30,
                 on_applied: Callable[[], None] | None = None):
        self.db, self.root, self.identity = db, Path(shared_folder), identity
        self.events = self.root / "events"
        self.snapshots = self.root / "snapshots"
        self.conflict_dir = self.root / "conflicts"
        self.device_state = self.root / "device_state"
        self.state = SyncStateRepository(db)
        self.interval_seconds = max(2, interval_seconds)
        self.on_applied = on_applied
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.status = "offline"
        self.last_sync: str | None = None

    def _ensure_folders(self) -> None:
        for folder in (self.events, self.snapshots, self.conflict_dir, self.device_state):
            folder.mkdir(parents=True, exist_ok=True)

    def record(self, entity: str, local_id: str | int, action: str, payload: dict) -> SyncEvent:
        self._ensure_folders()
        sync_id = self.state.sync_id(entity, str(local_id)) or str(uuid4())
        self.state.map(entity, sync_id, str(local_id))
        current = self.state.state(entity, sync_id)
        event = SyncEvent.create(self.identity.device_id, entity, sync_id, action, payload,
                                 current["last_event_id"] if current else None)
        atomic_json(self.events / f"{event.timestamp.replace(':','-')}_{event.event_id}.json", event.as_dict())
        self.state.mark_applied(event.event_id); self.state.set_state(event, action == "delete")
        return event

    def sync_now(self) -> dict:
        self.status = "syncing"
        applied = conflicts = 0
        self._ensure_folders()
        for path in sorted(self.events.glob("*.json")):
            try:
                event = SyncEvent.from_dict(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if self.state.applied(event.event_id):
                continue
            current = self.state.state(event.entity, event.entity_id)
            concurrent = bool(current and event.action != "create" and current["last_event_id"] != event.base_event_id
                              and current["last_device_id"] != event.device_id)
            if concurrent:
                conflict = self.state.add_conflict(event, current)
                atomic_json(self.conflict_dir / f"{conflict.conflict_id}.json", asdict(conflict))
                self.state.mark_applied(event.event_id)
                conflicts += 1
                continue
            self._apply(event)
            self.state.mark_applied(event.event_id)
            self.state.set_state(event, event.action == "delete")
            applied += 1
        if applied and self.on_applied:
            self.on_applied()
        self.last_sync = now_iso()
        self.status = "conflict" if self.state.conflicts() else "updated"
        atomic_json(self.device_state / f"{self.identity.device_id}.json", {
            "device_id": self.identity.device_id, "last_sync": self.last_sync, "status": self.status,
        })
        return {"status": self.status, "applied": applied, "conflicts": conflicts,
                "pending": 0, "last_sync": self.last_sync, "device_id": self.identity.device_id}

    def _apply(self, event: SyncEvent) -> None:
        local = self.state.local_id(event.entity, event.entity_id)
        if event.action == "delete":
            if local: self._delete(event.entity, local)
            return
        if local:
            self._update(event.entity, local, event.payload, event.action)
        else:
            local = self._create(event.entity, event.payload)
            self.state.map(event.entity, event.entity_id, local)

    def _create(self, entity: str, p: dict) -> str:
        if entity == "task":
            return str(self.db.execute(
                "INSERT INTO tasks(title,description,status,priority,due_at,estimated_minutes) VALUES(?,?,?,?,?,?)",
                (p.get("title", "Tarefa sincronizada"), p.get("description", ""), p.get("status", "pending"),
                 p.get("priority", "normal"), p.get("due_at"), p.get("estimated_minutes"))))
        if entity == "reminder":
            return str(self.db.execute("INSERT INTO reminders(text,remind_at,status) VALUES(?,?,?)",
                (p.get("text", "Lembrete sincronizado"), p.get("remind_at", now_iso()), p.get("status", "pending"))))
        if entity == "project":
            return str(self.db.execute("INSERT INTO projects(name,description,status) VALUES(?,?,?)",
                (p.get("name", f"Projeto {uuid4()}"), p.get("description", ""), p.get("status", "active"))))
        if entity == "preference":
            key = str(p.get("key", uuid4()))
            self.db.execute("INSERT OR REPLACE INTO preferences(key,value) VALUES(?,?)", (key, str(p.get("value", ""))))
            return key
        if entity == "automation":
            return str(self.db.execute(
                "INSERT INTO automation_rules(name,trigger_type,trigger_value,action_type,payload_json,next_run_at,enabled) VALUES(?,?,?,?,?,?,?)",
                (p.get("name", "Automação"), p.get("trigger_type", "schedule"), p.get("trigger_value", ""),
                 p.get("action_type", "notify"), p.get("payload_json", json.dumps(p.get("payload", {}))),
                 p.get("next_run_at"), int(bool(p.get("enabled", True))))))
        if entity == "shopping_item":
            name = p.get("list_name", "Lista de Compras")
            slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-") or "compras"
            row = self.db.one("SELECT id FROM lists WHERE name=? COLLATE NOCASE", (name,))
            list_id = row["id"] if row else self.db.execute("INSERT INTO lists(name,slug) VALUES(?,?)", (name, slug))
            return str(self.db.execute("INSERT INTO list_items(list_id,text,quantity,checked) VALUES(?,?,?,?)",
                (list_id, p.get("text", "Item"), p.get("quantity"), int(bool(p.get("checked"))))))
        raise ValueError("Entidade não suportada.")

    def _update(self, entity: str, local: str, p: dict, action: str) -> None:
        columns = {
            "task": ("tasks", ("title", "description", "status", "priority", "due_at", "estimated_minutes")),
            "reminder": ("reminders", ("text", "remind_at", "status")),
            "project": ("projects", ("name", "description", "status")),
            "shopping_item": ("list_items", ("text", "quantity", "checked")),
        }
        if entity in columns:
            table, allowed = columns[entity]
            changes = [(name, p[name]) for name in allowed if name in p]
            if changes:
                assignments = ",".join(f"{name}=?" for name, _ in changes)
                self.db.execute(f"UPDATE {table} SET {assignments} WHERE id=?",
                                tuple(value for _, value in changes) + (local,))
            if action == "complete":
                column = "checked" if entity == "shopping_item" else "status"
                value = 1 if column == "checked" else "completed"
                self.db.execute(f"UPDATE {table} SET {column}=? WHERE id=?", (value, local))
        elif entity == "preference":
            self.db.execute("UPDATE preferences SET value=? WHERE key=?", (str(p.get("value", "")), local))
        elif entity == "automation":
            changes = [(name, p[name]) for name in ("name", "trigger_value", "next_run_at", "enabled") if name in p]
            if changes:
                assignments = ",".join(f"{name}=?" for name, _ in changes)
                self.db.execute(f"UPDATE automation_rules SET {assignments} WHERE id=?",
                                tuple(value for _, value in changes) + (local,))

    def _delete(self, entity: str, local: str) -> None:
        table={"task":"tasks","reminder":"reminders","automation":"automation_rules","shopping_item":"list_items","project":"projects","preference":"preferences"}[entity]
        key="key" if entity=="preference" else "id"; self.db.execute(f"DELETE FROM {table} WHERE {key}=?",(local,))

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        def loop():
            while not self._stop.is_set():
                try: self.sync_now()
                except (OSError, TimeoutError):
                    self.status = "offline"
                self._stop.wait(self.interval_seconds)
        self._thread=threading.Thread(target=loop,name="NatySync",daemon=True); self._thread.start()
    def stop(self) -> None:
        self._stop.set()
        if self._thread: self._thread.join(timeout=2)
    def summary(self) -> dict:
        return {"status": self.status, "last_sync": self.last_sync, "device_id": self.identity.device_id,
                "conflicts": len(self.state.conflicts()), "pending": 0, "folder": str(self.root)}
