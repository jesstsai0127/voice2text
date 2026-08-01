import os

import requests

from notion_store import is_already_processed, save_record
from organize import organize
from transcribe import transcribe


def _download(url: str, dest_path: str) -> None:
    with requests.get(url, stream=True, timeout=300) as response:
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)


def run_episode(audio_url: str, output_dir: str, filename: str) -> dict:
    os.makedirs(output_dir, exist_ok=True)

    base_name, ext = os.path.splitext(filename)
    extension = ext.lstrip(".")

    audio_path = os.path.join(output_dir, filename)
    _download(audio_url, audio_path)
    file_size = os.path.getsize(audio_path)

    if is_already_processed(base_name, file_size, extension):
        return {"skipped": True, "reason": "duplicate"}

    transcript = transcribe(audio_path)
    transcript_path = os.path.join(output_dir, "transcript.txt")
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript)

    result = organize(transcript)
    report_path = os.path.join(output_dir, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(result["report"])

    page_id = save_record(
        filename=base_name,
        file_size=file_size,
        extension=extension,
        transcript=transcript,
        report=result["report"],
        tags=result["tags"],
    )

    return {
        "skipped": False,
        "transcript_path": transcript_path,
        "report_path": report_path,
        "notion_page_id": page_id,
    }
