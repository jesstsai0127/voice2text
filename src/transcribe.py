import os

import requests

WHISPER_SERVER_URL = os.environ.get(
    "WHISPER_SERVER_URL", "http://localhost:8000/v1/audio/transcriptions"
)
WHISPER_MODEL = "Systran/faster-whisper-large-v3"


def transcribe(audio_path: str) -> str:
    with open(audio_path, "rb") as f:
        response = requests.post(
            WHISPER_SERVER_URL,
            files={"file": (os.path.basename(audio_path), f)},
            data={"model": WHISPER_MODEL},
            timeout=3600,
        )
    response.raise_for_status()
    return response.json()["text"]
