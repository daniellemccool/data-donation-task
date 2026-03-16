import gzip
import json
import logging
from datetime import datetime, timezone

import pandas as pd
import port.api.props as props
import port.donation_flows.facebook as facebook
import port.donation_flows.instagram as instagram
import port.donation_flows.tiktok as tiktok
import port.donation_flows.twitter as twitter
import port.donation_flows.youtube as youtube
import port.helpers.port_helpers as ph
from port.api import d3i_props


class DataFrameHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self._data = []

    def emit(self, record):
        self._data.append(
            {
                "Level": record.levelname,
                "Message": record.getMessage(),
                "Timestamp": datetime.fromtimestamp(record.created).isoformat(),
            }
        )

    @property
    def df(self):
        return pd.DataFrame(self._data)


log_handler = DataFrameHandler()
logging.basicConfig(handlers=[log_handler], level=logging.INFO)
logger = logging.getLogger(__name__)


RETRY_HEADER = props.Translatable(
    {
        "en": "Try again",
        "nl": "Probeer opnieuw",
        "es": "Intente de nuevo",
    }
)


def process(session_id: int, platform: str | None):
    if platform is None or platform == "":
        p = yield ask_platform()
        platform = p.value
        assert isinstance(platform, str)

    while True:
        logger.info(f"Prompt for file for {platform}")

        if platform.lower() in ("tiktok", "tt"):
            extensions_arg = "application/json, application/zip"
        else:
            extensions_arg = "application/zip"

        file_prompt = ph.generate_file_prompt(extensions_arg)
        file_result = yield ph.render_page(platform_file_header(platform), file_prompt)

        if file_result.__type__ in ("PayloadString", "PayloadFile"):
            if file_result.__type__ == "PayloadFile":
                # PayloadFile: value is an AsyncFileAdapter (file-like).
                # Materialize to /tmp so existing helpers can use path-based zipfile.
                adapter = file_result.value
                file_path = f"/tmp/{adapter.name}"
                with open(file_path, "wb") as f:
                    f.write(adapter.read())
                adapter.seek(0)
                logger.info(f"PayloadFile: wrote {adapter.size} bytes to {file_path}")
            else:
                # PayloadString: value is a WORKERFS filesystem path
                file_path = file_result.value

            is_data_valid = is_valid(file_path, platform)
            logger.info(f"Received file {file_path}, valid={is_data_valid}")

            if is_data_valid:
                # Good, proceed with donation
                review_data_prompt = donation_flow([file_path], platform)
                # WvA I think donation flow should just never return None instead?
                if not review_data_prompt:
                    logger.info("No donation flow received")
                    break
                result = yield ph.render_page(
                    platform_data_header(platform),
                    review_data_prompt,
                )
                if result.__type__ == "PayloadJSON":
                    data = result.value
                    if False:  # Disable zipping for now
                        data = gzip.compress(data.encode("utf-8")).decode("latin-1")
                        logging.info(f"Zipped {len(result.value)} bytes into {len(data)} bytes")
                    logging.info(f"About to upload {len(data)} bytes")

                    yield ph.donate(f"{session_id}", data)
                elif result.__type__ == "PayloadFalse":
                    logging.info("Data submission declined by user")
                    value = json.dumps('{"status" : "data_submission declined"}')
                    yield ph.donate(f"{session_id}", value)

                break
            else:
                # Invalid file, allow retry
                retry_prompt = ph.generate_retry_prompt(platform)
                retry_prompt_result = yield ph.render_page(RETRY_HEADER, retry_prompt)

                # The participant wants to retry: start from the beginning
                if retry_prompt_result.__type__ == "PayloadTrue":
                    logger.info("Retrying file selection")
                    continue
                # The participant does not want to retry or pressed skip
                # WvA: Since we removed the cancel button, this else is redundant?
                else:
                    logger.info("Participant cancelled file re-selection. Note: This should never happen anymore")
                    break

        else:
            logger.info("Skipped at file selection ending flow")
            break
    log_json = log_handler.df.to_json(orient="records")
    yield ph.donate(f"{session_id}-log", log_json)
    yield ph.exit(0, "Success")


def is_valid(file_input: str, platform: str) -> bool:
    if platform == "Instagram":
        return instagram.is_data_valid(file_input)
    if platform == "Facebook":
        return facebook.is_data_valid(file_input)
    if platform == "Twitter":
        return twitter.is_data_valid(file_input)
    if platform == "Tiktok":
        return tiktok.is_data_valid(file_input)
    if platform == "Youtube":
        return youtube.is_data_valid(file_input)
    raise ValueError(f"Unknown platform: {platform}")


def donation_flow(file_input: list[str], platform: str) -> d3i_props.PropsUIPromptConsentFormViz | None:
    if platform == "Instagram":
        return instagram.create_donation_flow(file_input)
    if platform == "Facebook":
        return facebook.create_donation_flow(file_input)
    if platform == "Twitter":
        return twitter.create_donation_flow(file_input)
    if platform == "Tiktok":
        return tiktok.create_donation_flow(file_input)
    if platform == "Youtube":
        return youtube.create_donation_flow(file_input)
    raise ValueError(f"Unknown platform: {platform}")


def platform_file_header(platform: str):
    return props.Translatable(
        {
            "en": f"Select the {platform} data file",
            "nl": f"Selecteer het {platform} databestand",
            "es": f"Selecciona el archivo de datos de {platform}",
        }
    )


def platform_data_header(platform: str):
    return props.Translatable(
        {
            "en": f"Review the {platform} data",
            "nl": f"Controleer de {platform} data",
            "es": f"Revisa los datos de {platform}",
        }
    )


def ask_platform():
    title = props.Translatable(
        {
            "en": "Select import script to test",
            "nl": "Selecteer het import script dat je wilt testen",
            "es": "Selecciona el script de importación para probar",
        }
    )

    platform_buttons = props.PropsUIPromptRadioInput(
        title=props.Translatable(
            {
                "en": "Platform",
                "nl": "Platform",
                "es": "Platform",
            }
        ),
        description=props.Translatable({"en": "", "nl": "", "es": ""}),
        items=[
            props.RadioItem(id=5, value="Youtube"),
            props.RadioItem(id=4, value="Instagram"),
            props.RadioItem(id=2, value="Tiktok"),
            props.RadioItem(id=3, value="Facebook"),
            props.RadioItem(id=1, value="Twitter"),
        ],
    )

    return ph.render_page(title, platform_buttons)
