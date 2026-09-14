import os

import pytest

from chat_gamepad_app import _acquire_single_instance, _release_single_instance


@pytest.mark.skipif(os.name != "nt", reason="Windows named mutex")
def test_single_instance_mutex_blocks_duplicate_and_releases():
    first = _acquire_single_instance()
    assert first is not None
    try:
        assert _acquire_single_instance() is None
    finally:
        _release_single_instance(first)

    replacement = _acquire_single_instance()
    assert replacement is not None
    _release_single_instance(replacement)
