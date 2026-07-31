import os

import requests

_SECRETS_FILE = os.path.expanduser("~/.secrets/ai-gateway.env")


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
    raise RuntimeError(
        f"{name} not found in environment or {_SECRETS_FILE}"
    )


SYSTEM_PROMPT = """你是一個逐字稿整理助手。你會收到一份口語逐字稿，任務是把它整理成一份精簡的 markdown 報告。

嚴格規則：
- 只能使用逐字稿裡明確提到的內容，不能加入逐字稿沒有提到的任何事實、數字、預測、建議或推論
- 不要做投資建議、買賣建議、股價預測，即使逐字稿的主題是財經相關
- 如果逐字稿內容不足以判斷某件事，就不要提，不要用「可能」「應該」這類詞去補完你不確定的資訊
- 輸出純 markdown，不要额外的開場白或客套話
"""


def organize(transcript: str) -> str:
    response = requests.post(
        _load_secret("AI_GATEWAY_URL"),
        headers={
            "Authorization": f"Bearer {_load_secret('AI_GATEWAY_KEY')}",
            "Content-Type": "application/json",
        },
        json={
            "model": "auto",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": transcript},
            ],
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
