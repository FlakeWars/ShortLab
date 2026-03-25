#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

DEFAULT_REGISTRY_BASE = "https://registry.modelcontextprotocol.io"
DEFAULT_SERVERS = [
    "io.github.wmarceau/youtube-creator",
    "io.github.wmarceau/tiktok-creator",
]

EXPECTED_ENVS: dict[str, set[str]] = {
    "io.github.wmarceau/youtube-creator": {"YOUTUBE_CREDENTIALS_PATH", "YOUTUBE_TOKEN_PATH"},
    "io.github.wmarceau/tiktok-creator": {
        "TIKTOK_CLIENT_KEY",
        "TIKTOK_CLIENT_SECRET",
        "TIKTOK_ACCESS_TOKEN",
        "TIKTOK_REFRESH_TOKEN",
    },
}


@dataclass(slots=True)
class Check:
    name: str
    ok: bool
    detail: str
    severity: str = "medium"


def _http_get_json(url: str, timeout_s: int) -> Any:
    request = Request(
        url=url,
        headers={
            "User-Agent": "shortlab-mcp-audit/1.0",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=timeout_s) as response:  # noqa: S310
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def _iso_to_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _parse_github_repo(url: str | None) -> tuple[str, str] | None:
    if not url:
        return None
    match = re.match(r"^https://github\.com/([^/]+)/([^/]+?)/?$", url.strip())
    if not match:
        return None
    owner = match.group(1)
    repo = match.group(2)
    return owner, repo


def _fetch_registry_server(registry_base: str, server_name: str, timeout_s: int) -> dict[str, Any]:
    encoded = quote(server_name, safe="")
    url = f"{registry_base.rstrip('/')}/v0/servers/{encoded}/versions/latest"
    return _http_get_json(url, timeout_s=timeout_s)


def _fetch_github_repo(owner: str, repo: str, timeout_s: int) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{owner}/{repo}"
    return _http_get_json(url, timeout_s=timeout_s)


def _build_server_report(
    *,
    registry_entry: dict[str, Any] | None,
    github_entry: dict[str, Any] | None,
    server_name: str,
) -> dict[str, Any]:
    checks: list[Check] = []
    risks: list[str] = []

    if registry_entry is None:
        checks.append(Check("registry_entry", False, "No latest version in Official MCP Registry", "high"))
        return {
            "server_name": server_name,
            "checks": [asdict(check) for check in checks],
            "risks": ["Missing official registry record"],
            "risk_level": "high",
            "decision": "reject_for_trial",
        }

    server_payload = registry_entry.get("server", {})
    meta_payload = registry_entry.get("_meta", {}).get("io.modelcontextprotocol.registry/official", {})

    status = str(meta_payload.get("status", "unknown"))
    checks.append(Check("official_status_active", status == "active", f"status={status}", "high"))

    repository_url = ((server_payload.get("repository") or {}).get("url") or "").strip()
    checks.append(Check("repository_url", bool(repository_url), repository_url or "missing", "high"))

    packages = server_payload.get("packages") or []
    package = packages[0] if packages else {}
    transport_type = ((package.get("transport") or {}).get("type") or "").strip()
    checks.append(Check("transport_stdio", transport_type == "stdio", f"transport={transport_type or 'unknown'}"))

    env_names = [item.get("name") for item in (package.get("environmentVariables") or []) if item.get("name")]
    expected_envs = EXPECTED_ENVS.get(server_name, set())
    if expected_envs:
        missing_env = sorted(expected_envs - set(env_names))
        checks.append(
            Check(
                "env_contract_match",
                len(missing_env) == 0,
                "missing=" + ",".join(missing_env) if missing_env else "ok",
                "high",
            )
        )

    if github_entry is None:
        checks.append(Check("github_metadata", False, "GitHub metadata unavailable", "medium"))
        risks.append("No GitHub metadata (stars/license/activity unknown)")
    else:
        archived = bool(github_entry.get("archived"))
        license_id = ((github_entry.get("license") or {}).get("spdx_id") or "").strip()
        pushed_at = _iso_to_datetime(github_entry.get("pushed_at"))
        age_days = None
        if pushed_at is not None:
            age_days = int((datetime.now(UTC) - pushed_at.astimezone(UTC)).total_seconds() // 86400)

        checks.append(Check("github_not_archived", not archived, f"archived={archived}", "high"))
        checks.append(Check("license_present", bool(license_id), f"license={license_id or 'missing'}", "high"))
        checks.append(
            Check(
                "recent_activity_180d",
                age_days is not None and age_days <= 180,
                f"pushed_age_days={age_days if age_days is not None else 'unknown'}",
                "medium",
            )
        )

        if archived:
            risks.append("Repository archived")
        if not license_id:
            risks.append("Missing explicit SPDX license")
        if age_days is None or age_days > 180:
            risks.append("No recent maintenance activity in last 180 days")

    for check in checks:
        if not check.ok and check.severity == "high":
            risks.append(f"Critical check failed: {check.name}")

    if any(not check.ok and check.severity == "high" for check in checks):
        decision = "reject_for_trial"
        risk_level = "high"
    elif any(not check.ok for check in checks):
        decision = "trial_only_with_mitigations"
        risk_level = "medium"
    else:
        decision = "eligible_for_trial"
        risk_level = "low"

    return {
        "server_name": server_name,
        "registry": {
            "name": server_payload.get("name"),
            "version": server_payload.get("version"),
            "description": server_payload.get("description"),
            "repository_url": repository_url or None,
            "package": {
                "registry_type": package.get("registryType"),
                "identifier": package.get("identifier"),
                "version": package.get("version"),
                "transport": transport_type or None,
                "environment_variables": env_names,
            },
            "official_status": status,
            "published_at": meta_payload.get("publishedAt"),
            "updated_at": meta_payload.get("updatedAt"),
        },
        "github": None
        if github_entry is None
        else {
            "full_name": github_entry.get("full_name"),
            "stargazers_count": github_entry.get("stargazers_count"),
            "forks_count": github_entry.get("forks_count"),
            "open_issues_count": github_entry.get("open_issues_count"),
            "pushed_at": github_entry.get("pushed_at"),
            "archived": github_entry.get("archived"),
            "license": (github_entry.get("license") or {}).get("spdx_id"),
        },
        "checks": [asdict(check) for check in checks],
        "risks": sorted(set(risks)),
        "risk_level": risk_level,
        "decision": decision,
    }


def _to_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# MCP Publish Audit Report")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{report['generated_at']}`")
    lines.append(f"- Registry base: `{report['registry_base']}`")
    lines.append(f"- Servers audited: `{len(report['servers'])}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Server | Decision | Risk Level |")
    lines.append("|---|---|---|")
    for item in report["servers"]:
        lines.append(f"| `{item['server_name']}` | `{item['decision']}` | `{item['risk_level']}` |")
    lines.append("")
    lines.append("## Details")
    for item in report["servers"]:
        lines.append("")
        lines.append(f"### {item['server_name']}")
        lines.append("")
        lines.append(f"- Decision: `{item['decision']}`")
        lines.append(f"- Risk level: `{item['risk_level']}`")
        registry = item.get("registry") or {}
        if registry:
            lines.append(f"- Registry version: `{registry.get('version')}`")
            lines.append(f"- Official status: `{registry.get('official_status')}`")
            lines.append(f"- Repository: `{registry.get('repository_url')}`")
            pkg = registry.get("package") or {}
            lines.append(
                f"- Package: `{pkg.get('identifier')}` (`{pkg.get('registry_type')}`, transport=`{pkg.get('transport')}`)"
            )
        github = item.get("github") or {}
        if github:
            lines.append(
                "- GitHub: "
                f"stars={github.get('stargazers_count')}, forks={github.get('forks_count')}, "
                f"issues={github.get('open_issues_count')}, pushed_at={github.get('pushed_at')}, "
                f"archived={github.get('archived')}, license={github.get('license')}"
            )
        lines.append("- Checks:")
        for check in item.get("checks", []):
            icon = "OK" if check.get("ok") else "FAIL"
            lines.append(
                f"  - {icon} `{check.get('name')}` ({check.get('severity')}): {check.get('detail')}"
            )
        lines.append("- Risks:")
        risks = item.get("risks") or []
        if not risks:
            lines.append("  - none")
        else:
            for risk in risks:
                lines.append(f"  - {risk}")
    lines.append("")
    lines.append("## Gate")
    lines.append("")
    lines.append(
        "Recommendation: only servers with `decision=eligible_for_trial` can enter sandbox trial; "
        "all others require mitigations or rejection."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit MCP servers for publish/analytics trial readiness.")
    parser.add_argument(
        "--registry-base",
        default=os.getenv("MCP_REGISTRY_BASE", DEFAULT_REGISTRY_BASE),
        help="MCP Registry base URL (default: %(default)s)",
    )
    parser.add_argument(
        "--servers",
        default=",".join(DEFAULT_SERVERS),
        help="Comma-separated list of MCP server names to audit",
    )
    parser.add_argument(
        "--out-dir",
        default="out/reports",
        help="Output directory for audit report artifacts",
    )
    parser.add_argument(
        "--timeout-s",
        type=int,
        default=20,
        help="HTTP timeout in seconds",
    )
    parser.add_argument(
        "--fail-on-risk-level",
        choices=["none", "high", "medium"],
        default="none",
        help="Exit with code 2 when any server reaches selected or higher risk level",
    )
    args = parser.parse_args()

    server_names = [item.strip() for item in args.servers.split(",") if item.strip()]
    if not server_names:
        raise SystemExit("No servers configured for audit.")

    report_items: list[dict[str, Any]] = []
    for server_name in server_names:
        registry_entry: dict[str, Any] | None = None
        github_entry: dict[str, Any] | None = None
        registry_error: str | None = None
        github_error: str | None = None

        try:
            registry_entry = _fetch_registry_server(args.registry_base, server_name, args.timeout_s)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            registry_error = f"{type(exc).__name__}: {exc}"

        repo_tuple = None
        if registry_entry:
            server_payload = registry_entry.get("server", {})
            repository_url = ((server_payload.get("repository") or {}).get("url") or "").strip()
            repo_tuple = _parse_github_repo(repository_url)

        if repo_tuple:
            try:
                github_entry = _fetch_github_repo(repo_tuple[0], repo_tuple[1], args.timeout_s)
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
                github_error = f"{type(exc).__name__}: {exc}"

        item = _build_server_report(
            registry_entry=registry_entry,
            github_entry=github_entry,
            server_name=server_name,
        )
        if registry_error:
            item.setdefault("risks", []).append(f"Registry lookup failed: {registry_error}")
        if github_error:
            item.setdefault("risks", []).append(f"GitHub lookup failed: {github_error}")
        report_items.append(item)

    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    report_payload = {
        "generated_at": generated_at,
        "registry_base": args.registry_base,
        "servers": report_items,
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = out_dir / f"mcp-publish-audit-{stamp}.json"
    md_path = out_dir / f"mcp-publish-audit-{stamp}.md"
    latest_json_path = out_dir / "mcp-publish-audit-latest.json"
    latest_md_path = out_dir / "mcp-publish-audit-latest.md"

    json_text = json.dumps(report_payload, ensure_ascii=True, indent=2)
    md_text = _to_markdown(report_payload)
    json_path.write_text(json_text + "\n", encoding="utf-8")
    md_path.write_text(md_text, encoding="utf-8")
    latest_json_path.write_text(json_text + "\n", encoding="utf-8")
    latest_md_path.write_text(md_text, encoding="utf-8")

    decisions = {item.get("decision") for item in report_items}
    print(f"[mcp-audit] JSON: {json_path}")
    print(f"[mcp-audit] Markdown: {md_path}")
    print(f"[mcp-audit] Latest JSON: {latest_json_path}")
    print(f"[mcp-audit] Latest Markdown: {latest_md_path}")
    print(f"[mcp-audit] Decisions: {sorted(decisions)}")
    if args.fail_on_risk_level != "none":
        order = {"low": 0, "medium": 1, "high": 2}
        threshold = order[args.fail_on_risk_level]
        max_risk = max(order.get(str(item.get("risk_level", "low")), 0) for item in report_items)
        if max_risk >= threshold:
            print(
                f"[mcp-audit] FAIL gate: max_risk_level={max((item.get('risk_level', 'low') for item in report_items), key=lambda x: order.get(x, 0))}, threshold={args.fail_on_risk_level}"
            )
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
