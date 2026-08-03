import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import daily_run
from joblock import exclusive_job_lock


def _fake_episode(filename, published_at, title=None):
    return {
        "title": title or filename,
        "audio_url": f"http://example.com/{filename}",
        "filename": filename,
        "published_at": published_at.isoformat(),
    }


def _stub_common_feed_plumbing(monkeypatch, episodes):
    monkeypatch.setattr(
        daily_run,
        "list_tracked_feeds",
        lambda: [
            {
                "page_id": "feed1",
                "url": "http://example.com/feed.xml",
                "name": "測試節目",
                "source_type": "Podcast",
            }
        ],
    )
    monkeypatch.setattr(daily_run, "get_or_create_show_database", lambda page_id, name: "ds1")
    monkeypatch.setattr(daily_run, "resolve_feed_url", lambda url: url)
    monkeypatch.setattr(daily_run, "find_all_episodes", lambda feed_url: episodes)


def test_podcast_check_processes_every_recent_episode_not_just_one(monkeypatch, tmp_path):
    now = datetime.now(timezone.utc)
    episodes = [
        _fake_episode("recent1.mp3", now - timedelta(hours=1)),
        _fake_episode("recent2.mp3", now - timedelta(days=1)),
        _fake_episode("old.mp3", now - timedelta(days=10)),
    ]
    _stub_common_feed_plumbing(monkeypatch, episodes)
    monkeypatch.setenv("VOICE2TEXT_LOCK_PATH", str(tmp_path / "job.lock"))

    processed = []

    def fake_run_episode(audio_url, output_dir, filename, data_source_id, title=None, published_at=None):
        processed.append(filename)
        return {"skipped": False, "notion_page_id": f"p-{filename}"}

    monkeypatch.setattr(daily_run, "run_episode", fake_run_episode)

    daily_run.run_daily_podcast_check(str(tmp_path))

    assert processed == ["recent1.mp3", "recent2.mp3"]


def test_podcast_check_skips_entirely_if_lock_already_held(monkeypatch, tmp_path):
    lock_path = str(tmp_path / "job.lock")
    monkeypatch.setenv("VOICE2TEXT_LOCK_PATH", lock_path)

    def _should_not_be_called():
        raise AssertionError("list_tracked_feeds should not run while locked")

    monkeypatch.setattr(daily_run, "list_tracked_feeds", lambda: _should_not_be_called())

    with exclusive_job_lock(lock_path):
        result = daily_run.run_daily_podcast_check(str(tmp_path))

    assert result == []


def test_backfill_processes_up_to_batch_size_skipping_already_recorded(monkeypatch, tmp_path):
    now = datetime.now(timezone.utc)
    old_episodes = [
        _fake_episode(f"ep{i}.mp3", now - timedelta(days=10 + i)) for i in range(6)
    ]
    _stub_common_feed_plumbing(monkeypatch, old_episodes)
    monkeypatch.setenv("VOICE2TEXT_LOCK_PATH", str(tmp_path / "job.lock"))

    already_recorded = {"ep0", "ep1"}
    monkeypatch.setattr(
        daily_run, "is_filename_recorded", lambda ds, filename, ext: filename in already_recorded
    )

    processed = []

    def fake_run_episode(audio_url, output_dir, filename, data_source_id, title=None, published_at=None):
        processed.append(filename)
        return {"skipped": False, "notion_page_id": f"p-{filename}"}

    monkeypatch.setattr(daily_run, "run_episode", fake_run_episode)

    daily_run.run_podcast_backfill(str(tmp_path), batch_size=3)

    # ep0/ep1 already recorded -> skipped without counting toward the batch cap;
    # next 3 not-yet-recorded episodes (newest-first among the "older" set) get processed
    assert processed == ["ep2.mp3", "ep3.mp3", "ep4.mp3"]


def test_backfill_skips_entirely_if_lock_already_held(monkeypatch, tmp_path):
    lock_path = str(tmp_path / "job.lock")
    monkeypatch.setenv("VOICE2TEXT_LOCK_PATH", lock_path)

    def _should_not_be_called():
        raise AssertionError("list_tracked_feeds should not run while locked")

    monkeypatch.setattr(daily_run, "list_tracked_feeds", lambda: _should_not_be_called())

    with exclusive_job_lock(lock_path):
        result = daily_run.run_podcast_backfill(str(tmp_path))

    assert result == []
