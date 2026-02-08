from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
import re
from typing import Any

import os
from pathlib import Path
import time

import yaml
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

from db.models import AuditEvent, LLMMediatorBudgetDaily, LLMMediatorRouteMetric
from db.session import SessionLocal
from llm.codex_cli import CodexCliError, run_codex_cli


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
    max_tokens: int
    max_cost_usd: float


@dataclass(frozen=True)
class LLMError(Exception):
    code: str
    message: str
    provider: str
    task_type: str
    retryable: bool = False
    raw_content: str | None = None

    def __str__(self) -> str:
        return f"{self.code}({self.provider}/{self.task_type}): {self.message}"


def _provider_defaults(provider: str) -> tuple[str, str]:
    provider = provider.lower().strip()
    if provider == "gemini":
        return "https://generativelanguage.googleapis.com/v1beta", "GEMINI_API_KEY"
    if provider == "codex_cli":
        return "codex-cli", "CODEX_CLI_AUTH"
    if provider == "openrouter":
        return "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"
    if provider == "groq":
        return "https://api.groq.com/openai/v1", "GROQ_API_KEY"
    if provider == "litellm":
        return os.getenv("LITELLM_BASE_URL", "http://localhost:4000"), "LITELLM_API_KEY"
    return "https://api.openai.com/v1", "OPENAI_API_KEY"


def _default_api_key_header(provider: str) -> str:
    provider = provider.lower().strip()
    if provider == "gemini":
        return "x-goog-api-key"
    return "Authorization"

def _openai_responses_models() -> set[str]:
    raw = os.getenv("LLM_OPENAI_RESPONSES_MODELS", "").strip()
    if not raw:
        return set()
    return {item.strip() for item in raw.split(",") if item.strip()}


def _sanitize_gemini_schema(schema: Any) -> Any:
    if isinstance(schema, dict):
        cleaned: dict[str, Any] = {}
        for key, value in schema.items():
            if key == "additionalProperties":
                continue
            cleaned[key] = _sanitize_gemini_schema(value)
        return cleaned
    if isinstance(schema, list):
        return [_sanitize_gemini_schema(item) for item in schema]
    return schema


DEFAULT_TASK_PROFILES: dict[str, str] = {
    "idea_generate": "creative",
    "idea_verify_capability": "analytical",
    "idea_compile_dsl": "structured",
    "dsl_repair": "structured",
}


