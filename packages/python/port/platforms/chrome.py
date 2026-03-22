"""
Chrome

This module contains a Chrome browser history data donation flow.

Assumptions:
It handles DDPs in English and Dutch with filetype JSON.
"""
from collections import Counter
from html.parser import HTMLParser
import logging

import pandas as pd

import port.api.props as props
import port.api.d3i_props as d3i_props
from port.api.d3i_props import ExtractionResult
import port.helpers.extraction_helpers as eh
import port.helpers.validate as validate
from port.helpers.extraction_helpers import ZipArchiveReader
from port.helpers.flow_builder import FlowBuilder

from port.helpers.validate import (
    DDPCategory,
    DDPFiletype,
    Language,
)

logger = logging.getLogger(__name__)


DDP_CATEGORIES = [
    DDPCategory(
        id="json_en",
        ddp_filetype=DDPFiletype.JSON,
        language=Language.EN,
        known_files=[
            "Autofill.json",
            "Bookmarks.html",
            "BrowserHistory.json",
            "History.json",
            "Device Information.json",
            "Dictionary.csv",
            "Extensions.json",
            "Omnibox.json",
            "OS Settings.json",
            "ReadingList.html",
            "SearchEngines.json",
            "SyncSettings.json",
        ],
    ),
    DDPCategory(
        id="json_nl",
        ddp_filetype=DDPFiletype.JSON,
        language=Language.NL,
        known_files=[
            "Adressen en meer.json",
            "Bookmarks.html",
            "Geschiedenis.json",
            "Leeslijst.html",
            "Woordenboek.csv",
            "Apparaatgegevens.json",
            "Extensies.json",
            "Instellingen.json",
            "OS-instellingen.json",
        ],
    ),
]


class _BookmarkParser(HTMLParser):
    """Minimal HTML parser to extract <a> tags from bookmarks HTML."""

    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._current_href: str | None = None
        self._current_text = ""

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs_dict = dict(attrs)
            self._current_href = attrs_dict.get("href", "")
            self._current_text = ""

    def handle_data(self, data):
        if self._current_href is not None:
            self._current_text = data

    def handle_endtag(self, tag):
        if tag == "a" and self._current_href is not None:
            self.links.append((self._current_text, self._current_href))
            self._current_href = None


def browser_history_to_df(reader: ZipArchiveReader, errors: Counter) -> pd.DataFrame:
    """Extract browser history from History.json, BrowserHistory.json, or Geschiedenis.json (NL)."""

    d: dict | list = {}
    for filename in ("Geschiedenis.json", "BrowserHistory.json", "History.json"):
        result = reader.json(filename)
        if result.found:
            d = result.data
            break

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["Browser History"]  # type: ignore
        for item in items:
            datapoints.append((
                item.get("title", None),
                item.get("url", None),
                item.get("page_transition_qualifier") or item.get("page_transition"),
                eh.epoch_to_iso(item.get("time_usec", 0) / 1_000_000, errors=errors),
            ))

        out = pd.DataFrame(datapoints, columns=["Title", "URL", "Transition", "Date"])
        out = out.sort_values("Date", ascending=False).head(10_000).reset_index(drop=True)
    except Exception as e:
        logger.error("Exception caught: %s", e)
        errors[type(e).__name__] += 1

    return out


def bookmarks_to_df(reader: ZipArchiveReader, errors: Counter) -> pd.DataFrame:
    """Extract bookmarks from Bookmarks.html."""

    result = reader.raw("Bookmarks.html")
    if not result.found:
        return pd.DataFrame()
    out = pd.DataFrame()

    try:
        html_content = result.data.read().decode("utf-8", errors="replace")
        parser = _BookmarkParser()
        parser.feed(html_content)
        out = pd.DataFrame(parser.links, columns=["Bookmark", "URL"])
    except Exception as e:
        logger.error("Exception caught: %s", e)
        errors[type(e).__name__] += 1

    return out


def omnibox_to_df(reader: ZipArchiveReader, errors: Counter) -> pd.DataFrame:
    """Extract omnibox (address bar) history from Omnibox.json or History.json."""

    d: dict | list = {}
    for filename in ("Omnibox.json", "History.json"):
        result = reader.json(filename)
        if result.found:
            d = result.data
            break

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["Typed Url"]  # type: ignore
        for item in items:
            datapoints.append((
                item.get("title", None),
                len(item.get("visits", [])),
                item.get("url", None),
            ))

        out = pd.DataFrame(datapoints, columns=["Title", "Number of visits", "URL"])
        out = out.sort_values(by="Number of visits", ascending=False).reset_index(drop=True)
    except Exception as e:
        logger.error("Exception caught: %s", e)
        errors[type(e).__name__] += 1

    return out


def extraction(chrome_zip: str, validation) -> ExtractionResult:
    errors = Counter()
    reader = ZipArchiveReader(chrome_zip, validation.archive_members, errors)
    tables = [
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="chrome_browser_history",
            data_frame=browser_history_to_df(reader, errors),
            title=props.Translatable({
                "en": "Chrome browser history",
                "nl": "Chrome browsergeschiedenis",
            }),
            description=props.Translatable({
                "en": "The websites you have visited using Chrome",
                "nl": "De websites die u heeft bezocht met Chrome",
            }),
            headers={
                "Title": props.Translatable({"en": "Title", "nl": "Titel"}),
                "URL": props.Translatable({"en": "URL", "nl": "URL"}),
                "Transition": props.Translatable({"en": "Transition type", "nl": "Transitietype"}),
                "Date": props.Translatable({"en": "Date", "nl": "Datum"}),
            },
            visualizations=[
                {
                    "title": {"en": "Most visited websites", "nl": "Meest bezochte websites"},
                    "type": "wordcloud",
                    "textColumn": "URL",
                    "tokenize": False,
                }
            ],
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="chrome_bookmarks",
            data_frame=bookmarks_to_df(reader, errors),
            title=props.Translatable({
                "en": "Chrome bookmarks",
                "nl": "Chrome bladwijzers",
            }),
            description=props.Translatable({
                "en": "Websites you have bookmarked in Chrome",
                "nl": "Websites die u heeft opgeslagen als bladwijzer in Chrome",
            }),
            headers={
                "Bookmark": props.Translatable({"en": "Bookmark", "nl": "Bladwijzer"}),
                "URL": props.Translatable({"en": "URL", "nl": "URL"}),
            },
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="chrome_omnibox",
            data_frame=omnibox_to_df(reader, errors),
            title=props.Translatable({
                "en": "Chrome address bar history",
                "nl": "Chrome adresbalk geschiedenis",
            }),
            description=props.Translatable({
                "en": "URLs you have typed directly into the Chrome address bar",
                "nl": "URLs die u direct in de Chrome adresbalk heeft ingevoerd",
            }),
            headers={
                "Title": props.Translatable({"en": "Title", "nl": "Titel"}),
                "Number of visits": props.Translatable({"en": "Number of visits", "nl": "Aantal bezoeken"}),
                "URL": props.Translatable({"en": "URL", "nl": "URL"}),
            },
        ),
    ]

    return ExtractionResult(
        tables=[table for table in tables if not table.data_frame.empty],
        errors=errors,
    )


class ChromeFlow(FlowBuilder):
    def __init__(self, session_id: str):
        super().__init__(session_id, "Chrome")

    def validate_file(self, file):
        return validate.validate_zip(DDP_CATEGORIES, file)

    def extract_data(self, file_value, validation):
        return extraction(file_value, validation)


def process(session_id):
    flow = ChromeFlow(session_id)
    return flow.start_flow()
