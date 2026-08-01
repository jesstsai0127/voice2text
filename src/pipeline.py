import os

import requests

from organize import organize
from transcribe import transcribe


def _download(url: str, dest_path: str) -> None:
    with requests.get(url, stream=True, timeout=300) as response:
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)


def run_episode(audio_url: str, output_dir: str) -> dict:
    os.makedirs(output_dir, exist_ok=True)

    audio_path = os.path.join(output_dir, "audio.mp3")
    _download(audio_url, audio_path)

    transcript = transcribe(audio_path)
    transcript_path = os.path.join(output_dir, "transcript.txt")
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript)

    result = organize(transcript)
    report_path = os.path.join(output_dir, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(result["report"])

    return {"transcript_path": transcript_path, "report_path": report_path}
