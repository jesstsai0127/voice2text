import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from organize import organize

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(name):
    with open(os.path.join(FIXTURE_DIR, f"{name}.json"), encoding="utf-8") as f:
        return json.load(f)


def test_report_stays_grounded_in_transcript():
    fixture = _load_fixture("nvidia-transcript")

    result = organize(fixture["transcript"])
    report = result["report"]

    assert report.strip() != ""

    for alternatives in fixture["must_mention_any_of"]:
        assert any(alt in report for alt in alternatives), (
            f"expected one of {alternatives!r} to appear in report, got: {report!r}"
        )

    for must_not in fixture["must_not_mention"]:
        assert must_not not in report, (
            f"{must_not!r} should not appear (not in transcript) but was found in report: {report!r}"
        )


def test_tech_content_gets_tagged_as_ai_tech():
    fixture = _load_fixture("nvidia-transcript")

    result = organize(fixture["transcript"])

    assert len(result["tags"]) > 0
    assert any(
        "AI" in tag or "科技" in tag for tag in result["tags"]
    ), f"expected an AI/tech-ish tag, got: {result['tags']!r}"
