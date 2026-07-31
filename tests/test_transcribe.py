import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from transcribe import transcribe

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(name):
    with open(os.path.join(FIXTURE_DIR, f"{name}.json"), encoding="utf-8") as f:
        return json.load(f)


def test_known_sentence_transcribed_correctly():
    fixture = _load_fixture("known-sentence")
    audio_path = os.path.join(FIXTURE_DIR, fixture["audio"])

    text = transcribe(audio_path)

    for expected in fixture["expected_text_contains"]:
        assert expected in text, f"expected {expected!r} in transcript, got: {text!r}"
