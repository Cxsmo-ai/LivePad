import time

from chat.normalized_event import ChatEvent
from chat.processor import ChatCommandProcessor
from controller.state_engine import StateEngine


def test_thousand_viewers_are_processed_without_queueing_or_crashing():
    processor = ChatCommandProcessor(StateEngine())
    start = time.perf_counter()
    for index in range(1000):
        result = processor.process(ChatEvent(f"viewer-{index}", str(index), "w sprint ads fire right 35", time.monotonic_ns()))
        assert len(result.accepted) == 5
    elapsed = time.perf_counter() - start
    assert elapsed < 1.0
