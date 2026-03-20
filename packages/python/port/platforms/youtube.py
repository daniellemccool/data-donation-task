"""
YouTube

This module provides an example flow of a YouTube data donation study

Assumptions:
It handles DDPs in the Dutch and English language with filetype JSON.
"""
import json
import logging
from collections import Counter

import pandas as pd

import port.api.props as props
import port.api.d3i_props as d3i_props
from port.api.d3i_props import ExtractionResult
import port.helpers.extraction_helpers as eh
import port.helpers.validate as validate
from port.helpers.flow_builder import FlowBuilder

from port.helpers.validate import (
    DDPCategory,
    DDPFiletype,
    Language,
    ValidateInput,
)

logger = logging.getLogger(__name__)

DDP_CATEGORIES = [
    DDPCategory(
        id="json_en",
        ddp_filetype=DDPFiletype.JSON,
        language=Language.EN,
        known_files=[
            "search-history.json",
            "watch-history.json",
            "subscriptions.csv",
            "comments.csv",
        ],
    ),
    DDPCategory(
        id="json_nl",
        ddp_filetype=DDPFiletype.JSON,
        language=Language.NL,
        known_files=[
            "abonnementen.csv",
            "kijkgeschiedenis.json",
            "zoekgeschiedenis.json",
            "reacties.csv",
        ],
    ),
]


def watch_history_to_df(zip: str, validation, errors: Counter) -> pd.DataFrame:

    if validation.current_ddp_category.language == Language.NL:
        b = eh.extract_file_from_zip(zip, "kijkgeschiedenis.json", errors=errors)
        d = eh.read_json_from_bytes(b, errors=errors)

    elif validation.current_ddp_category.language == Language.EN:
        b = eh.extract_file_from_zip(zip, "watch-history.json", errors=errors)
        d = eh.read_json_from_bytes(b, errors=errors)

    else:
        d = {}

    out = pd.DataFrame()
    datapoints = []

    try:
        for item in d:
            datapoints.append((
                item.get("title", ""),
                item.get("titleUrl", ""),
                item.get("time", ""),
            ))

        out = pd.DataFrame(datapoints, columns=["Title", "URL", "Timestamp"])  # pyright: ignore

    except Exception as e:
        logger.error("Exception caught: %s", e)
        errors[type(e).__name__] += 1

    return out


def search_history_to_df(zip: str, validation, errors: Counter) -> pd.DataFrame:

    if validation.current_ddp_category.language == Language.NL:
        b = eh.extract_file_from_zip(zip, "zoekgeschiedenis.json", errors=errors)
        d = eh.read_json_from_bytes(b, errors=errors)

    elif validation.current_ddp_category.language == Language.EN:
        b = eh.extract_file_from_zip(zip, "search-history.json", errors=errors)
        d = eh.read_json_from_bytes(b, errors=errors)

    else:
        d = {}

    out = pd.DataFrame()
    datapoints = []

    try:
        for item in d:
            datapoints.append((
                item.get("title", ""),
                item.get("titleUrl", ""),
                item.get("time", ""),
                bool(item.get("details") or []),
            ))

        out = pd.DataFrame(datapoints, columns=["Title", "URL", "Timestamp", "Ad"])  # pyright: ignore

    except Exception as e:
        logger.error("Exception caught: %s", e)
        errors[type(e).__name__] += 1

    return out


def subscriptions_to_df(youtube_zip: str, validation, errors: Counter) -> pd.DataFrame:
    """
    Parses 'subscriptions.csv' or 'abonnementen.csv' from a YouTube DDP.
    Normalises column names to English regardless of export language.
    """

    if validation.current_ddp_category.language == Language.NL:
        file_name = "abonnementen.csv"

    elif validation.current_ddp_category.language == Language.EN:
        file_name = "subscriptions.csv"
    else:
        file_name = ""

    b = eh.extract_file_from_zip(youtube_zip, file_name, errors=errors)
    df = eh.read_csv_from_bytes_to_df(b)

    if not df.empty:
        df.columns = ["Channel Id", "Channel URL", "Channel Name"]  # pyright: ignore

    return df


def _parse_comment_text(raw: str) -> str:
    try:
        segments = json.loads(f"[{raw}]")
        return " ".join(s["text"] for s in segments if isinstance(s, dict) and s.get("text", "").strip())
    except Exception:
        return raw


def comments_to_df(youtube_zip: str, validation, errors: Counter) -> pd.DataFrame:
    if validation.current_ddp_category.language == Language.NL:
        file_name = "reacties.csv"
    else:
        file_name = "comments.csv"

    b = eh.extract_file_from_zip(youtube_zip, file_name, errors=errors)
    df = eh.read_csv_from_bytes_to_df(b)

    if not df.empty:
        # Normalise NL column names to English
        df = df.rename(columns={
            "Reactie-ID": "Comment ID",
            "Kanaal-ID": "Channel ID",
            "Aanmaaktijdstempel reactie": "Timestamp",
            "Comment create timestamp": "Timestamp",
            "Prijs": "Price",
            "Video-ID": "Video ID",
            "Reactietekst": "Comment text",
        })
        keep = ["Timestamp", "Channel ID", "Comment text", "Comment ID", "Video ID", "Price"]
        df = df[[col for col in keep if col in df.columns]]  # pyright: ignore
        if "Comment text" in df.columns:
            df["Comment text"] = df["Comment text"].apply(_parse_comment_text)

    return df


