"""Study orchestration — platform list, filtering, sequencing.

This module defines which platforms are included in the study and
delegates per-platform flows to FlowBuilder subclasses via `yield from`.
"""
import port.helpers.port_helpers as ph

import port.platforms.linkedin as linkedin
import port.platforms.instagram as instagram
import port.platforms.facebook as facebook
import port.platforms.youtube as youtube
import port.platforms.tiktok as tiktok
import port.platforms.netflix as netflix
import port.platforms.chatgpt as chatgpt
import port.platforms.whatsapp as whatsapp
import port.platforms.x as x
import port.platforms.chrome as chrome


def process(session_id: str, platform: str | None = None):
    """Run the data donation study.

    Args:
        session_id: Unique session identifier (from host).
        platform: If set (via VITE_PLATFORM), run only this platform.
    """
    all_platforms = [
        ("LinkedIn", linkedin.LinkedInFlow(session_id)),
        ("Instagram", instagram.InstagramFlow(session_id)),
        ("Facebook", facebook.FacebookFlow(session_id)),
        ("YouTube", youtube.YouTubeFlow(session_id)),
        ("TikTok", tiktok.TikTokFlow(session_id)),
        ("Netflix", netflix.NetflixFlow(session_id)),
        ("ChatGPT", chatgpt.ChatGPTFlow(session_id)),
        ("WhatsApp", whatsapp.WhatsAppFlow(session_id)),
        ("X", x.XFlow(session_id)),
        ("Chrome", chrome.ChromeFlow(session_id)),
    ]

    platforms = filter_platforms(all_platforms, platform)

    for platform_name, flow in platforms:
        yield from ph.emit_log("info", f"Starting platform: {platform_name}")
        yield from flow.start_flow()

    yield from ph.emit_log("info", "Study complete")
    yield ph.render_end_page()


def filter_platforms(all_platforms, platform_filter):
    """Filter platform list by VITE_PLATFORM value.

    If platform_filter is None or empty, return all platforms.
    Otherwise return only the matching platform (case-insensitive).
    """
    if not platform_filter:
        return all_platforms
    return [
        (name, flow) for name, flow in all_platforms
        if name.lower() == platform_filter.lower()
    ]
