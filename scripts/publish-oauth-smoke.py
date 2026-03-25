#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

YOUTUBE_TOKEN_URL = "https://oauth2.googleapis.com/token"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"


@dataclass(slots=True)
class ProviderResult:
    provider: str
    status: str
    detail: str
    http_status: int | None = None
    issued_at: str | None = None
    expires_in: int | None = None
    scope: str | None = None
    open_id: str | None = None
    refresh_token_rotated: bool | None = None


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _post_form(url: str, data: dict[str, str], timeout_s: int) -> tuple[int, dict[str, Any]]:
    encoded = urlencode(data).encode("utf-8")
    request = Request(
        url=url,
        data=encoded,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "shortlab-oauth-smoke/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_s) as response:  # noqa: S310
            status = response.getcode()
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        payload = _try_json(body)
        return exc.code, payload
    except URLError as exc:
        return 0, {"error": "network_error", "error_description": str(exc)}
    payload = _try_json(body)
    return status, payload


def _try_json(value: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        payload = {"raw": value}
    if isinstance(payload, dict):
        return payload
    return {"raw": payload}


def _mask(text: str | None) -> str | None:
    if text is None:
        return None
    if len(text) <= 8:
        return "***"
    return f"{text[:4]}...{text[-4:]}"


def _youtube_smoke(timeout_s: int, online: bool) -> ProviderResult:
    client_id = (os.getenv("YOUTUBE_CLIENT_ID", "") or "").strip()
    client_secret = (os.getenv("YOUTUBE_CLIENT_SECRET", "") or "").strip()
    refresh_token = (os.getenv("YOUTUBE_REFRESH_TOKEN", "") or "").strip()
    missing = [
        key
        for key, val in [
            ("YOUTUBE_CLIENT_ID", client_id),
            ("YOUTUBE_CLIENT_SECRET", client_secret),
            ("YOUTUBE_REFRESH_TOKEN", refresh_token),
        ]
        if not val
    ]
    if missing:
        return ProviderResult(
            provider="youtube",
            status="skipped",
            detail=f"missing env: {', '.join(missing)}",
        )
    if not online:
        return ProviderResult(
            provider="youtube",
            status="skipped",
            detail="online mode disabled",
        )

    status_code, payload = _post_form(
        YOUTUBE_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout_s=timeout_s,
    )
    access_token = payload.get("access_token")
    if status_code == 200 and isinstance(access_token, str) and access_token:
        return ProviderResult(
            provider="youtube",
            status="passed",
            detail=f"token refresh OK (access_token={_mask(access_token)})",
            http_status=status_code,
            issued_at=_utc_now_iso(),
            expires_in=int(payload.get("expires_in", 0) or 0),
            scope=str(payload.get("scope", "")) or None,
        )
    err = payload.get("error_description") or payload.get("error") or "unknown_error"
    return ProviderResult(
        provider="youtube",
        status="failed",
        detail=f"token refresh failed: {err}",
        http_status=status_code if status_code > 0 else None,
    )


def _tiktok_smoke(timeout_s: int, online: bool) -> ProviderResult:
    client_key = (os.getenv("TIKTOK_CLIENT_KEY", "") or "").strip()
    client_secret = (os.getenv("TIKTOK_CLIENT_SECRET", "") or "").strip()
    refresh_token = (os.getenv("TIKTOK_REFRESH_TOKEN", "") or "").strip()
    missing = [
        key
        for key, val in [
            ("TIKTOK_CLIENT_KEY", client_key),
            ("TIKTOK_CLIENT_SECRET", client_secret),
            ("TIKTOK_REFRESH_TOKEN", refresh_token),
        ]
        if not val
    ]
    if missing:
        return ProviderResult(
            provider="tiktok",
            status="skipped",
            detail=f"missing env: {', '.join(missing)}",
        )
    if not online:
        return ProviderResult(
            provider="tiktok",
            status="skipped",
            detail="online mode disabled",
        )

    status_code, payload = _post_form(
        TIKTOK_TOKEN_URL,
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout_s=timeout_s,
    )
    access_token = payload.get("access_token")
    new_refresh = payload.get("refresh_token")
    if status_code == 200 and isinstance(access_token, str) and access_token:
        rotated = isinstance(new_refresh, str) and bool(new_refresh) and new_refresh != refresh_token
        return ProviderResult(
            provider="tiktok",
            status="passed",
            detail=f"token refresh OK (access_token={_mask(access_token)})",
            http_status=status_code,
            issued_at=_utc_now_iso(),
            expires_in=int(payload.get("expires_in", 0) or 0),
            scope=str(payload.get("scope", "")) or None,
            open_id=str(payload.get("open_id", "")) or None,
            refresh_token_rotated=rotated,
        )
    err = payload.get("error_description") or payload.get("message") or payload.get("error") or "unknown_error"
    return ProviderResult(
        provider="tiktok",
        status="failed",
        detail=f"token refresh failed: {err}",
        http_status=status_code if status_code > 0 else None,
    )


def _to_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Publish OAuth Smoke Report")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{payload['generated_at']}`")
    lines.append(f"- Online mode: `{payload['online_mode']}`")
    lines.append(f"- Policy require: `{payload['require']}`")
    lines.append("")
    lines.append("| Provider | Status | Detail |")
    lines.append("|---|---|---|")
    for item in payload["results"]:
        lines.append(f"| `{item['provider']}` | `{item['status']}` | {item['detail']} |")
    lines.append("")
    lines.append("## Raw")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(payload, ensure_ascii=True, indent=2))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sandbox smoke test for YouTube/TikTok OAuth refresh token flow."
    )
    parser.add_argument("--out-dir", default="out/reports", help="Output directory for report files")
    parser.add_argument("--timeout-s", type=int, default=20, help="HTTP timeout in seconds")
    parser.add_argument(
        "--online",
        action="store_true",
        help="Execute live refresh requests when required env vars are present",
    )
    parser.add_argument(
        "--require",
        choices=["none", "passed_if_configured", "passed_all"],
        default="none",
        help=(
            "Fail policy: "
            "none=no fail; "
            "passed_if_configured=fail only when configured provider does not pass; "
            "passed_all=both providers must pass"
        ),
    )
    args = parser.parse_args()

    results = [
        _youtube_smoke(timeout_s=args.timeout_s, online=args.online),
        _tiktok_smoke(timeout_s=args.timeout_s, online=args.online),
    ]
    result_payloads = [asdict(item) for item in results]

    report = {
        "generated_at": _utc_now_iso(),
        "online_mode": args.online,
        "require": args.require,
        "results": result_payloads,
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = out_dir / f"publish-oauth-smoke-{stamp}.json"
    md_path = out_dir / f"publish-oauth-smoke-{stamp}.md"
    latest_json_path = out_dir / "publish-oauth-smoke-latest.json"
    latest_md_path = out_dir / "publish-oauth-smoke-latest.md"

    json_text = json.dumps(report, ensure_ascii=True, indent=2)
    md_text = _to_markdown(report)
    json_path.write_text(json_text + "\n", encoding="utf-8")
    md_path.write_text(md_text, encoding="utf-8")
    latest_json_path.write_text(json_text + "\n", encoding="utf-8")
    latest_md_path.write_text(md_text, encoding="utf-8")

    print(f"[oauth-smoke] JSON: {json_path}")
    print(f"[oauth-smoke] Markdown: {md_path}")
    print(f"[oauth-smoke] Latest JSON: {latest_json_path}")
    print(f"[oauth-smoke] Latest Markdown: {latest_md_path}")

    if args.require == "none":
        return 0

    statuses = {item.provider: item.status for item in results}
    configured = {
        item.provider
        for item in results
        if not str(item.detail).startswith("missing env:")
    }

    if args.require == "passed_all":
        if statuses.get("youtube") == "passed" and statuses.get("tiktok") == "passed":
            return 0
        return 2

    # passed_if_configured
    for provider in configured:
        if statuses.get(provider) != "passed":
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