def _task_profile(task_type: str) -> str | None:
    key = task_type.upper()
    profile_override = os.getenv(f"LLM_TASK_PROFILE_{key}", "").strip().lower()
    if profile_override:
        return profile_override
    return DEFAULT_TASK_PROFILES.get(task_type)


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _split_env_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _load_routes(task_type: str) -> list[TaskRoute]:
    key = task_type.upper()
    profile = _task_profile(task_type)
    profile_key = f"LLM_PROFILE_{profile.upper()}_" if profile else None

    providers = _split_env_list(os.getenv(f"LLM_ROUTE_{key}_PROVIDERS"))
    models = _split_env_list(os.getenv(f"LLM_ROUTE_{key}_MODELS"))
    base_urls = _split_env_list(os.getenv(f"LLM_ROUTE_{key}_BASE_URLS"))
    key_envs = _split_env_list(os.getenv(f"LLM_ROUTE_{key}_API_KEY_ENVS"))
    key_headers = _split_env_list(os.getenv(f"LLM_ROUTE_{key}_API_KEY_HEADERS"))

    if providers or models:
        if not providers or not models:
            raise RuntimeError(f"Both PROVIDERS and MODELS must be set for task '{task_type}'")
        if len(providers) != len(models):
            raise RuntimeError(f"PROVIDERS and MODELS length mismatch for task '{task_type}'")
    else:
        provider = _first_non_empty(
            os.getenv(f"LLM_ROUTE_{key}_PROVIDER"),
            os.getenv(f"{profile_key}PROVIDER") if profile_key else None,
            "openai",
        )
        assert provider is not None
        providers = [provider]
        models = [
            _first_non_empty(
                os.getenv(f"LLM_ROUTE_{key}_MODEL"),
                os.getenv(f"{profile_key}MODEL") if profile_key else None,
                os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            )
            or "gpt-4o-mini"
        ]

    timeout_s = int(
        _first_non_empty(
            os.getenv(f"LLM_ROUTE_{key}_TIMEOUT_S"),
            os.getenv(f"{profile_key}TIMEOUT_S") if profile_key else None,
            "45",
        )
        or "45"
    )
    retries = int(
        _first_non_empty(
            os.getenv(f"LLM_ROUTE_{key}_RETRIES"),
            os.getenv(f"{profile_key}RETRIES") if profile_key else None,
            "2",
        )
        or "2"
    )
    breaker_threshold = int(
        _first_non_empty(
            os.getenv(f"LLM_ROUTE_{key}_BREAKER_THRESHOLD"),
            os.getenv(f"{profile_key}BREAKER_THRESHOLD") if profile_key else None,
            "5",
        )
        or "5"
    )
    breaker_cooldown_s = int(
        _first_non_empty(
            os.getenv(f"LLM_ROUTE_{key}_BREAKER_COOLDOWN_S"),
            os.getenv(f"{profile_key}BREAKER_COOLDOWN_S") if profile_key else None,
            "60",
        )
        or "60"
    )
    max_tokens = int(
        _first_non_empty(
            os.getenv(f"LLM_ROUTE_{key}_MAX_TOKENS"),
            os.getenv(f"{profile_key}MAX_TOKENS") if profile_key else None,
            "1200",
        )
        or "1200"
    )
    max_cost_usd = float(
        _first_non_empty(
            os.getenv(f"LLM_ROUTE_{key}_MAX_COST_USD"),
            os.getenv(f"{profile_key}MAX_COST_USD") if profile_key else None,
            "0",
        )
        or "0"
    )

    routes: list[TaskRoute] = []
    for idx, provider_value in enumerate(providers):
        provider = provider_value.lower()
        default_base, default_key_env = _provider_defaults(provider)
        base_url = (
            (base_urls[idx] if idx < len(base_urls) else None)
            or _first_non_empty(
                os.getenv(f"LLM_ROUTE_{key}_BASE_URL"),
                os.getenv(f"{profile_key}BASE_URL") if profile_key else None,
                default_base,
            )
            or default_base
        ).rstrip("/")
        key_env = (
            (key_envs[idx] if idx < len(key_envs) else None)
            or _first_non_empty(
                os.getenv(f"LLM_ROUTE_{key}_API_KEY_ENV"),
                os.getenv(f"{profile_key}API_KEY_ENV") if profile_key else None,
                default_key_env,
            )
        )
        model = models[idx] if idx < len(models) else models[0]
        assert model is not None and key_env is not None
        api_key = os.getenv(key_env, "").strip()
        if provider != "codex_cli" and not api_key:
            continue
        api_key_header = (
            (key_headers[idx] if idx < len(key_headers) else None)
            or _first_non_empty(
                os.getenv(f"LLM_ROUTE_{key}_API_KEY_HEADER"),
                os.getenv(f"{profile_key}API_KEY_HEADER") if profile_key else None,
                _default_api_key_header(provider),
            )
        )
        routes.append(
            TaskRoute(
                provider=provider,
                model=model,
                base_url=base_url,
                api_key=api_key,
                api_key_header=api_key_header or "Authorization",
                timeout_s=timeout_s,
                retries=retries,
                breaker_threshold=breaker_threshold,
                breaker_cooldown_s=breaker_cooldown_s,
                max_tokens=max_tokens,
                max_cost_usd=max_cost_usd,
            )
        )

    if not routes:
        raise RuntimeError(f"Missing API key for task '{task_type}'")
    return routes


def _load_route(task_type: str) -> TaskRoute:
    return _load_routes(task_type)[0]


