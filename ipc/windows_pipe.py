from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import os
import threading

from ipc.handler import CoreRequestHandler
from ipc.protocol import MAX_MESSAGE_BYTES, ProtocolError, decode_message, encode_message


PIPE_ACCESS_DUPLEX = 0x00000003
PIPE_TYPE_BYTE = 0x00000000
PIPE_READMODE_BYTE = 0x00000000
PIPE_WAIT = 0x00000000
ERROR_PIPE_CONNECTED = 535
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class WindowsNamedPipeServer:
    def __init__(self, pipe_name: str, handler: CoreRequestHandler, logger: logging.Logger | None = None):
        if os.name != "nt":
            raise RuntimeError("Windows Named Pipes requer Windows.")
        if not pipe_name or any(char in pipe_name for char in "\\/:"):
            raise ValueError("Nome de pipe inválido.")
        self.path = rf"\\.\pipe\{pipe_name}"
        self.handler = handler
        self.logger = logger or logging.getLogger("naty.ipc")
        self._stopped = threading.Event()
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._configure_api()

    def _configure_api(self) -> None:
        self.kernel32.CreateNamedPipeW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                                                   wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID]
        self.kernel32.CreateNamedPipeW.restype = wintypes.HANDLE
        self.kernel32.ConnectNamedPipe.argtypes = [wintypes.HANDLE, wintypes.LPVOID]
        self.kernel32.ConnectNamedPipe.restype = wintypes.BOOL
        self.kernel32.ReadFile.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
        self.kernel32.ReadFile.restype = wintypes.BOOL
        self.kernel32.WriteFile.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
        self.kernel32.WriteFile.restype = wintypes.BOOL

    def _new_pipe(self):
        handle = self.kernel32.CreateNamedPipeW(self.path, PIPE_ACCESS_DUPLEX,
            PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT, 1, MAX_MESSAGE_BYTES, MAX_MESSAGE_BYTES, 5000, None)
        if handle == INVALID_HANDLE_VALUE:
            raise ctypes.WinError(ctypes.get_last_error())
        return handle

    def _read_line(self, handle) -> bytes:
        data = bytearray()
        buffer = ctypes.create_string_buffer(4096)
        while len(data) <= MAX_MESSAGE_BYTES:
            read = wintypes.DWORD()
            ok = self.kernel32.ReadFile(handle, buffer, len(buffer), ctypes.byref(read), None)
            if not ok or read.value == 0:
                break
            data.extend(buffer.raw[:read.value])
            if b"\n" in data:
                return bytes(data.split(b"\n", 1)[0])
        if len(data) > MAX_MESSAGE_BYTES:
            raise ProtocolError("Mensagem excede 64 KiB.")
        return bytes(data)

    def _write(self, handle, data: bytes) -> None:
        written = wintypes.DWORD()
        if not self.kernel32.WriteFile(handle, data, len(data), ctypes.byref(written), None) or written.value != len(data):
            raise ctypes.WinError(ctypes.get_last_error())

    def serve_forever(self) -> None:
        while not self._stopped.is_set() and not self.handler.shutdown_requested:
            handle = self._new_pipe()
            try:
                connected = self.kernel32.ConnectNamedPipe(handle, None)
                if not connected and ctypes.get_last_error() != ERROR_PIPE_CONNECTED:
                    continue
                raw = self._read_line(handle)
                if not raw:
                    continue
                try:
                    message = decode_message(raw)
                    outgoing = self.handler.handle(message)
                except ProtocolError as exc:
                    request_id = "invalid"
                    try: request_id = decode_message(raw).get("request_id", "invalid")
                    except ProtocolError: pass
                    outgoing = {"protocol": 1, "type": "error", "request_id": request_id,
                                "payload": {"code": "invalid_request", "message": str(exc)}}
                except Exception as exc:
                    self.logger.exception("Falha no request IPC")
                    outgoing = {"protocol": 1, "type": "error", "request_id": "internal",
                                "payload": {"code": "internal_error", "message": "O Core não conseguiu concluir o pedido."}}
                self._write(handle, encode_message(outgoing))
            finally:
                self.kernel32.FlushFileBuffers(handle)
                self.kernel32.DisconnectNamedPipe(handle)
                self.kernel32.CloseHandle(handle)

    def stop(self) -> None:
        self._stopped.set()
