#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _audit_ok(audit: dict[str, Any] | None, max_allowed_risk: str) -> tuple[bool, str]:
    if not audit:
        return False, "missing audit report"
    order = {"low": 0, "medium": 1, "high": 2}
    threshold = order.get(max_allowed_risk, 2)
    max_risk = "low"
    for server in audit.get("servers", []):
        risk = str(server.get("risk_level", "low"))
        if order.get(risk, 0) >= order.get(max_risk, 0):
            max_risk = risk
    ok = order.get(max_risk, 0) <= threshold
    return ok, f"max_risk={max_risk}, allowed={max_allowed_risk}"


def _compliance_ok(compliance: dict[str, Any] | None) -> tuple[bool, str]:
    if not compliance:
        return False, "missing compliance report"
    verdict = str(compliance.get("verdict", "unknown"))
    return verdict == "pass", f"verdict={verdict}"


def _oauth_ok(oauth: dict[str, Any] | None) -> tuple[bool, str]:
    if not oauth:
        return False, "missing oauth smoke report"
    results = oauth.get("results") or []
    statuses = {str(item.get("provider")): str(item.get("status")) for item in results if isinstance(item, dict)}
    # readiness logic: no failed providers, and at least one provider is passed or intentionally skipped by missing config
    has_failed = any(status == "failed" for status in statuses.values())
    has_provider = len(statuses) > 0
    ok = has_provider and not has_failed
    return ok, f"statuses={statuses}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate latest publish readiness reports into one summary.")
    parser.add_argument("--reports-dir", default="out/reports", help="Directory with latest report files")
    parser.add_argument(
        "--max-allowed-risk",
        choices=["low", "medium", "high"],
        default="medium",
        help="Maximum allowed MCP audit risk level",
    )
    parser.add_argument(
        "--require-pass",
        action="store_true",
        help="Return exit code 2 when overall readiness is false",
    )
    args = parser.parse_args()

    reports_dir = Path(args.reports_dir)
    audit = _read_json(reports_dir / "mcp-publish-audit-latest.json")
    compliance = _read_json(reports_dir / "mcp-compliance-check-latest.json")
    oauth = _read_json(reports_dir / "publish-oauth-smoke-latest.json")

    audit_pass, audit_reason = _audit_ok(audit, args.max_allowed_risk)
    compliance_pass, compliance_reason = _compliance_ok(compliance)
    oauth_pass, oauth_reason = _oauth_ok(oauth)

    overall_pass = audit_pass and compliance_pass and oauth_pass
    payload = {
        "generated_at": _utc_now_iso(),
        "reports_dir": str(reports_dir),
        "overall_pass": overall_pass,
        "components": {
            "mcp_publish_audit": {"pass": audit_pass, "reason": audit_reason},
            "mcp_compliance_check": {"pass": compliance_pass, "reason": compliance_reason},
            "publish_oauth_smoke": {"pass": oauth_pass, "reason": oauth_reason},
        },
    }

    summary_json = reports_dir / "publish-readiness-summary-latest.json"
    summary_md = reports_dir / "publish-readiness-summary-latest.md"
    summary_json.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    md_lines = [
        "# Publish Readiness Summary",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Overall pass: `{overall_pass}`",
        "",
        "| Component | Pass | Reason |",
        "|---|---|---|",
        f"| `mcp_publish_audit` | `{audit_pass}` | {audit_reason} |",
        f"| `mcp_compliance_check` | `{compliance_pass}` | {compliance_reason} |",
        f"| `publish_oauth_smoke` | `{oauth_pass}` | {oauth_reason} |",
        "",
    ]
    summary_md.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"[publish-readiness] JSON: {summary_json}")
    print(f"[publish-readiness] Markdown: {summary_md}")
    print(f"[publish-readiness] overall_pass={overall_pass}")

    if args.require_pass and not overall_pass:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