def extraction(zip: str, validation: ValidateInput) -> ExtractionResult:
    errors = Counter()
    tables = [
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="youtube_watch_history",
            data_frame=watch_history_to_df(zip, validation, errors),
            title=props.Translatable({
                "en": "Your watch history",
                "nl": "Je kijkgeschiedenis",
            }),
            description=props.Translatable({
                "en": "Videos you have watched on YouTube, including timestamps.",
                "nl": "Video's die je op YouTube hebt bekeken, inclusief tijdstippen.",
            }),
            headers={
                "Title": props.Translatable({"en": "Title", "nl": "Titel"}),
                "URL": props.Translatable({"en": "URL", "nl": "URL"}),
                "Timestamp": props.Translatable({"en": "Timestamp", "nl": "Datum en tijd"}),
            },
            visualizations=[
                {
                    "title": {
                        "en": "Videos watched over time",
                        "nl": "Bekeken video's in de loop van de tijd",
                    },
                    "type": "area",
                    "group": {
                        "column": "Timestamp",
                        "dateFormat": "auto",
                    },
                    "values": [{
                        "aggregate": "count",
                        "label": "Count",
                    }],
                },
                {
                    "title": {
                        "en": "Videos watched by hour of the day",
                        "nl": "Bekeken video's per uur van de dag",
                    },
                    "type": "bar",
                    "group": {
                        "column": "Timestamp",
                        "dateFormat": "hour_cycle",
                        "label": "Hour of the day",
                    },
                    "values": [{
                        "label": "Count",
                    }],
                },
                {
                    "title": {
                        "en": "Words in video titles you watched",
                        "nl": "Woorden in titels van bekeken video's",
                    },
                    "type": "wordcloud",
                    "textColumn": "Title",
                    "tokenize": True,
                },
            ]
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="youtube_search_history",
            data_frame=search_history_to_df(zip, validation, errors),
            title=props.Translatable({
                "en": "Your search and watch history",
                "nl": "Je zoek- en kijkgeschiedenis",
            }),
            description=props.Translatable({
                "en": "Your search queries, videos watched, and ads seen on YouTube, with timestamps.",
                "nl": "Je zoekopdrachten, bekeken video's en geziene advertenties op YouTube, met tijdstippen.",
            }),
            headers={
                "Title": props.Translatable({"en": "Title", "nl": "Titel"}),
                "URL": props.Translatable({"en": "URL", "nl": "URL"}),
                "Timestamp": props.Translatable({"en": "Timestamp", "nl": "Datum en tijd"}),
                "Ad": props.Translatable({"en": "Ad", "nl": "Advertentie"}),
            },
            visualizations=[
                {
                    "title": {
                        "en": "Words in your search and watch history",
                        "nl": "Woorden in je zoek- en kijkgeschiedenis",
                    },
                    "type": "wordcloud",
                    "textColumn": "Title",
                    "tokenize": True,
                }
            ]
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="youtube_subscriptions",
            data_frame=subscriptions_to_df(zip, validation, errors),
            title=props.Translatable({
                "en": "Your subscriptions",
                "nl": "Je abonnementen",
            }),
            description=props.Translatable({
                "en": "YouTube channels you are subscribed to.",
                "nl": "YouTube-kanalen waarop je bent geabonneerd.",
            }),
            headers={
                "Channel Id": props.Translatable({"en": "Channel Id", "nl": "Kanaal-id"}),
                "Channel URL": props.Translatable({"en": "Channel URL", "nl": "Kanaal-URL"}),
                "Channel Name": props.Translatable({"en": "Channel Name", "nl": "Kanaalnaam"}),
            },
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="youtube_comments",
            data_frame=comments_to_df(zip, validation, errors),
            title=props.Translatable({
                "en": "Your comments",
                "nl": "Je reacties",
            }),
            description=props.Translatable({
                "en": "Comments you posted on YouTube videos and posts.",
                "nl": "Reacties die je op YouTube-video's en -posts hebt geplaatst.",
            }),
            headers={
                "Comment ID": props.Translatable({"en": "Comment ID", "nl": "Reactie-ID"}),
                "Channel ID": props.Translatable({"en": "Channel ID", "nl": "Kanaal-ID"}),
                "Timestamp": props.Translatable({"en": "Timestamp", "nl": "Datum en tijd"}),
                "Price": props.Translatable({"en": "Price", "nl": "Prijs"}),
                "Video ID": props.Translatable({"en": "Video ID", "nl": "Video-ID"}),
                "Comment text": props.Translatable({"en": "Comment text", "nl": "Reactietekst"}),
            },
            visualizations=[
                {
                    "title": {
                        "en": "Most common words in your comments",
                        "nl": "Meest voorkomende woorden in je reacties",
                    },
                    "type": "wordcloud",
                    "textColumn": "Comment text",
                    "tokenize": True,
                }
            ],
        ),
    ]

    return ExtractionResult(
        tables=[table for table in tables if not table.data_frame.empty],
        errors=errors,
    )


class YouTubeFlow(FlowBuilder):
    def __init__(self, session_id: str):
        super().__init__(session_id, "YouTube")

    def validate_file(self, file):
        return validate.validate_zip(DDP_CATEGORIES, file)

    def extract_data(self, file, validation):
        return extraction(file, validation)


def process(session_id):
    flow = YouTubeFlow(session_id)
    return flow.start_flow()
