import os

import requests

WHISPER_SERVER_URL = os.environ.get(
    "WHISPER_SERVER_URL", "http://localhost:8000/v1/audio/transcriptions"
)
WHISPER_MODEL = "Systran/faster-whisper-large-v3"

# second attempt forces an explicit language hint instead of relying on
# auto-detection, in case the failure/garbled result was caused by a
# language-detection misfire on noisy or accented audio
_FALLBACK_REQUEST_DATA = {"model": WHISPER_MODEL, "language": "zh"}


class TranscriptionFailedError(Exception):
    pass


def _request_transcription(audio_path: str, data: dict) -> str:
    with open(audio_path, "rb") as f:
        response = requests.post(
            WHISPER_SERVER_URL,
            files={"file": (os.path.basename(audio_path), f)},
            data=data,
            timeout=3600,
        )
    response.raise_for_status()
    return response.json()["text"]


def transcribe(audio_path: str) -> str:
    try:
        return _request_transcription(audio_path, {"model": WHISPER_MODEL})
    except requests.RequestException:
        pass

    try:
        return _request_transcription(audio_path, _FALLBACK_REQUEST_DATA)
    except requests.RequestException as e:
        raise TranscriptionFailedError(
            f"transcription failed after fallback retry: {e}"
        ) from e
