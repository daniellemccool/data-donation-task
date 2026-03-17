import logging
import traceback
import json
import datetime
from collections import deque
from collections.abc import Generator

from port.api.commands import CommandSystemExit, CommandUIRender, CommandSystemDonate
from port.api.file_utils import AsyncFileAdapter
from port.api.logging import LogForwardingHandler
from port.script import process
import port.api.props as props


def error_flow(platform: str | None, tb: str):
    """
    Generator that handles a Python exception in the donation flow.

    Yields an error consent page, then optionally donates the error log
    if the participant consents.

    Args:
        platform: Name of the active platform when the error occurred.
        tb: Full traceback string from traceback.format_exc().
    """
    header = props.PropsUIHeader(
        props.Translatable({"nl": "Er is iets misgegaan", "en": "Something went wrong"})
    )
    body = [
        props.PropsUIPromptText(text=props.Translatable({"nl": tb, "en": tb})),
        props.PropsUIPromptConfirm(
            text=props.Translatable({
                "nl": "Wilt u de fout rapporteren zodat we het probleem kunnen oplossen?",
                "en": "Would you like to report this error so we can fix the problem?",
            }),
            ok=props.Translatable({"nl": "Fout rapporteren", "en": "Report error"}),
            cancel=props.Translatable({"nl": "Overslaan", "en": "Skip"}),
        ),
    ]
    page = props.PropsUIPageDataSubmission(platform or "error", header, body)
    consent_result = yield CommandUIRender(page)

    if consent_result is not None and getattr(consent_result, "__type__", None) == "PayloadTrue":
        error_data = json.dumps({
            "platform": platform,
            "traceback": tb,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })
        yield CommandSystemDonate("error-report", error_data)


class ScriptWrapper(Generator):
    def __init__(self, script, platform: str | None = None):
        self.script = script
        self.platform = platform or "unknown"
        self._error_handler = None
        self.queue: deque = deque()

    def add_log_handler(self, logger_name: str = "port") -> None:
        """Attach a handler to the named logger that forwards log records as CommandSystemLog commands."""
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        handler = LogForwardingHandler(self.queue)
        handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
        logger.addHandler(handler)

    def send(self, data):
        # If log commands are queued, discard incoming response
        # because it is the PayloadVoid response to a previous log.
        if self.queue:
            return self.queue.popleft()

        if self._error_handler is not None:
            try:
                command = self._error_handler.send(data)
                return command.toDict()
            except StopIteration:
                return CommandSystemExit(0, "End of script").toDict()

        # Automatically wrap JS file readers with AsyncFileAdapter
        if data and getattr(data, "__type__", None) == "PayloadFile":
            data.value = AsyncFileAdapter(data.value)

        try:
            command = self.script.send(data)
            # If the script yields None (e.g. bare `yield` used as a checkpoint),
            # continue the generator immediately with None so the next step runs.
            while command is None:
                command = self.script.send(None)
        except StopIteration:
            return CommandSystemExit(0, "End of script").toDict()
        except Exception:
            tb = traceback.format_exc()
            self._error_handler = error_flow(self.platform, tb)
            command = next(self._error_handler)
            return command.toDict()

        # Append the script command AFTER any log commands already in the queue.
        # This preserves log-before-command ordering.
        self.queue.append(command.toDict())
        return self.queue.popleft()

    def throw(self, _type=None, _value=None, _traceback=None):
        raise StopIteration


def start(sessionId, platform=None):
    script = process(sessionId, platform)
    wrapper = ScriptWrapper(script, platform=platform)
    wrapper.add_log_handler()
    return wrapper
