# --------------------------------------------------------------------
# This script provides a basic data donation flow using the standard
# UI components and helper functions available in this package.
#
# Researchers: copy this file and adapt it for your study. The three
# things you will most likely change are:
#   1. PLATFORM_NAME — the name of the platform you are collecting from
#   2. extract_the_data_you_are_interested_in() — your actual extraction logic
#   3. validate_the_participants_input() — your file validation logic
#
# For a more advanced example using custom UI components, see:
#   script_custom_ui.py
# --------------------------------------------------------------------

import zipfile
import json

import pandas as pd

import port.api.props as props
import port.api.d3i_props as d3i_props
import port.helpers.port_helpers as ph


PLATFORM_NAME = "Platform of interest"

SUBMIT_FILE_HEADER = props.Translatable({
    "en": "Select your data download file",
    "nl": "Selecteer uw databestand",
})

REVIEW_DATA_HEADER = props.Translatable({
    "en": "Your data",
    "nl": "Uw gegevens",
})

REVIEW_DATA_DESCRIPTION = props.Translatable({
    "en": "Below you will find the data extracted from the file you submitted. Please review the data carefully and remove any information you do not wish to share. If you would like to share this data, click 'Yes, share for research' at the bottom of the page.",
    "nl": "Hieronder ziet u de gegevens uit het bestand dat u heeft ingediend. Bekijk de gegevens zorgvuldig en verwijder wat u niet wilt delen. Als u de gegevens wilt delen, klik dan onderaan op 'Ja, deel voor onderzoek'.",
})

RETRY_HEADER = props.Translatable({
    "en": "Try again",
    "nl": "Probeer opnieuw",
})


def process(session_id: str):
    # Start of the data donation flow
    while True:
        # Ask the participant to submit a file
        file_prompt = ph.generate_file_prompt("application/zip, text/plain")
        file_prompt_result = yield ph.render_page(SUBMIT_FILE_HEADER, file_prompt)

        # If the participant submitted a file: continue
        if file_prompt_result.__type__ == "PayloadFile":

            # Validate the file the participant submitted
            is_data_valid = validate_the_participants_input(file_prompt_result.value)

            # Happy flow: file is valid
            if is_data_valid:
                extracted_data = extract_the_data_you_are_interested_in(file_prompt_result.value)
                consent_prompt = ph.generate_review_data_prompt(
                    description=REVIEW_DATA_DESCRIPTION,
                    table_list=extracted_data,
                )
                result = yield ph.render_page(REVIEW_DATA_HEADER, consent_prompt)
                if result.__type__ == "PayloadJSON":
                    yield ph.donate(session_id, result.value)
                if result.__type__ == "PayloadFalse":
                    yield ph.donate(session_id, json.dumps({"status": "donation declined"}))
                break

            # Sad flow: file is invalid, ask to retry
            else:
                retry_prompt = ph.generate_retry_prompt(PLATFORM_NAME)
                retry_result = yield ph.render_page(RETRY_HEADER, retry_prompt)
                if retry_result.__type__ == "PayloadTrue":
                    continue
                else:
                    break

        # Participant pressed skip
        else:
            break

    yield ph.exit(0, "Success")


def extract_the_data_you_are_interested_in(file) -> list[d3i_props.PropsUIPromptConsentFormTableViz]:
    """
    Extract the data relevant to your research from the submitted file.

    The `file` argument is a file-like object that can be passed directly
    to zipfile.ZipFile(). Replace this implementation with your own
    extraction logic.

    Returns a list of PropsUIPromptConsentFormTableViz, one per table
    you want to show the participant in the consent form.
    """
    tables = []

    try:
        zf = zipfile.ZipFile(file)
        data = []
        for name in zf.namelist():
            info = zf.getinfo(name)
            data.append((name, info.compress_size, info.file_size))

        df = pd.DataFrame(data, columns=["File name", "Compressed size", "File size"])

        table_title = props.Translatable({
            "en": "Contents of your zip file",
            "nl": "Inhoud van uw zip bestand",
        })

        # Example visualization — remove or replace as needed
        wordcloud = {
            "title": {"en": "File names", "nl": "Bestandsnamen"},
            "type": "wordcloud",
            "textColumn": "File name",
            "tokenize": True,
        }

        tables.append(
            d3i_props.PropsUIPromptConsentFormTableViz(
                id="zip_contents",
                title=table_title,
                data_frame=df,
                visualizations=[wordcloud],
                delete_option=True,
                data_frame_max_size=10000,
            )
        )

    except Exception as e:
        print(f"Something went wrong extracting data: {e}")

    return tables


def validate_the_participants_input(file) -> bool:
    """
    Check that the participant submitted a valid zip file.

    The `file` argument is a file-like object. Extend this function
    to check for expected file contents, language, or structure.
    Returns True if valid, False otherwise.
    """
    try:
        with zipfile.ZipFile(file):
            return True
    except zipfile.BadZipFile:
        return False
