"""
Tests for the log queue integration in ScriptWrapper.
Verifies that log commands emitted during script execution are interleaved
correctly and that error handling still works with the queue.

Design note: `add_log_handler()` attaches a handler to a global logger
(`logging.getLogger("port.bridge")`). Each test that calls `add_log_handler()`
must clean up that handler afterwards. The `clean_port_script_logger` autouse
fixture handles this.

Protocol assumption: when the JS engine receives a `CommandSystemLog`, it
calls `bridge.send(command)` (fire-and-forget) then sends back `PayloadVoid`
as the response. `ScriptWrapper.send()` drains the queue on the next call by
discarding that `PayloadVoid` response and returning the next queued item.
This matches `command_router.ts` (onCommandSystem else-branch returns PayloadVoid).
"""
import sys
import logging
import pytest
from unittest.mock import MagicMock

sys.modules['js'] = MagicMock()

from port.main import ScriptWrapper
from port.api.commands import CommandUIRender
from port.api.props import PropsUIPageEnd


@pytest.fixture(autouse=True)
def clean_port_script_logger():
    """Remove any LogForwardingHandler added during a test to prevent handler accumulation."""
    logger = logging.getLogger("port.bridge")
    handlers_before = list(logger.handlers)
    yield
    logger.handlers = handlers_before


def test_log_commands_returned_before_script_command():
    """Log commands queued during script.send() are returned before the script command."""
    logger = logging.getLogger("port.bridge")

    def script_with_logging():
        logger.info("step one")
        logger.info("step two")
        yield CommandUIRender(PropsUIPageEnd())

    wrapper = ScriptWrapper(script_with_logging())
    wrapper.add_log_handler()

    # First send: runs the script, which emits two logs then yields CommandUIRender.
    # Queue after send: [log1, log2, CommandUIRender]. Returns log1.
    result1 = wrapper.send(None)
    assert result1["__type__"] == "CommandSystemLog"
    assert result1["message"] == "port.bridge: step one"

    # PayloadVoid is the response to the log command — discarded by queue-drain guard.
    result2 = wrapper.send({"__type__": "PayloadVoid", "value": None})
    assert result2["__type__"] == "CommandSystemLog"
    assert result2["message"] == "port.bridge: step two"

    # Queue still holds CommandUIRender from the first cycle.
    result3 = wrapper.send({"__type__": "PayloadVoid", "value": None})
    assert result3["__type__"] == "CommandUIRender"


def test_no_logs_returns_script_command_directly():
    """Without any log calls, ScriptWrapper returns the script command directly."""
    def simple_script():
        yield CommandUIRender(PropsUIPageEnd())

    wrapper = ScriptWrapper(simple_script())
    wrapper.add_log_handler()

    result = wrapper.send(None)
    assert result["__type__"] == "CommandUIRender"


def test_add_log_handler_wires_logger():
    """add_log_handler attaches a handler to the port logger."""
    logger = logging.getLogger("port.bridge")
    initial_handler_count = len(logger.handlers)

    def simple():
        yield CommandUIRender(PropsUIPageEnd())

    wrapper = ScriptWrapper(simple())
    wrapper.add_log_handler()

    assert len(logger.handlers) == initial_handler_count + 1
    # Cleanup handled by autouse fixture


def test_error_handler_still_works_with_queue():
    """Error handling still works correctly even with the queue system present."""
    def crashing():
        data = yield
        raise RuntimeError("queue test explosion")

    wrapper = ScriptWrapper(crashing(), platform="X")
    wrapper.add_log_handler()
    result = wrapper.send(None)

    assert result["__type__"] == "CommandUIRender"
    page = result["page"]
    assert page["__type__"] == "PropsUIPageDataSubmission"


def test_log_command_flow_integration():
    """Integration test: Python log → CommandSystemLog → then script command, full cycle."""
    logger = logging.getLogger("port.bridge")

    def script():
        logger.info("hello")
        yield CommandUIRender(PropsUIPageEnd())

    wrapper = ScriptWrapper(script())
    wrapper.add_log_handler()

    first = wrapper.send(None)
    assert first["__type__"] == "CommandSystemLog"
    assert first["message"] == "port.bridge: hello"

    second = wrapper.send({"__type__": "PayloadVoid", "value": None})
    assert second["__type__"] == "CommandUIRender"


def test_start_function_creates_wrapper_with_log_handler(monkeypatch):
    """start() returns a ScriptWrapper with the log handler attached."""
    def fake_process(session_id, platform):
        return iter([])

    monkeypatch.setattr("port.main.process", fake_process)

    from port.main import start
    wrapper = start("session123", "LinkedIn")
    assert isinstance(wrapper, ScriptWrapper)
    logger = logging.getLogger("port.bridge")
    handler_types = [type(h).__name__ for h in logger.handlers]
    assert "LogForwardingHandler" in handler_types
    # Cleanup handled by autouse fixture
