import os
import sys

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from daily_run import list_tracked_feeds, run_daily
from notion_store import _headers


def test_list_tracked_feeds_returns_seeded_show():
    feeds = list_tracked_feeds()

    assert len(feeds) > 0
    assert any(
        "feed.firstory.me/rss/user/cm3o5681s06e801v3fxpjehwb" in url
        for url in feeds
    )


@pytest.mark.slow
def test_run_daily_processes_every_tracked_feed(tmp_path):
    results = run_daily(str(tmp_path))

    assert len(results) > 0
    for result in results:
        assert result["episode"]["title"].strip() != ""
        # freshly-seen episode: not skipped, real transcript+report+Notion page
        if not result["skipped"]:
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
