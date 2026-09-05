from __future__ import annotations

import json
from typing import Any
from uuid import uuid4


PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 64 * 1024
ALLOWED_TYPES = {
    "ping", "status", "dashboard", "graph", "user_input",
    "voice_start", "voice_status", "voice_stop",
    "voice_precision_start", "voice_precision_status", "voice_precision_stop",
    "settings_get", "settings_save", "sync_now", "diagnostics", "shutdown",
}


class ProtocolError(ValueError):
    pass


def decode_message(raw: bytes | str) -> dict[str, Any]:
    if isinstance(raw, bytes):
        if len(raw) > MAX_MESSAGE_BYTES:
            raise ProtocolError("Mensagem excede 64 KiB.")
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ProtocolError("Mensagem não está em UTF-8.") from exc
    try:
        message = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ProtocolError("JSON inválido.") from exc
    if not isinstance(message, dict):
        raise ProtocolError("A mensagem deve ser um objeto JSON.")
    if message.get("protocol") != PROTOCOL_VERSION:
        raise ProtocolError(f"Protocolo incompatível; esperado {PROTOCOL_VERSION}.")
    type_ = message.get("type")
    if not isinstance(type_, str) or type_ not in ALLOWED_TYPES:
        raise ProtocolError("Tipo de mensagem ausente ou não permitido.")
    request_id = message.get("request_id")
    if not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 128:
        raise ProtocolError("request_id inválido.")
    payload = message.get("payload", {})
    if not isinstance(payload, dict):
        raise ProtocolError("payload deve ser um objeto JSON.")
    return {"protocol": PROTOCOL_VERSION, "type": type_, "request_id": request_id, "payload": payload}


def encode_message(message: dict[str, Any]) -> bytes:
    raw = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    if len(raw) > MAX_MESSAGE_BYTES:
        raise ProtocolError("Resposta excede 64 KiB.")
    return raw


def request(type_: str, payload: dict[str, Any] | None = None, request_id: str | None = None) -> dict[str, Any]:
    return {"protocol": PROTOCOL_VERSION, "type": type_, "request_id": request_id or str(uuid4()), "payload": payload or {}}


def response(source: dict[str, Any], type_: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"protocol": PROTOCOL_VERSION, "type": type_, "request_id": source["request_id"], "payload": payload or {}}
