import os
from pathlib import Path
import sys

import pytest

from chat_gamepad_app import _acquire_single_instance, _config_root, _release_single_instance


@pytest.mark.skipif(os.name != "nt", reason="Windows named mutex")
def test_single_instance_mutex_blocks_duplicate_and_releases():
    name = r"LocalTikForeverChatGamepad.UnitTest"
    first = _acquire_single_instance(name)
    assert first is not None
    try:
        assert _acquire_single_instance(name) is None
    finally:
        _release_single_instance(first)

    replacement = _acquire_single_instance(name)
    assert replacement is not None
    _release_single_instance(replacement)


def test_frozen_app_keeps_runtime_files_out_of_exe_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert _config_root() == Path(tmp_path) / "HIDMaestroStreamerEdition"
