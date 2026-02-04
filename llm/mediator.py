from __future__ import annotations

from dataclasses import dataclass
import json
import os
import time
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
    timeout_s: int
    retries: int
    breaker_threshold: int
    breaker_cooldown_s: int


@dataclass(frozen=True)
class LLMError(Exception):
    code: str
    message: str
    provider: str
    task_type: str
    retryable: bool = False

    def __str__(self) -> str:
        return f"{self.code}({self.provider}/{self.task_type}): {self.message}"


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
    timeout_s = int(os.getenv(f"LLM_ROUTE_{key}_TIMEOUT_S", "45"))
    retries = int(os.getenv(f"LLM_ROUTE_{key}_RETRIES", "2"))
    breaker_threshold = int(os.getenv(f"LLM_ROUTE_{key}_BREAKER_THRESHOLD", "5"))
    breaker_cooldown_s = int(os.getenv(f"LLM_ROUTE_{key}_BREAKER_COOLDOWN_S", "60"))
    return TaskRoute(
        provider=provider,
        model=model,
        base_url=base_url,
        api_key=api_key,
        api_key_header=api_key_header,
        timeout_s=timeout_s,
        retries=retries,
        breaker_threshold=breaker_threshold,
        breaker_cooldown_s=breaker_cooldown_s,
    )


class LLMMediator:
    def __init__(self) -> None:
        self._failures: dict[str, int] = {}
        self._breaker_until: dict[str, float] = {}

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
        breaker_key = f"{task_type}:{route.provider}"
        now_ts = time.time()
        if self._breaker_until.get(breaker_key, 0) > now_ts:
            raise LLMError(
                code="circuit_open",
                message="Circuit breaker active for task/provider route",
                provider=route.provider,
                task_type=task_type,
                retryable=True,
            )
        payload = self._build_chat_payload(
            route=route,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=json_schema,
            max_tokens=max_tokens,
            temperature=temperature,
            seed=seed,
        )
        response = self._call_with_retries(task_type, route, payload)
        try:
            content = response["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise LLMError(
                    code="invalid_response",
                    message="LLM response content is not text",
                    provider=route.provider,
                    task_type=task_type,
                )
            self._failures[breaker_key] = 0
            return json.loads(content), {
                "provider": route.provider,
                "model": route.model,
                "id": response.get("id"),
            }
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, LLMError) as exc:
            fail_count = self._failures.get(breaker_key, 0) + 1
            self._failures[breaker_key] = fail_count
            if fail_count >= route.breaker_threshold:
                self._breaker_until[breaker_key] = now_ts + route.breaker_cooldown_s
            if isinstance(exc, LLMError):
                raise exc
            raise LLMError(
                code="invalid_json",
                message=f"Failed to parse LLM JSON response: {exc}",
                provider=route.provider,
                task_type=task_type,
            ) from exc

    def _call_with_retries(
        self,
        task_type: str,
        route: TaskRoute,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        last_error: LLMError | None = None
        for attempt in range(route.retries + 1):
            try:
                return self._call_chat_completion(task_type, route, payload)
            except LLMError as exc:
                last_error = exc
                if not exc.retryable or attempt >= route.retries:
                    break
                time.sleep(min(2**attempt, 3))
        assert last_error is not None
        raise last_error

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

    def _call_chat_completion(
        self,
        task_type: str,
        route: TaskRoute,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
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
            with urlrequest.urlopen(req, timeout=max(5, route.timeout_s)) as resp:
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
                return self._call_chat_completion(task_type, route, fallback)
            raise LLMError(
                code=f"http_{exc.code}",
                message=detail[:300],
                provider=route.provider,
                task_type=task_type,
                retryable=exc.code >= 500 or exc.code == 429,
            ) from exc
        except URLError as exc:
            raise LLMError(
                code="network_error",
                message=str(exc),
                provider=route.provider,
                task_type=task_type,
                retryable=True,
            ) from exc


_MEDIATOR = LLMMediator()


def get_mediator() -> LLMMediator:
    return _MEDIATOR
