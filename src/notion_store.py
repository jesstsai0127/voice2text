import os

import requests

_SECRETS_FILE = os.path.expanduser("~/.secrets/voice2text-notion.env")
NOTION_VERSION = "2026-03-11"
_MAX_RICH_TEXT_CHARS = 2000
_MAX_BLOCKS_PER_REQUEST = 90


def _load_secret(name: str) -> str:
    if name in os.environ:
        return os.environ[name]
    if os.path.exists(_SECRETS_FILE):
        with open(_SECRETS_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                if key == name:
                    return value
    raise RuntimeError(f"{name} not found in environment or {_SECRETS_FILE}")


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_load_secret('NOTION_API_KEY')}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _chunk_text_to_paragraph_blocks(text: str) -> list:
    chunks = [
        text[i : i + _MAX_RICH_TEXT_CHARS]
        for i in range(0, len(text), _MAX_RICH_TEXT_CHARS)
    ] or [""]
    return [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]},
        }
        for chunk in chunks
    ]


def _heading_block(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _append_blocks(page_id: str, blocks: list) -> None:
    for i in range(0, len(blocks), _MAX_BLOCKS_PER_REQUEST):
        batch = blocks[i : i + _MAX_BLOCKS_PER_REQUEST]
        response = requests.patch(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            headers=_headers(),
            json={"children": batch},
            timeout=60,
        )
        response.raise_for_status()


def save_record(filename: str, file_size: int, transcript: str, report: str) -> str:
    create_response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=_headers(),
        json={
            "parent": {
                "type": "data_source_id",
                "data_source_id": _load_secret("NOTION_DATA_SOURCE_ID"),
            },
            "properties": {
                "檔名": {"title": [{"type": "text", "text": {"content": filename}}]},
                "檔案大小": {"number": file_size},
            },
        },
        timeout=60,
    )
    create_response.raise_for_status()
    page_id = create_response.json()["id"]

    blocks = (
        [_heading_block("逐字稿")]
        + _chunk_text_to_paragraph_blocks(transcript)
        + [_heading_block("整理報告")]
        + _chunk_text_to_paragraph_blocks(report)
    )
    _append_blocks(page_id, blocks)

    return page_id


def fetch_record(page_id: str) -> dict:
    page_response = requests.get(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=_headers(),
        timeout=60,
    )
    page_response.raise_for_status()
    props = page_response.json()["properties"]
    filename = props["檔名"]["title"][0]["plain_text"] if props["檔名"]["title"] else ""
    file_size = props["檔案大小"]["number"]

    blocks_response = requests.get(
        f"https://api.notion.com/v1/blocks/{page_id}/children",
        headers=_headers(),
        params={"page_size": 100},
        timeout=60,
    )
    blocks_response.raise_for_status()
    blocks = blocks_response.json()["results"]

    sections = {"逐字稿": [], "整理報告": []}
    current_section = None
    for block in blocks:
        if block["type"] == "heading_2":
            text = "".join(
                rt["plain_text"] for rt in block["heading_2"]["rich_text"]
            )
            current_section = text if text in sections else None
        elif block["type"] == "paragraph" and current_section:
            text = "".join(
                rt["plain_text"] for rt in block["paragraph"]["rich_text"]
            )
            sections[current_section].append(text)

    return {
        "filename": filename,
        "file_size": file_size,
        "transcript": "".join(sections["逐字稿"]),
        "report": "".join(sections["整理報告"]),
    }
