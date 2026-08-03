import os

import requests

from notion_store import is_already_processed, save_record, update_record
from organize import organize
from transcribe import transcribe


def _download(url: str, dest_path: str) -> None:
    with requests.get(url, stream=True, timeout=300) as response:
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)


def _transcribe_and_organize(audio_path: str, output_dir: str) -> tuple:
    transcript = transcribe(audio_path)
    transcript_path = os.path.join(output_dir, "transcript.txt")
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript)

    result = organize(transcript)
    report_path = os.path.join(output_dir, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(result["report"])

    return transcript, result, transcript_path, report_path


def run_episode(
    audio_url: str,
    output_dir: str,
    filename: str,
    data_source_id: str,
    title: str = None,
) -> dict:
    os.makedirs(output_dir, exist_ok=True)

    base_name, ext = os.path.splitext(filename)
    extension = ext.lstrip(".")

    audio_path = os.path.join(output_dir, filename)
    _download(audio_url, audio_path)
    file_size = os.path.getsize(audio_path)

    if is_already_processed(data_source_id, base_name, file_size, extension):
        return {"skipped": True, "reason": "duplicate"}

    transcript, result, transcript_path, report_path = _transcribe_and_organize(
        audio_path, output_dir
    )

    page_id = save_record(
        data_source_id=data_source_id,
        filename=base_name,
        file_size=file_size,
        extension=extension,
        transcript=transcript,
        report=result["report"],
        tags=result["tags"],
        title=title,
    )

    return {
        "skipped": False,
        "transcript_path": transcript_path,
        "report_path": report_path,
        "notion_page_id": page_id,
    }


def process_pending_upload(
    page_id: str, file_url: str, filename: str, output_dir: str, data_source_id: str
) -> dict:
    os.makedirs(output_dir, exist_ok=True)

    base_name, ext = os.path.splitext(filename)
    extension = ext.lstrip(".")

    audio_path = os.path.join(output_dir, filename)
    _download(file_url, audio_path)
    file_size = os.path.getsize(audio_path)

    if is_already_processed(data_source_id, base_name, file_size, extension):
        return {"skipped": True, "reason": "duplicate"}

    transcript, result, transcript_path, report_path = _transcribe_and_organize(
        audio_path, output_dir
    )

    update_record(
        page_id=page_id,
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
