import os
import sys

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from daily_run import list_tracked_feeds, run_daily_podcast_check
from notion_store import _headers


def test_list_tracked_feeds_returns_seeded_show():
    feeds = list_tracked_feeds()

    assert len(feeds) > 0
    assert any(
        feed["url"] and "feed.firstory.me/rss/user/cm3o5681s06e801v3fxpjehwb" in feed["url"]
        for feed in feeds
    )
    # every feed carries its own Notion page id, so processed episodes can
    # be linked back to which tracked show they came from
    assert all(feed["page_id"] for feed in feeds)
    # the personal-audio row has no 網址 and must not be silently dropped
    assert any(feed["source_type"] == "個人上傳" for feed in feeds)


@pytest.mark.slow
def test_run_daily_podcast_check_processes_recent_tracked_episodes(tmp_path):
    # real feeds may or may not have published anything in the last few days,
    # so this only asserts on the shape of whatever comes back, not a nonzero
    # count
    results = run_daily_podcast_check(str(tmp_path))

    for result in results:
        assert result["episode"]["title"].strip() != ""
        # freshly-seen episode: not skipped, real transcript+report+Notion page
        if not result["skipped"] and not result.get("failed"):
            assert result["notion_page_id"]
            try:
                with open(result["transcript_path"], encoding="utf-8") as f:
                    assert len(f.read()) > 0
            finally:
                requests.patch(
                    f"https://api.notion.com/v1/pages/{result['notion_page_id']}",
                    headers=_headers(),
                    json={"in_trash": True},
                    timeout=60,
                ).raise_for_status()
