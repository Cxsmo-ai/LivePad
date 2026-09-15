"""Newline-delimited JSON messages for the HIDMaestro bridge."""

import json
from typing import Any

from controller.state import ControllerState


def encode_message(message: dict[str, Any]) -> bytes:
    # Field insertion order is already deterministic for our protocol. Avoid
    # sorting every tiny frame because this runs on the low-latency hot path.
    return (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")


def encode_state(state: ControllerState, sequence: int) -> bytes:
    return encode_message(state.to_wire(sequence))


def decode_message(line: bytes | str) -> dict[str, Any]:
    if isinstance(line, bytes):
        line = line.decode("utf-8")
    message = json.loads(line)
    if not isinstance(message, dict) or not isinstance(message.get("type"), str):
        raise ValueError("bridge message must be a JSON object with a string type")
    return message
