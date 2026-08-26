"""OpenAI-compatible LLM client with retries, JSON coercion and graceful fallback."""
import json
import logging
import re
from typing import Any

import httpx

from app.config import settings

log = logging.getLogger("llm")


class LLMError(Exception):
    pass


def _extract_json_block(text: str) -> Any:
    """Pull the first JSON object/array out of a model response."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # find first { ... } or [ ... ] balanced-ish
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == opener:
                depth += 1
            elif text[i] == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
    raise LLMError("no json found in response")


def chat(
    messages: list[dict],
    *,
    max_tokens: int = 4000,
    temperature: float = 0.1,
    timeout: float = 150.0,
    retries: int = 1,
) -> str:
    """Raw chat completion. Raises LLMError on failure."""
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = httpx.post(
                f"{settings.llm_base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model,
                    "messages": messages,
                    "max_completion_tokens": max_tokens,
                },
                timeout=timeout,
            )
            if resp.status_code != 200:
                raise LLMError(f"llm http {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            log.warning("llm attempt %s failed: %s", attempt + 1, exc)
    raise LLMError(str(last_err))


def chat_json(messages: list[dict], **kw) -> Any:
    raw = chat(messages, **kw)
    return _extract_json_block(raw)


def available() -> bool:
    return bool(settings.llm_api_key)
