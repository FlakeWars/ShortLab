#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

VALID_ITEM_STATUS = {"passed", "failed", "waived", "pending"}
VALID_SERVER_DECISION = {"approved", "rejected", "pending"}


@dataclass(slots=True)
class Finding:
    severity: str
    message: str


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _ensure_checklist_exists(template_path: Path, checklist_path: Path) -> None:
    if checklist_path.exists():
        return
    checklist_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template_path, checklist_path)


def _validate(payload: dict[str, Any]) -> tuple[list[Finding], dict[str, Any]]:
    findings: list[Finding] = []
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    servers = payload.get("servers") if isinstance(payload.get("servers"), list) else []
    summary = {
        "servers_total": len(servers),
        "servers_approved": 0,
        "servers_rejected": 0,
        "servers_pending": 0,
        "items_total": 0,
        "items_passed": 0,
        "items_failed": 0,
        "items_waived": 0,
        "items_pending": 0,
    }

    reviewed_by = str(meta.get("reviewed_by", "")).strip()
    reviewed_at = str(meta.get("reviewed_at", "")).strip()
    if not reviewed_by:
        findings.append(Finding("medium", "meta.reviewed_by is empty"))
    if not reviewed_at:
        findings.append(Finding("medium", "meta.reviewed_at is empty"))

    for idx, server in enumerate(servers):
        if not isinstance(server, dict):
            findings.append(Finding("high", f"servers[{idx}] is not an object"))
            continue
        name = str(server.get("name", "")).strip()
        decision = str(server.get("decision", "")).strip()
        items = server.get("items")
        if not name:
            findings.append(Finding("high", f"servers[{idx}].name is empty"))
        if decision not in VALID_SERVER_DECISION:
            findings.append(
                Finding("high", f"servers[{idx}].decision has invalid value '{decision}'")
            )
            summary["servers_pending"] += 1
        elif decision == "approved":
            summary["servers_approved"] += 1
        elif decision == "rejected":
            summary["servers_rejected"] += 1
        else:
            summary["servers_pending"] += 1

        if not isinstance(items, list) or not items:
            findings.append(Finding("high", f"servers[{idx}].items missing or empty"))
            continue
        for jdx, item in enumerate(items):
            summary["items_total"] += 1
            if not isinstance(item, dict):
                findings.append(Finding("high", f"servers[{idx}].items[{jdx}] is not an object"))
                summary["items_pending"] += 1
                continue
            item_id = str(item.get("id", "")).strip()
            status = str(item.get("status", "")).strip()
            evidence = str(item.get("evidence", "")).strip()
            if not item_id:
                findings.append(Finding("high", f"servers[{idx}].items[{jdx}].id is empty"))
            if status not in VALID_ITEM_STATUS:
                findings.append(
                    Finding(
                        "high",
                        f"servers[{idx}].items[{jdx}] has invalid status '{status}'",
                    )
                )
                summary["items_pending"] += 1
                continue
            if status == "passed":
                summary["items_passed"] += 1
            elif status == "failed":
                summary["items_failed"] += 1
            elif status == "waived":
                summary["items_waived"] += 1
            else:
                summary["items_pending"] += 1

            if status in {"passed", "waived"} and not evidence:
                findings.append(
                    Finding(
                        "medium",
                        f"servers[{idx}].items[{jdx}] status '{status}' requires evidence",
                    )
                )
            if status == "failed":
                findings.append(
                    Finding(
                        "high",
                        f"servers[{idx}].items[{jdx}] marked failed ({item_id})",
                    )
                )

    if summary["servers_pending"] > 0:
        findings.append(Finding("medium", "At least one server decision is pending"))
    if summary["items_pending"] > 0:
        findings.append(Finding("medium", "At least one compliance item is pending"))

    return findings, summary


def _render_md(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# MCP Compliance Check Report")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{report['generated_at']}`")
    lines.append(f"- Checklist path: `{report['checklist_path']}`")
    lines.append(f"- Verdict: `{report['verdict']}`")
    lines.append("")
    summary = report["summary"]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Servers: total={summary['servers_total']}, approved={summary['servers_approved']}, rejected={summary['servers_rejected']}, pending={summary['servers_pending']}")
    lines.append(
        f"- Items: total={summary['items_total']}, passed={summary['items_passed']}, failed={summary['items_failed']}, waived={summary['items_waived']}, pending={summary['items_pending']}"
    )
    lines.append("")
    lines.append("## Findings")
    lines.append("")
    if not report["findings"]:
        lines.append("- none")
    else:
        for finding in report["findings"]:
            lines.append(f"- [{finding['severity']}] {finding['message']}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate MCP compliance checklist and produce report.")
    parser.add_argument(
        "--checklist",
        default="docs/mcp-compliance-checklist.json",
        help="Checklist JSON path (created from template if missing)",
    )
    parser.add_argument(
        "--template",
        default="docs/mcp-compliance-checklist.template.json",
        help="Checklist template path",
    )
    parser.add_argument("--out-dir", default="out/reports", help="Report output directory")
    parser.add_argument(
        "--require",
        choices=["none", "strict"],
        default="strict",
        help="strict returns exit code 2 when verdict != pass",
    )
    args = parser.parse_args()

    checklist_path = Path(args.checklist)
    template_path = Path(args.template)
    if not template_path.exists():
        raise SystemExit(f"Template not found: {template_path}")

    _ensure_checklist_exists(template_path, checklist_path)
    payload = _load_json(checklist_path)
    findings, summary = _validate(payload)

    has_high = any(f.severity == "high" for f in findings)
    has_medium = any(f.severity == "medium" for f in findings)
    if has_high:
        verdict = "fail_high"
    elif has_medium:
        verdict = "fail_medium"
    else:
        verdict = "pass"

    report = {
        "generated_at": _utc_now_iso(),
        "checklist_path": str(checklist_path),
        "verdict": verdict,
        "summary": summary,
        "findings": [asdict(f) for f in findings],
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = out_dir / f"mcp-compliance-check-{stamp}.json"
    md_path = out_dir / f"mcp-compliance-check-{stamp}.md"
    latest_json_path = out_dir / "mcp-compliance-check-latest.json"
    latest_md_path = out_dir / "mcp-compliance-check-latest.md"

    _write_json(json_path, report)
    _write_json(latest_json_path, report)
    md_text = _render_md(report)
    md_path.write_text(md_text, encoding="utf-8")
    latest_md_path.write_text(md_text, encoding="utf-8")

    print(f"[mcp-compliance] Checklist: {checklist_path}")
    print(f"[mcp-compliance] JSON: {json_path}")
    print(f"[mcp-compliance] Markdown: {md_path}")
    print(f"[mcp-compliance] Verdict: {verdict}")

    if args.require == "strict" and verdict != "pass":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
