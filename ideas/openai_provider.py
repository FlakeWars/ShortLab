from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError


@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    model: str
    base_url: str
    temperature: float
    max_output_tokens: int


def load_openai_config() -> OpenAIConfig:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    max_output_tokens = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "800"))
    return OpenAIConfig(
        api_key=api_key,
        model=model,
        base_url=base_url.rstrip("/"),
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )


def build_request_payload(*, prompt: str, limit: int, seed: int | None) -> dict[str, Any]:
    schema = {
        "type": "object",
        "properties": {
            "ideas": {
                "type": "array",
                "minItems": limit,
                "maxItems": limit,
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "what_to_expect": {"type": "string"},
                        "preview": {"type": "string"},
                    },
                    "required": ["title", "summary", "what_to_expect", "preview"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["ideas"],
        "additionalProperties": False,
    }

    instructions = (
        "You generate concise idea proposals for short, deterministic 2D animations. "
        "Return JSON that matches the provided schema exactly. "
        "Ideas must be distinct, short, and suitable for a 30-60s looped animation."
    )

    user_prompt = prompt.strip() if prompt else ""
    if user_prompt:
        user_prompt = f"User prompt: {user_prompt}"

    seed_hint = f"Seed: {seed}" if seed is not None else "Seed: none"

    input_text = "\n".join(
        [
            f"Generate {limit} ideas.",
            seed_hint,
            user_prompt,
        ]
    ).strip()

    return {
        "instructions": instructions,
        "input": input_text,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "idea_batch",
                "schema": schema,
                "strict": True,
            }
        },
    }


def call_openai(config: OpenAIConfig, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(
        {
            "model": config.model,
            "temperature": config.temperature,
            "max_output_tokens": config.max_output_tokens,
            "store": False,
            **payload,
        }
    ).encode("utf-8")

    req = urlrequest.Request(
        url=f"{config.base_url}/responses",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urlrequest.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"OpenAI API error: {exc.code} {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"OpenAI API unreachable: {exc}") from exc


def extract_json_output(response: dict[str, Any]) -> dict[str, Any]:
    if isinstance(response.get("output_text"), str):
        text = response["output_text"]
        return json.loads(text)

    output = response.get("output", [])
    chunks: list[str] = []
    if isinstance(output, list):
        for item in output:
            if item.get("type") != "message":
                continue
            for content in item.get("content", []) or []:
                if content.get("type") in {"output_text", "text"}:
                    chunks.append(content.get("text", ""))
    if not chunks:
        raise RuntimeError("OpenAI response missing output text")
    return json.loads("".join(chunks))
