"""FlowBuilder — shared per-platform donation flow orchestration.

Subclass this to implement a platform-specific donation flow.
Override validate_file() and extract_data(). Call start_flow()
as a generator from script.py via `yield from`.
"""
from abc import abstractmethod
from collections.abc import Generator
import json
import logging

import port.api.props as props
import port.api.d3i_props as d3i_props
import port.helpers.port_helpers as ph
import port.helpers.validate as validate
import port.helpers.uploads as uploads

logger = logging.getLogger(__name__)
bridge_logger = logging.getLogger("port.bridge")


class FlowBuilder:
    def __init__(self, session_id: str, platform_name: str):
        self.session_id = session_id
        self.platform_name = platform_name
        self._initialize_ui_text()

    def _initialize_ui_text(self):
        """Initialize UI text based on platform name."""
        self.UI_TEXT = {
            "submit_file_header": props.Translatable({
                "en": f"Select your {self.platform_name} file",
                "nl": f"Selecteer uw {self.platform_name} bestand",
            }),
            "review_data_header": props.Translatable({
                "en": f"Your {self.platform_name} data",
                "nl": f"Uw {self.platform_name} gegevens",
            }),
            "retry_header": props.Translatable({
                "en": "Try again",
                "nl": "Probeer opnieuw",
            }),
            "review_data_description": props.Translatable({
                "en": f"Below you will find a curated selection of {self.platform_name} data.",
                "nl": f"Hieronder vindt u een zorgvuldig samengestelde selectie van {self.platform_name} gegevens.",
            }),
        }

    def start_flow(self):
        """Main per-platform flow: file→materialize→safety→validate→retry→extract→consent→donate.

        This is a generator. script.py calls it via `yield from flow.start_flow()`.
        Control flow rules:
        - continue: retry upload only
        - break: successful extraction, proceed to consent
        - return: every terminal path

        Bridge logger milestones are PII-free status messages forwarded to mono.
        Local logger keeps full diagnostic detail in browser console only.
        """
        while True:
            # 1. Render file prompt → receive payload
            logger.info("Prompt for file for %s", self.platform_name)
            file_prompt = self.generate_file_prompt()
            file_result = yield ph.render_page(self.UI_TEXT["submit_file_header"], file_prompt)

            # Skip: user didn't select a file
            if file_result.__type__ not in ("PayloadFile", "PayloadString"):
                logger.info("Skipped at file selection for %s", self.platform_name)
                return

            # 2. Materialize upload to path
            path = uploads.materialize_file(file_result)
            file_size = getattr(file_result.value, "size", None) if file_result.__type__ == "PayloadFile" else None
            bridge_logger.info("[%s] File received: %s bytes, %s",
                               self.platform_name, file_size or "unknown", file_result.__type__)

            # 3. Safety check
            try:
                uploads.check_file_safety(path)
            except (uploads.FileTooLargeError, uploads.ChunkedExportError) as e:
                logger.error("Safety check failed for %s: %s", self.platform_name, e)
                bridge_logger.info("[%s] Safety check failed: %s", self.platform_name, type(e).__name__)
                _ = yield ph.render_safety_error_page(self.platform_name, e)
                return

            # 4. Validate
            validation = self.validate_file(path)
            status = validation.get_status_code_id()
            category = getattr(validation, "current_ddp_category", None)
            category_id = getattr(category, "id", "unknown") if category else "unknown"

            if status == 0:
                bridge_logger.info("[%s] Validation: valid (%s)", self.platform_name, category_id)
            else:
                bridge_logger.info("[%s] Validation: invalid", self.platform_name)

            # 5. If invalid → retry prompt
            if status != 0:
                logger.info("Invalid %s file; prompting retry", self.platform_name)
                retry_prompt = self.generate_retry_prompt()
                retry_result = yield ph.render_page(self.UI_TEXT["retry_header"], retry_prompt)
                if retry_result.__type__ == "PayloadTrue":
                    continue  # loop back to step 1
                return  # user declined retry

            # 6. Extract
            logger.info("Extracting data for %s", self.platform_name)
            raw_result = self.extract_data(path, validation)
            if isinstance(raw_result, Generator):
                result = yield from raw_result
            else:
                result = raw_result

            # 7. Log extraction summary via bridge (PII-free: counts only)
            total_rows = sum(len(t.data_frame) for t in result.tables)
            if result.errors:
                error_summary = ", ".join(f"{k}×{v}" for k, v in result.errors.items())
                bridge_logger.info("[%s] Extraction complete: %d tables, %d rows; errors: %s",
                                   self.platform_name, len(result.tables), total_rows, error_summary)
            else:
                bridge_logger.info("[%s] Extraction complete: %d tables, %d rows; errors: none",
                                   self.platform_name, len(result.tables), total_rows)

            # 8. If no tables → no-data page
            if not result.tables:
                logger.info("No data extracted for %s", self.platform_name)
                _ = yield ph.render_no_data_page(self.platform_name)
                return

            break  # proceed to consent

        # 9. Render consent form
        bridge_logger.info("[%s] Consent form shown", self.platform_name)
        review_data_prompt = self.generate_review_data_prompt(result.tables)
        consent_result = yield ph.render_page(self.UI_TEXT["review_data_header"], review_data_prompt)

        # 10. Donate with per-platform key
        if consent_result.__type__ == "PayloadJSON":
            reviewed_data = consent_result.value
            bridge_logger.info("[%s] Consent: accepted", self.platform_name)
        elif consent_result.__type__ == "PayloadFalse":
            reviewed_data = json.dumps({"status": "data_submission declined"})
            bridge_logger.info("[%s] Consent: declined", self.platform_name)
        else:
            return

        donate_key = f"{self.session_id}-{self.platform_name.lower()}"
        bridge_logger.info("[%s] Donation started: payload size=%d bytes",
                           self.platform_name, len(reviewed_data))
        donate_result = yield ph.donate(donate_key, reviewed_data)

        # 11. Inspect donate result
        if not ph.handle_donate_result(donate_result):
            logger.error("Donation failed for %s", self.platform_name)
            bridge_logger.info("[%s] Donation result: failed", self.platform_name)
            _ = yield ph.render_donate_failure_page(self.platform_name)
            return

        bridge_logger.info("[%s] Donation result: success", self.platform_name)

    # Methods to be overridden by platform-specific implementations
    def generate_file_prompt(self):
        """Generate platform-specific file prompt."""
        return ph.generate_file_prompt("application/zip")

    @abstractmethod
    def validate_file(self, file: str) -> validate.ValidateInput:
        """Validate the file according to platform-specific rules."""
        raise NotImplementedError("Must be implemented by subclass")

    @abstractmethod
    def extract_data(self, file: str, validation: validate.ValidateInput) -> d3i_props.ExtractionResult:
        """Extract data from file using platform-specific logic."""
        raise NotImplementedError("Must be implemented by subclass")

    def generate_retry_prompt(self):
        """Generate platform-specific retry prompt."""
        return ph.generate_retry_prompt(self.platform_name)

    def generate_review_data_prompt(self, table_list):
        """Generate platform-specific review data prompt."""
        return ph.generate_review_data_prompt(
            description=self.UI_TEXT["review_data_description"],
            table_list=table_list,
        )
