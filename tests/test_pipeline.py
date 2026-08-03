import os
import sys
import uuid

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from notion_store import _headers, get_or_create_show_database
from pipeline import run_episode

TECHWAV_FEED_PAGE_ID = "3affa664-385e-81ff-8289-d33381432318"  # 哈利說 科技浪 Tech.wav

# 哈利說「科技浪 Tech.wav」EP1 -（試播集）全世界一起做了一個美夢
# Enclosure URL resolved manually via the show's RSS feed for this tracer-bullet
# ticket (#2). Generic feed parsing / "find the latest episode" logic is ticket #3.
EP1_AUDIO_URL = (
    "https://m.cdn.firstory.me/track/cm3o5681s06e801v3fxpjehwb/"
    "cm3o5683c06hx01v39rfk9wc5/https%3A%2F%2Ffile.cdn.firstory.me%2FRecord%2F"
    "cm3o5681s06e801v3fxpjehwb%2Fcm3po9swg02af01us7pfh321m.mp3"
)


def _archive(page_id: str) -> None:
    response = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=_headers(),
        json={"in_trash": True},
        timeout=60,
    )
    response.raise_for_status()


@pytest.mark.slow
def test_ep1_end_to_end_produces_transcript_and_report(tmp_path):
    # unique filename per run so re-running this (deliberately, not via the
    # default gate) doesn't get skipped as a duplicate of a prior run
    filename = f"ep1-{uuid.uuid4().hex[:8]}.mp3"
    data_source_id = get_or_create_show_database(TECHWAV_FEED_PAGE_ID, "哈利說 科技浪 Tech.wav")

    result = run_episode(
        EP1_AUDIO_URL, str(tmp_path), filename=filename, data_source_id=data_source_id
    )

    try:
        assert result["skipped"] is False

        with open(result["transcript_path"], encoding="utf-8") as f:
            transcript = f.read()
        with open(result["report_path"], encoding="utf-8") as f:
            report = f.read()

        # A ~45 minute episode should produce a substantial transcript.
        assert len(transcript) > 500

        # The report should exist, be non-trivial, and meaningfully shorter
        # than the full transcript (that's the whole point — 10 minutes to
        # read, not 45 minutes to listen).
        assert len(report) > 0
        assert len(report) < len(transcript)
    finally:
        _archive(result["notion_page_id"])
