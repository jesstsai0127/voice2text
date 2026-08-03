import os
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import unquote, urlparse

import requests

_APPLE_PODCASTS_ID_RE = re.compile(r"/id(\d+)")


def resolve_feed_url(url: str) -> str:
    host = urlparse(url).netloc
    if "podcasts.apple.com" not in host:
        return url

    match = _APPLE_PODCASTS_ID_RE.search(url)
    if not match:
        raise ValueError(f"couldn't find an Apple Podcasts id in: {url}")
    apple_id = match.group(1)

    response = requests.get(
        "https://itunes.apple.com/lookup",
        params={"id": apple_id, "country": "tw"},
        timeout=30,
    )
    response.raise_for_status()
    results = response.json()["results"]
    if not results:
        raise ValueError(f"no iTunes lookup result for id {apple_id}")
    return results[0]["feedUrl"]


def _episode_from_item(item) -> dict:
    title = item.find("title").text or ""
    enclosure = item.find("enclosure")
    audio_url = enclosure.attrib["url"]
    published_at = parsedate_to_datetime(item.find("pubDate").text)

    # enclosure URLs here are firstory redirect wrappers ending in the real
    # filename, URL-encoded as part of the path — recover a usable filename.
    decoded_path = unquote(audio_url)
    filename = os.path.basename(urlparse(decoded_path).path)

    return {
        "title": title,
        "audio_url": audio_url,
        "filename": filename,
        "published_at": published_at.isoformat(),
    }


def find_latest_episode(feed_url: str) -> dict:
    response = requests.get(feed_url, timeout=30)
    response.raise_for_status()
    root = ET.fromstring(response.content)

    items = root.findall(".//item")
    latest = max(
        items,
        key=lambda item: parsedate_to_datetime(item.find("pubDate").text),
    )

    return _episode_from_item(latest)


def find_all_episodes(feed_url: str) -> list:
    response = requests.get(feed_url, timeout=30)
    response.raise_for_status()
    root = ET.fromstring(response.content)

    episodes = [_episode_from_item(item) for item in root.findall(".//item")]
    episodes.sort(key=lambda e: e["published_at"], reverse=True)
    return episodes
