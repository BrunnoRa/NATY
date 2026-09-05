"""IPC versionado entre o Core Python e o Desktop Windows."""

from ipc.protocol import PROTOCOL_VERSION, ProtocolError, decode_message, encode_message, response

__all__ = ["PROTOCOL_VERSION", "ProtocolError", "decode_message", "encode_message", "response"]
