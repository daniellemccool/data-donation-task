"""
LinkedIn

This module contains an example flow of a LinkedIn data donation study

Assumptions:
It handles DDPs in the english language with filetype CSV.
"""

import logging
from collections import Counter
import io
import re

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
)

logger = logging.getLogger(__name__)

DDP_CATEGORIES = [
    DDPCategory(
        id="csv_en",
        ddp_filetype=DDPFiletype.CSV,
        language=Language.EN,
        known_files=[
            "Ad_Targeting.csv",
            "Endorsement_Given_Info.csv",
            "Member_Follows.csv",
            "Recommendations_Given.csv",
            "Company Follows.csv",
            "Endorsement_Received_Info.csv",
            "messages.csv",
            "Registration.csv",
            "Connections.csv",
            "Inferences_about_you.csv",
            "PhoneNumbers.csv",
            "Rich Media.csv",
            "Contacts.csv",
            "Invitations.csv",
            "Positions.csv",
            "Skills.csv",
            "Education.csv",
            "Profile.csv",
            "Votes.csv",
            "Email Addresses.csv",
            "Learning.csv",
            "Reactions.csv",
            "LAN Ads Engagement.csv",
        ]
    ),
]

def strip_notes(b: io.BytesIO) -> io.BytesIO:
    """
    Strip notes LinkedIn puts at the start of CSV files
    """

    try:
        pattern = re.compile(rb'^(.*?)\n\n', re.DOTALL)
        out = io.BytesIO(pattern.sub(b'', b.read()))
    except Exception:
        out = b 

    return out


def company_follows_to_df(linkedin_zip: str, errors: Counter) -> pd.DataFrame:
    """
    'Company Follows.csv'
    """
    filename = "Company Follows.csv"

    b = eh.extract_file_from_zip(linkedin_zip, filename, errors=errors)
    df = eh.read_csv_from_bytes_to_df(b)

    return df


def member_follows_to_df(linkedin_zip: str, errors: Counter) -> pd.DataFrame:
    """
    'Member_Follows.csv'
    """
    filename = "Member_Follows.csv"
    b = eh.extract_file_from_zip(linkedin_zip, filename, errors=errors)
    b = strip_notes(b)
    df = eh.read_csv_from_bytes_to_df(b)

    return df


def connections_to_df(linkedin_zip: str, errors: Counter) -> pd.DataFrame:
    """
    'Connections.csv'
    """
    filename = "Connections.csv"
    b = eh.extract_file_from_zip(linkedin_zip, filename, errors=errors)
    b = strip_notes(b)
    df = eh.read_csv_from_bytes_to_df(b)

    return df


def reactions_to_df(linkedin_zip: str, errors: Counter) -> pd.DataFrame:
    """
    'Reactions.csv'
    """
    filename = "Reactions.csv"
    b = eh.extract_file_from_zip(linkedin_zip, filename, errors=errors)
    df = eh.read_csv_from_bytes_to_df(b)

    return df


def ads_clicked_to_df(linkedin_zip: str, errors: Counter) -> pd.DataFrame:
    """
    'Ads Clicked.csv'
    """
    filename = "Ads Clicked.csv"
    b = eh.extract_file_from_zip(linkedin_zip, filename, errors=errors)
    df = eh.read_csv_from_bytes_to_df(b)

    return df


def search_queries_to_df(linkedin_zip: str, errors: Counter) -> pd.DataFrame:
    """
    'SearchQueries.csv'
    """
    filename = "SearchQueries.csv"
    b = eh.extract_file_from_zip(linkedin_zip, filename, errors=errors)
    df = eh.read_csv_from_bytes_to_df(b)

    return df


def shares_to_df(linkedin_zip: str, errors: Counter) -> pd.DataFrame:
    """
    'Shares.csv'
    """
    filename = "Shares.csv"
    b = eh.extract_file_from_zip(linkedin_zip, filename, errors=errors)
    df = eh.read_csv_from_bytes_to_df(b)

    return df


def comments_to_df(linkedin_zip: str, errors: Counter) -> pd.DataFrame:
    """
    'Comments.csv'
    """
    filename = "Comments.csv"
    b = eh.extract_file_from_zip(linkedin_zip, filename, errors=errors)
    df = eh.read_csv_from_bytes_to_df(b)

    return df