class LLMMediator:
    def __init__(self) -> None:
        self._failures: dict[str, int] = {}
        self._breaker_until: dict[str, float] = {}
        self._metrics: dict[str, dict[str, float]] = {}
        self._spent_usd_total = 0.0
        self._daily_budget_usd = float(os.getenv("LLM_DAILY_BUDGET_USD", "0") or 0)
        self._budget_day = self._today_utc()
        self._token_budget_models: dict[str, int] = {}
        self._token_budget_groups: dict[str, dict[str, Any]] = {}
        self._persist_backend = os.getenv("LLM_MEDIATOR_PERSIST_BACKEND", "db").strip().lower()
        self._state_file = Path(os.getenv("LLM_MEDIATOR_STATE_FILE", ".state/llm-mediator-state.json"))
        self._load_token_budgets()
        self._load_state()

    @staticmethod
    def log_event(message: str, *, payload: dict[str, Any] | None = None) -> None:
        try:
            with SessionLocal() as session:
                session.add(
                    AuditEvent(
                        event_type="llm_token_budget",
                        source="system",
                        occurred_at=datetime.now(timezone.utc),
                        payload={"message": message, **(payload or {})},
                    )
                )
                session.commit()
        except Exception:
            return

    def get_metrics_snapshot(self) -> dict[str, Any]:
        return {
            "routes": self._metrics,
            "budget": {
                "spent_usd_total": self._spent_usd_total,
                "daily_budget_usd": self._daily_budget_usd,
                "budget_day": self._budget_day,
            },
            "state_backend": self._persist_backend,
            "state_file": str(self._state_file) if self._persist_backend != "db" else None,
        }

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
        routes = _load_routes(task_type)
        self._roll_budget_day_if_needed()
        if self._daily_budget_usd > 0 and self._spent_usd_total >= self._daily_budget_usd:
            raise LLMError(
                code="budget_exceeded",
                message="Daily LLM budget exhausted",
                provider=routes[0].provider,
                task_type=task_type,
            )
        now_ts = time.time()
        last_error: LLMError | None = None
        for route in routes:
            breaker_key = f"{task_type}:{route.provider}:{route.model}"
            if self._breaker_until.get(breaker_key, 0) > now_ts:
                continue
            payload = self._build_chat_payload(
                route=route,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_schema=json_schema,
                max_tokens=max_tokens,
                temperature=temperature,
                seed=seed,
            )
            start = time.perf_counter()
            try:
                self._assert_token_budget(task_type=task_type, provider=route.provider, model=route.model)
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
                    parsed = self._parse_json_content(content)
                except (KeyError, IndexError, TypeError, json.JSONDecodeError, LLMError) as exc:
                    fail_count = self._failures.get(breaker_key, 0) + 1
                    self._failures[breaker_key] = fail_count
                    self._track_metrics(
                        task_type=task_type,
                        provider=route.provider,
                        model=route.model,
                        success=False,
                        latency_ms=0.0,
                        prompt_tokens=0.0,
                        completion_tokens=0.0,
                        estimated_cost_usd=0.0,
                    )
                    if fail_count >= route.breaker_threshold:
                        self._breaker_until[breaker_key] = now_ts + route.breaker_cooldown_s
                    raw_content = ""
                    try:
                        raw_content = response["choices"][0]["message"]["content"]
                    except Exception:
                        raw_content = ""
                    if route.provider == "gemini" and os.getenv("LLM_GEMINI_DISABLE_REPAIR", "1") == "1":
                        exc = LLMError(
                            code="invalid_json",
                            message=f"Failed to parse LLM JSON response: {exc}",
                            provider=route.provider,
                            task_type=task_type,
                            raw_content=raw_content,
                            retryable=True,
                        )
                        raise exc
                    parsed, response = self._repair_json_response(
                        task_type=task_type,
                        route=route,
                        payload=payload,
                        content=raw_content,
                    )
                self._failures[breaker_key] = 0
                latency_ms = (time.perf_counter() - start) * 1000.0
                usage = response.get("usage", {}) if isinstance(response, dict) else {}
                prompt_tokens = float(usage.get("prompt_tokens", 0) or 0)
                completion_tokens = float(usage.get("completion_tokens", 0) or 0)
                estimated_cost = self._estimate_cost_usd(prompt_tokens, completion_tokens)
                if route.max_cost_usd > 0 and estimated_cost > route.max_cost_usd:
                    raise LLMError(
                        code="request_cost_exceeded",
                        message="Estimated request cost exceeds route cap",
                        provider=route.provider,
                        task_type=task_type,
                    )
                self._spent_usd_total += estimated_cost
                self._track_metrics(
                    task_type=task_type,
                    provider=route.provider,
                    model=route.model,
                    success=True,
                    latency_ms=latency_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    estimated_cost_usd=estimated_cost,
                )
                return parsed, {
                    "provider": route.provider,
                    "model": route.model,
                    "id": response.get("id"),
                }
            except LLMError as exc:
                last_error = exc
                if exc.code == "invalid_json" and route.provider == "gemini":
                    continue
                if exc.retryable:
                    continue
                raise
            finally:
                self._persist_state()
        if last_error is not None:
            raise last_error
        raise LLMError(
            code="no_routes",
            message="No LLM routes available",
            provider=routes[0].provider,
            task_type=task_type,
        )

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
                if attempt > 0:
                    self._track_retry(task_type=task_type, provider=route.provider, model=route.model)
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
        safe_max_tokens = max(1, min(max_tokens, route.max_tokens))
        payload: dict[str, Any] = {
            "model": route.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": safe_max_tokens,
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

    def _parse_json_content(self, content: str) -> dict[str, Any]:
        content = content.strip()
        if not content:
            raise json.JSONDecodeError("empty response", content, 0)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            try:
                parsed = yaml.safe_load(content)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
            extracted = self._extract_json_block(content)
            if extracted is None:
                raise
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                coerced = self._coerce_json_like(extracted)
                try:
                    return json.loads(coerced)
                except json.JSONDecodeError:
                    parsed = yaml.safe_load(coerced)
                    if isinstance(parsed, dict):
                        return parsed
                    raise

    def _extract_json_block(self, content: str) -> str | None:
        start = min(
            (idx for idx in (content.find("{"), content.find("[")) if idx != -1),
            default=-1,
        )
        if start == -1:
            return None
        end_obj = content.rfind("}")
        end_arr = content.rfind("]")
        end = max(end_obj, end_arr)
        if end == -1 or end <= start:
            return None
        return content[start : end + 1]

    def _coerce_json_like(self, content: str) -> str:
        # Best-effort fix for JSON-like responses (single quotes, trailing commas).
        text = content.strip()
        text = re.sub(r"(?<=\\{|,|\\s)'([^']+?)'\\s*:", r'\"\\1\":', text)
        text = re.sub(r":\\s*'([^']*?)'", lambda m: ': "' + m.group(1) + '"', text)
        text = re.sub(r",\\s*([}\\]])", r"\\1", text)
        return text

    def _repair_json_response(
        self,
        *,
        task_type: str,
        route: TaskRoute,
        payload: dict[str, Any],
        content: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        repair_payload = dict(payload)
        repair_payload.pop("response_format", None)
        messages = list(payload.get("messages", []))
        messages.append(
            {
                "role": "system",
                "content": "Return ONLY valid JSON that matches the requested schema. Do not include markdown.",
            }
        )
        if content and content.strip():
            messages.append(
                {
                    "role": "user",
                    "content": f"Reformat this into JSON only:\n{content}",
                }
            )
        repair_payload["messages"] = messages
        if route.provider == "gemini":
            # Trigger JSON-only response for Gemini via responseMimeType
            repair_payload["response_format"] = {"type": "json_object"}
        response = self._call_with_retries(task_type, route, repair_payload)
        try:
            content = response["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise LLMError(
                    code="invalid_response",
                    message="LLM response content is not text",
                    provider=route.provider,
                    task_type=task_type,
                )
            return self._parse_json_content(content), response
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, LLMError) as exc:
            raise LLMError(
                code="invalid_json",
                message=f"Failed to parse LLM JSON response: {exc}",
                provider=route.provider,
                task_type=task_type,
                raw_content=content,
            ) from exc

    def _call_chat_completion(
        self,
        task_type: str,
        route: TaskRoute,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if route.provider == "gemini":
            return self._call_gemini_generate_content(task_type, route, payload)
        if route.provider == "openai" and route.model in _openai_responses_models():
            return self._call_openai_responses(task_type, route, payload)
        if route.provider == "codex_cli":
            try:
                content = run_codex_cli(
                    system_prompt=payload["messages"][0]["content"],
                    user_prompt=payload["messages"][1]["content"],
                    json_schema=payload.get("response_format", {})
                    .get("json_schema", {})
                    .get("schema", {}),
                    model=route.model,
                    timeout_s=route.timeout_s,
                )
            except CodexCliError as exc:
                raise LLMError(
                    code="codex_cli_error",
                    message=str(exc),
                    provider=route.provider,
                    task_type=task_type,
                    retryable=True,
                ) from exc
            return {
                "id": "codex-cli",
                "choices": [{"message": {"content": content}}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0},
            }
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
                message=self._sanitize_error_message(detail),
                provider=route.provider,
                task_type=task_type,
                retryable=exc.code >= 500 or exc.code in {401, 403, 429},
            ) from exc
        except URLError as exc:
            raise LLMError(
                code="network_error",
                message=self._sanitize_error_message(str(exc)),
                provider=route.provider,
                task_type=task_type,
                retryable=True,
            ) from exc

    def _call_openai_responses(
        self,
        task_type: str,
        route: TaskRoute,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {route.api_key}"}
        messages = payload.get("messages", [])
        system_prompt = str(messages[0].get("content", "")) if len(messages) >= 1 else ""
        user_prompt = str(messages[1].get("content", "")) if len(messages) >= 2 else ""
        body: dict[str, Any] = {
            "model": route.model,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
            "temperature": payload.get("temperature"),
            "max_output_tokens": payload.get("max_tokens"),
        }
        if payload.get("seed") is not None:
            body["seed"] = payload["seed"]
        response_format = payload.get("response_format")
        if response_format:
            if isinstance(response_format, dict) and response_format.get("type") == "json_schema":
                json_schema = response_format.get("json_schema", {}) if isinstance(response_format, dict) else {}
                body["text"] = {
                    "format": {
                        "type": "json_schema",
                        "name": json_schema.get("name", "schema"),
                        "schema": json_schema.get("schema", {}),
                        "strict": bool(json_schema.get("strict", True)),
                    }
                }
            else:
                body["text"] = {"format": response_format}

        req = urlrequest.Request(
            url=f"{route.base_url}/responses",
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers=headers,
        )
        try:
            with urlrequest.urlopen(req, timeout=max(5, route.timeout_s)) as resp:
                response = json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8")
            raise LLMError(
                code=f"http_{exc.code}",
                message=self._sanitize_error_message(detail),
                provider=route.provider,
                task_type=task_type,
                retryable=exc.code >= 500 or exc.code in {401, 403, 429},
            ) from exc
        except URLError as exc:
            raise LLMError(
                code="network_error",
                message=self._sanitize_error_message(str(exc)),
                provider=route.provider,
                task_type=task_type,
                retryable=True,
            ) from exc

        output_text = response.get("output_text")
        if not output_text:
            output = response.get("output", [])
            if output:
                content = output[0].get("content", [])
                for part in content:
                    if part.get("type") == "output_text":
                        output_text = part.get("text")
                        break
        if not output_text:
            raise LLMError(
                code="invalid_response",
                message="OpenAI responses output is empty",
                provider=route.provider,
                task_type=task_type,
            )
        usage = response.get("usage", {}) if isinstance(response, dict) else {}
        prompt_tokens = usage.get("input_tokens", 0) or 0
        completion_tokens = usage.get("output_tokens", 0) or 0
        return {
            "id": response.get("id"),
            "choices": [{"message": {"content": output_text}}],
            "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
        }

    def _sanitize_error_message(self, message: str) -> str:
        text = (message or "").replace("\n", " ")
        text = text.replace("Bearer ", "Bearer [redacted]")
        return text[:300]

    def _call_gemini_generate_content(
        self,
        task_type: str,
        route: TaskRoute,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        headers[route.api_key_header] = route.api_key
        messages = payload.get("messages", [])
        system_prompt = ""
        user_prompt = ""
        if len(messages) >= 1:
            system_prompt = str(messages[0].get("content", ""))
        if len(messages) >= 2:
            user_prompt = str(messages[1].get("content", ""))
        generation_config = {
            "temperature": payload.get("temperature"),
            "maxOutputTokens": payload.get("max_tokens"),
        }
        response_format = payload.get("response_format")
        if response_format:
            generation_config["responseMimeType"] = "application/json"
            schema = (
                response_format.get("json_schema", {}).get("schema")
                if isinstance(response_format, dict)
                else None
            )
            if schema:
                generation_config["responseSchema"] = _sanitize_gemini_schema(schema)

        body = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": user_prompt,
                        }
                    ]
                }
            ],
            "generationConfig": generation_config,
        }
        if system_prompt:
            body["system_instruction"] = {"parts": [{"text": system_prompt}]}

        req = urlrequest.Request(
            url=f"{route.base_url}/models/{route.model}:generateContent",
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers=headers,
        )
        try:
            with urlrequest.urlopen(req, timeout=max(5, route.timeout_s)) as resp:
                response = json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8")
            raise LLMError(
                code=f"http_{exc.code}",
                message=self._sanitize_error_message(detail),
                provider=route.provider,
                task_type=task_type,
                retryable=exc.code >= 500 or exc.code in {401, 403, 429},
            ) from exc
        except URLError as exc:
            raise LLMError(
                code="network_error",
                message=self._sanitize_error_message(str(exc)),
                provider=route.provider,
                task_type=task_type,
                retryable=True,
            ) from exc

        candidates = response.get("candidates") if isinstance(response, dict) else None
        if not candidates:
            raise LLMError(
                code="invalid_response",
                message="Gemini response missing candidates",
                provider=route.provider,
                task_type=task_type,
            )
        parts = candidates[0].get("content", {}).get("parts", [])
        text_chunks = [part.get("text", "") for part in parts if isinstance(part, dict)]
        content = "".join(text_chunks).strip()
        if not content:
            raise LLMError(
                code="invalid_response",
                message="Gemini response content is empty",
                provider=route.provider,
                task_type=task_type,
            )
        usage = response.get("usageMetadata", {}) if isinstance(response, dict) else {}
        return {
            "id": response.get("responseId"),
            "choices": [{"message": {"content": content}}],
            "usage": {
                "prompt_tokens": usage.get("promptTokenCount", 0) or 0,
                "completion_tokens": usage.get("candidatesTokenCount", 0) or 0,
            },
        }

    def _estimate_cost_usd(self, prompt_tokens: float, completion_tokens: float) -> float:
        in_rate = float(os.getenv("LLM_PRICE_DEFAULT_INPUT_PER_1K", "0") or 0)
        out_rate = float(os.getenv("LLM_PRICE_DEFAULT_OUTPUT_PER_1K", "0") or 0)
        if in_rate <= 0 and out_rate <= 0:
            return 0.0
        return (prompt_tokens / 1000.0) * in_rate + (completion_tokens / 1000.0) * out_rate

    def _track_metrics(
        self,
        *,
        task_type: str,
        provider: str,
        model: str,
        success: bool,
        latency_ms: float,
        prompt_tokens: float,
        completion_tokens: float,
        estimated_cost_usd: float,
    ) -> None:
        key = f"{task_type}|{provider}|{model}"
        bucket = self._metrics.setdefault(
            key,
            {
                "calls": 0.0,
                "success": 0.0,
                "errors": 0.0,
                "retries": 0.0,
                "latency_ms_total": 0.0,
                "prompt_tokens_total": 0.0,
                "completion_tokens_total": 0.0,
                "estimated_cost_usd_total": 0.0,
            },
        )
        bucket["calls"] += 1
        if success:
            bucket["success"] += 1
            bucket["latency_ms_total"] += max(0.0, latency_ms)
            bucket["prompt_tokens_total"] += max(0.0, prompt_tokens)
            bucket["completion_tokens_total"] += max(0.0, completion_tokens)
            bucket["estimated_cost_usd_total"] += max(0.0, estimated_cost_usd)
        else:
            bucket["errors"] += 1

    def _track_retry(self, *, task_type: str, provider: str, model: str) -> None:
        key = f"{task_type}|{provider}|{model}"
        bucket = self._metrics.setdefault(
            key,
            {
                "calls": 0.0,
                "success": 0.0,
                "errors": 0.0,
                "retries": 0.0,
                "latency_ms_total": 0.0,
                "prompt_tokens_total": 0.0,
                "completion_tokens_total": 0.0,
                "estimated_cost_usd_total": 0.0,
            },
        )
        bucket["retries"] += 1

    def _today_utc(self) -> str:
        return time.strftime("%Y-%m-%d", time.gmtime())

    def _roll_budget_day_if_needed(self) -> None:
        today = self._today_utc()
        if today != self._budget_day:
            self._budget_day = today
            self._spent_usd_total = 0.0
            self._metrics = {}

    def _load_token_budgets(self) -> None:
        raw = os.getenv("LLM_TOKEN_BUDGETS", "").strip()
        if not raw:
            return
        try:
            data = json.loads(raw)
        except Exception:
            return
        if not isinstance(data, dict):
            return
        models = data.get("models")
        if isinstance(models, dict):
            for key, limit in models.items():
                try:
                    self._token_budget_models[str(key)] = int(limit)
                except Exception:
                    continue
        groups = data.get("groups")
        if isinstance(groups, dict):
            for name, payload in groups.items():
                if isinstance(payload, dict):
                    limit = payload.get("limit")
                    members = payload.get("members", [])
                else:
                    limit = payload
                    members = []
                try:
                    limit_value = int(limit)
                except Exception:
                    continue
                member_list = [str(m) for m in members if m]
                self._token_budget_groups[str(name)] = {
                    "limit": limit_value,
                    "members": member_list,
                }

    def _tokens_used_for_model(self, *, provider: str, model: str) -> float:
        total = 0.0
        for key, bucket in self._metrics.items():
            _, key_provider, key_model = self._route_key_parts(key)
            if key_provider == provider and key_model == model:
                total += float(bucket.get("prompt_tokens_total", 0.0) or 0.0)
                total += float(bucket.get("completion_tokens_total", 0.0) or 0.0)
        return total

    def _tokens_used_for_group(self, *, members: list[str]) -> float:
        total = 0.0
        for member in members:
            if ":" not in member:
                continue
            provider, model = member.split(":", 1)
            total += self._tokens_used_for_model(provider=provider, model=model)
        return total

    def _assert_token_budget(self, *, task_type: str, provider: str, model: str) -> None:
        model_key = f"{provider}:{model}"
        limit = self._token_budget_models.get(model_key)
        if limit is not None:
            used = self._tokens_used_for_model(provider=provider, model=model)
            if used >= limit:
                self.log_event(
                    "model_token_budget_exceeded",
                    payload={
                        "task_type": task_type,
                        "provider": provider,
                        "model": model,
                        "limit": limit,
                        "used": int(used),
                    },
                )
                raise LLMError(
                    code="token_budget_exceeded",
                    message=f"Token budget exceeded for model {model_key}",
                    provider=provider,
                    task_type=task_type,
                )
        for group_name, payload in self._token_budget_groups.items():
            members = payload.get("members", [])
            if model_key not in members:
                continue
            group_limit = int(payload.get("limit", 0) or 0)
            if group_limit <= 0:
                continue
            used = self._tokens_used_for_group(members=members)
            if used >= group_limit:
                self.log_event(
                    "group_token_budget_exceeded",
                    payload={
                        "task_type": task_type,
                        "group": group_name,
                        "limit": group_limit,
                        "used": int(used),
                    },
                )
                raise LLMError(
                    code="token_budget_exceeded",
                    message=f"Token budget exceeded for group {group_name}",
                    provider=provider,
                    task_type=task_type,
                )

    def _load_state(self) -> None:
        if self._persist_backend == "db" and self._load_state_db():
            return
        self._load_state_file()

    def _load_state_file(self) -> None:
        try:
            if not self._state_file.exists():
                return
            data = json.loads(self._state_file.read_text())
            if not isinstance(data, dict):
                return
            self._metrics = data.get("routes", {}) if isinstance(data.get("routes"), dict) else {}
            budget = data.get("budget", {})
            if isinstance(budget, dict):
                self._budget_day = str(budget.get("budget_day", self._budget_day))
                self._spent_usd_total = float(budget.get("spent_usd_total", 0.0) or 0.0)
            self._roll_budget_day_if_needed()
        except Exception:
            # Non-fatal: mediator should still work without persisted state.
            self._metrics = {}
            self._spent_usd_total = 0.0
            self._budget_day = self._today_utc()

    def _persist_state(self) -> None:
        if self._persist_backend == "db":
            if self._persist_state_db():
                return
        self._persist_state_file()

    def _persist_state_file(self) -> None:
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "routes": self._metrics,
                "budget": {
                    "budget_day": self._budget_day,
                    "spent_usd_total": self._spent_usd_total,
                    "daily_budget_usd": self._daily_budget_usd,
                },
            }
            tmp = self._state_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=True))
            tmp.replace(self._state_file)
        except Exception:
            # Non-fatal: failure to persist should not block runtime calls.
            return

    def _load_state_db(self) -> bool:
        try:
            with SessionLocal() as session:
                latest_budget = (
                    session.query(LLMMediatorBudgetDaily)
                    .order_by(LLMMediatorBudgetDaily.day.desc())
                    .limit(1)
                    .one_or_none()
                )
                if latest_budget:
                    self._budget_day = latest_budget.day.isoformat()
                    self._spent_usd_total = float(latest_budget.spent_usd_total or 0.0)
                    if latest_budget.daily_budget_usd is not None:
                        self._daily_budget_usd = float(latest_budget.daily_budget_usd)
                self._roll_budget_day_if_needed()
                current_day = self._parse_day(self._budget_day)
                metrics = (
                    session.query(LLMMediatorRouteMetric)
                    .filter(LLMMediatorRouteMetric.day == current_day)
                    .all()
                )
                loaded: dict[str, dict[str, float]] = {}
                for row in metrics:
                    key = f"{row.task_type}|{row.provider}|{row.model}"
                    loaded[key] = {
                        "calls": float(row.calls or 0),
                        "success": float(row.success or 0),
                        "errors": float(row.errors or 0),
                        "retries": float(row.retries or 0),
                        "latency_ms_total": float(row.latency_ms_total or 0),
                        "prompt_tokens_total": float(row.prompt_tokens_total or 0),
                        "completion_tokens_total": float(row.completion_tokens_total or 0),
                        "estimated_cost_usd_total": float(row.estimated_cost_usd_total or 0),
                    }
                self._metrics = loaded
            return True
        except Exception:
            self._metrics = {}
            self._spent_usd_total = 0.0
            self._budget_day = self._today_utc()
            return False

    def _persist_state_db(self) -> bool:
        try:
            day_value = self._parse_day(self._budget_day)
            with SessionLocal() as session:
                budget_row = session.get(LLMMediatorBudgetDaily, day_value)
                if budget_row is None:
                    budget_row = LLMMediatorBudgetDaily(day=day_value)
                    session.add(budget_row)
                budget_row.spent_usd_total = self._spent_usd_total
                budget_row.daily_budget_usd = self._daily_budget_usd

                for key, bucket in self._metrics.items():
                    task_type, provider, model = self._route_key_parts(key)
                    metric_row = (
                        session.query(LLMMediatorRouteMetric)
                        .filter(
                            LLMMediatorRouteMetric.day == day_value,
                            LLMMediatorRouteMetric.task_type == task_type,
                            LLMMediatorRouteMetric.provider == provider,
                            LLMMediatorRouteMetric.model == model,
                        )
                        .one_or_none()
                    )
                    if metric_row is None:
                        metric_row = LLMMediatorRouteMetric(
                            day=day_value,
                            task_type=task_type,
                            provider=provider,
                            model=model,
                        )
                        session.add(metric_row)
                    metric_row.calls = int(bucket.get("calls", 0) or 0)
                    metric_row.success = int(bucket.get("success", 0) or 0)
                    metric_row.errors = int(bucket.get("errors", 0) or 0)
                    metric_row.retries = int(bucket.get("retries", 0) or 0)
                    metric_row.latency_ms_total = float(bucket.get("latency_ms_total", 0) or 0)
                    metric_row.prompt_tokens_total = int(bucket.get("prompt_tokens_total", 0) or 0)
                    metric_row.completion_tokens_total = int(bucket.get("completion_tokens_total", 0) or 0)
                    metric_row.estimated_cost_usd_total = float(bucket.get("estimated_cost_usd_total", 0) or 0)
                session.commit()
            return True
        except Exception:
            return False

    def _parse_day(self, day_value: str) -> date:
        return date.fromisoformat(day_value)

    def _route_key_parts(self, key: str) -> tuple[str, str, str]:
        task_type, provider, model = key.split("|", 2)
        return task_type, provider, model


_MEDIATOR = LLMMediator()


def get_mediator() -> LLMMediator:
    return _MEDIATOR
