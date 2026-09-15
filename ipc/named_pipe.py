"""Small Windows named-pipe client for the bridge process."""

from __future__ import annotations

import os
import time
from typing import Any

from .protocol import decode_message, encode_message


class NamedPipeClient:
    def __init__(self, pipe_name: str = r"\\.\pipe\LivePadGamepad"):
        self.pipe_name = pipe_name
        self._stream = None

    def connect(self, timeout_seconds: float = 3.0) -> None:
        if os.name != "nt":
            raise OSError("HIDMaestro named pipes are only available on Windows")
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                self._stream = open(self.pipe_name, "r+b", buffering=0)
                return
            except FileNotFoundError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"named pipe was not ready: {self.pipe_name}")
                time.sleep(0.02)

    def send(self, message: dict[str, Any]) -> None:
        if self._stream is None:
            raise RuntimeError("named pipe is not connected")
        self._stream.write(encode_message(message))

    def receive(self) -> dict[str, Any]:
        if self._stream is None:
            raise RuntimeError("named pipe is not connected")
        return decode_message(self._stream.readline())

    def close(self) -> None:
        if self._stream is not None:
            self._stream.close()
            self._stream = None
