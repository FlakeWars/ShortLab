from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError


@dataclass(frozen=True)
class TaskRoute:
    provider: str
    model: str
    base_url: str
    api_key: str
    api_key_header: str


def _provider_defaults(provider: str) -> tuple[str, str]:
    provider = provider.lower().strip()
    if provider == "openrouter":
        return "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"
    if provider == "groq":
        return "https://api.groq.com/openai/v1", "GROQ_API_KEY"
    if provider == "litellm":
        return os.getenv("LITELLM_BASE_URL", "http://localhost:4000"), "LITELLM_API_KEY"
    return "https://api.openai.com/v1", "OPENAI_API_KEY"


def _load_route(task_type: str) -> TaskRoute:
    key = task_type.upper()
    provider = os.getenv(f"LLM_ROUTE_{key}_PROVIDER", "openai").strip().lower()
    default_base, default_key_env = _provider_defaults(provider)
    base_url = os.getenv(f"LLM_ROUTE_{key}_BASE_URL", default_base).strip().rstrip("/")
    model = os.getenv(f"LLM_ROUTE_{key}_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")).strip()
    key_env = os.getenv(f"LLM_ROUTE_{key}_API_KEY_ENV", default_key_env).strip()
    api_key = os.getenv(key_env, "").strip()
    if not api_key:
        raise RuntimeError(f"Missing API key for task '{task_type}' (env: {key_env})")
    api_key_header = os.getenv(f"LLM_ROUTE_{key}_API_KEY_HEADER", "Authorization").strip()
    return TaskRoute(
        provider=provider,
        model=model,
        base_url=base_url,
        api_key=api_key,
        api_key_header=api_key_header,
    )


class LLMMediator:
    def generate_json(
        self,
        *,
        task_type: str,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        max_tokens: int = 800,
        temperature: float = 0.7,
        seed: int | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        route = _load_route(task_type)
        payload = self._build_chat_payload(
            route=route,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=json_schema,
            max_tokens=max_tokens,
            temperature=temperature,
            seed=seed,
        )
        response = self._call_chat_completion(route, payload)
        try:
            content = response["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise RuntimeError("LLM response content is not text")
            return json.loads(content), {
                "provider": route.provider,
                "model": route.model,
                "id": response.get("id"),
            }
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Failed to parse LLM JSON response: {exc}") from exc

    def _build_chat_payload(
        self,
        *,
        route: TaskRoute,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        max_tokens: int,
        temperature: float,
        seed: int | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": route.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if seed is not None:
            payload["seed"] = seed

        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": f"{route.provider}_schema",
                "schema": json_schema,
                "strict": True,
            },
        }
        return payload

    def _call_chat_completion(self, route: TaskRoute, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if route.api_key_header.lower() == "authorization":
            headers["Authorization"] = f"Bearer {route.api_key}"
        else:
            headers[route.api_key_header] = route.api_key

        body = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(
            url=f"{route.base_url}/chat/completions",
            data=body,
            method="POST",
            headers=headers,
        )
        try:
            with urlrequest.urlopen(req, timeout=45) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8")
            if exc.code in {400, 422} and "response_format" in payload:
                fallback = dict(payload)
                fallback.pop("response_format", None)
                fallback["messages"] = fallback["messages"] + [
                    {
                        "role": "system",
                        "content": "Return ONLY valid JSON matching the requested schema.",
                    }
                ]
                return self._call_chat_completion(route, fallback)
            raise RuntimeError(f"LLM API error: {exc.code} {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"LLM API unreachable: {exc}") from exc


_MEDIATOR = LLMMediator()


def get_mediator() -> LLMMediator:
    return _MEDIATOR