def extraction(linkedin_zip: str) -> ExtractionResult:
    errors = Counter()
    tables = [
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="linkedin_ads_clicked",
            data_frame=ads_clicked_to_df(linkedin_zip, errors),
            title=props.Translatable({
                "en": "Ads you clicked on",
                "nl": "Ads clicked"
            }),
            description=props.Translatable({
                "en": "Record of advertisements you have clicked on while using LinkedIn. Note: LinkedIn only provides numeric ad IDs, not ad titles or descriptions.",
                "nl": "Overzicht van advertenties waarop je hebt geklikt tijdens het gebruik van LinkedIn. Let op: LinkedIn geeft alleen numerieke advertentie-ID's, geen titels of beschrijvingen.",
            }),
            headers={
                "Ad clicked Date": props.Translatable({"en": "Ad clicked Date", "nl": "Advertentiedatum"}),
                "Ad Title/Id": props.Translatable({"en": "Ad Title/Id", "nl": "Advertentietitel/id"}),
            }
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="linkedin_comments",
            data_frame=comments_to_df(linkedin_zip, errors),
            title=props.Translatable({
                "en": "Your comments on LinkedIn",
                "nl": "Comments"
            }),
            description=props.Translatable({
                "en": "Comments you've posted on LinkedIn content",
                "nl": "Reacties die je hebt geplaatst op LinkedIn-content"
            }),
            headers={
                "Date": props.Translatable({"en": "Date", "nl": "Datum"}),
                "Message": props.Translatable({"en": "Message", "nl": "Bericht"}),
            },
            visualizations=[
                {
                    "title": {
                        "en": "Words in your comments",
                        "nl": "Words in your comments"
                    },
                    "type": "wordcloud",
                    "textColumn": "Message",
                    "tokenize": True
                }
            ]
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="linked_in_company_follows",
            data_frame=company_follows_to_df(linkedin_zip, errors),
            title=props.Translatable({
                "en": "Companies you follow",
                "nl": "Company follows"
            }),
            description=props.Translatable({
                "en": "List of companies you are following on LinkedIn",
                "nl": "Lijst van bedrijven die je volgt op LinkedIn"
            }),
            headers={
                "Organization": props.Translatable({"en": "Organization", "nl": "Organisatie"}),
                "Followed On": props.Translatable({"en": "Followed On", "nl": "Gevolgd op"}),
            }
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="linkedin_shares",
            data_frame=shares_to_df(linkedin_zip, errors),
            title=props.Translatable({
                "en": "Posts you shared on LinkedIn",
                "nl": "Shares"
            }),
            description=props.Translatable({
                "en": "Content you've shared with your network on LinkedIn",
                "nl": "Content die je hebt gedeeld met je netwerk op LinkedIn"
            }),
            headers={
                "Date": props.Translatable({"en": "Date", "nl": "Datum"}),
                "ShareLink": props.Translatable({"en": "ShareLink", "nl": "Gedeelde link"}),
                "ShareCommentary": props.Translatable({"en": "ShareCommentary", "nl": "Gedeelde tekst"}),
                "SharedUrl": props.Translatable({"en": "SharedUrl", "nl": "Gedeelde URL"}),
                "MediaUrl": props.Translatable({"en": "MediaUrl", "nl": "Media-URL"}),
                "Visibility": props.Translatable({"en": "Visibility", "nl": "Zichtbaarheid"}),
            }
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="linkedin_reactions",
            data_frame=reactions_to_df(linkedin_zip, errors),
            title=props.Translatable({
                "en": "Your reactions on LinkedIn",
                "nl": "Reactions"
            }),
            description=props.Translatable({
                "en": "Record of your reactions to posts and content on LinkedIn",
                "nl": "Overzicht van je reacties op berichten en content op LinkedIn"
            }),
            headers={
                "Date": props.Translatable({"en": "Date", "nl": "Datum"}),
                "Type": props.Translatable({"en": "Type", "nl": "Type"}),
            },
            visualizations=[
                {
                    "title": {
                        "en": "The type of reactions you put under posts on Linkedin",
                        "nl": "The type of reactions you put under posts on Linkedin"
                    },
                    "type": "wordcloud",
                    "textColumn": "Type",
                    "tokenize": True
                }
            ]
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="linkedin_connections",
            data_frame=connections_to_df(linkedin_zip, errors),
            title=props.Translatable({
                "en": "Your LinkedIn connections",
                "nl": "Je LinkedIn-connecties"
            }),
            description=props.Translatable({
                "en": "List of people you are connected with on LinkedIn",
                "nl": "Lijst van mensen met wie je verbonden bent op LinkedIn"
            }),
            headers={
                "First Name": props.Translatable({"en": "First Name", "nl": "Voornaam"}),
                "Last Name": props.Translatable({"en": "Last Name", "nl": "Achternaam"}),
                "Email Address": props.Translatable({"en": "Email Address", "nl": "E-mailadres"}),
                "Company": props.Translatable({"en": "Company", "nl": "Bedrijf"}),
                "Position": props.Translatable({"en": "Position", "nl": "Functie"}),
                "Connected On": props.Translatable({"en": "Connected On", "nl": "Verbonden op"}),
            }
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="linkedin_search_queries",
            data_frame=search_queries_to_df(linkedin_zip, errors),
            title=props.Translatable({
                "en": "Your search queries on LinkedIn",
                "nl": "Search queries"
            }),
            description=props.Translatable({
                "en": "Terms and phrases you've searched for on LinkedIn",
                "nl": "Termen en zinnen waarnaar je hebt gezocht op LinkedIn"
            }),
            headers={
                "Time": props.Translatable({"en": "Time", "nl": "Tijd"}),
                "Search Query": props.Translatable({"en": "Search Query", "nl": "Zoekterm"}),
            },
            visualizations=[
                {
                    "title": {
                        "en": "What you searched for on Linkedin",
                        "nl": "What you searched for on Linkedin"
                    },
                    "type": "wordcloud",
                    "textColumn": "Search Query",
                    "tokenize": True
                }
            ]
        )
    ]
    
    return ExtractionResult(
        tables=[table for table in tables if not table.data_frame.empty],
        errors=errors,
    )


class LinkedInFlow(FlowBuilder):
    def __init__(self, session_id: str):
        super().__init__(session_id, "LinkedIn")
        
    def validate_file(self, file):
        return validate.validate_zip(DDP_CATEGORIES, file)
        
    def extract_data(self, file_value, validation):
        return extraction(file_value)


def process(session_id):
    flow = LinkedInFlow(session_id)
    return flow.start_flow()
