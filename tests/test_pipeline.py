import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pipeline import run_episode

# 哈利說「科技浪 Tech.wav」EP1 -（試播集）全世界一起做了一個美夢
# Enclosure URL resolved manually via the show's RSS feed for this tracer-bullet
# ticket (#2). Generic feed parsing / "find the latest episode" logic is ticket #3.
EP1_AUDIO_URL = (
    "https://m.cdn.firstory.me/track/cm3o5681s06e801v3fxpjehwb/"
    "cm3o5683c06hx01v39rfk9wc5/https%3A%2F%2Ffile.cdn.firstory.me%2FRecord%2F"
    "cm3o5681s06e801v3fxpjehwb%2Fcm3po9swg02af01us7pfh321m.mp3"
)


@pytest.mark.slow
def test_ep1_end_to_end_produces_transcript_and_report(tmp_path):
    result = run_episode(EP1_AUDIO_URL, str(tmp_path))

    with open(result["transcript_path"], encoding="utf-8") as f:
        transcript = f.read()
    with open(result["report_path"], encoding="utf-8") as f:
        report = f.read()

    # A ~45 minute episode should produce a substantial transcript.
    assert len(transcript) > 500

    # The report should exist, be non-trivial, and meaningfully shorter than
    # the full transcript (that's the whole point — 10 minutes to read, not
    # 45 minutes to listen).
    assert len(report) > 0
    assert len(report) < len(transcript)
