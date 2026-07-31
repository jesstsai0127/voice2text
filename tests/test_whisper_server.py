import json
import os

import pytest
import requests

WHISPER_SERVER_URL = os.environ.get(
    "WHISPER_SERVER_URL", "http://localhost:8000/v1/audio/transcriptions"
)
FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(name):
    with open(os.path.join(FIXTURE_DIR, f"{name}.json"), encoding="utf-8") as f:
        return json.load(f)


def test_known_sentence_transcribed_correctly():
    fixture = _load_fixture("known-sentence")
    audio_path = os.path.join(FIXTURE_DIR, fixture["audio"])

    with open(audio_path, "rb") as f:
        response = requests.post(
            WHISPER_SERVER_URL,
            files={"file": (fixture["audio"], f, "audio/m4a")},
            data={"model": "Systran/faster-whisper-large-v3"},
            timeout=60,
        )

    assert response.status_code == 200, (
        f"whisper-server returned {response.status_code}: {response.text}"
    )
    transcript = response.json()["text"]

    for expected in fixture["expected_text_contains"]:
        assert expected in transcript, (
            f"expected {expected!r} in transcript, got: {transcript!r}"
        )
