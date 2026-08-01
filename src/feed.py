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


def find_latest_episode(feed_url: str) -> dict:
    response = requests.get(feed_url, timeout=30)
    response.raise_for_status()
    root = ET.fromstring(response.content)

    items = root.findall(".//item")
    latest = max(
        items,
        key=lambda item: parsedate_to_datetime(item.find("pubDate").text),
    )

    title = latest.find("title").text or ""
    enclosure = latest.find("enclosure")
    audio_url = enclosure.attrib["url"]

    # enclosure URLs here are firstory redirect wrappers ending in the real
    # filename, URL-encoded as part of the path — recover a usable filename.
    decoded_path = unquote(audio_url)
    filename = os.path.basename(urlparse(decoded_path).path)

    return {"title": title, "audio_url": audio_url, "filename": filename}
