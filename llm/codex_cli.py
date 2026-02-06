from __future__ import annotations

import json
import os
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class CodexCliError(RuntimeError):
    pass


def _build_prompt(system_prompt: str, user_prompt: str) -> str:
    return f"SYSTEM:\\n{system_prompt}\\n\\nUSER:\\n{user_prompt}\\n"


def _run_codex(
    *,
    codex_bin: str,
    sandbox: str,
    extra_args: str,
    model: str,
    timeout_s: int,
    prompt: str,
    output_path: Path,
    schema_path: Path | None,
) -> subprocess.CompletedProcess[bytes]:
    args = [codex_bin, "exec", "-"]
    if model:
        args += ["--model", model]
    if sandbox:
        args += ["--sandbox", sandbox]
    args += ["--color", "never", "--output-last-message", str(output_path)]
    if schema_path is not None:
        args += ["--output-schema", str(schema_path)]
    if extra_args:
        args += shlex.split(extra_args)

    return subprocess.run(
        args,
        input=prompt.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=max(5, timeout_s),
        check=False,
    )


def run_codex_cli(
    *,
    system_prompt: str,
    user_prompt: str,
    json_schema: dict[str, Any],
    model: str,
    timeout_s: int,
) -> str:
    codex_bin = os.getenv("CODEX_CLI_BIN", "codex").strip() or "codex"
    sandbox = os.getenv("CODEX_CLI_SANDBOX", "read-only").strip()
    use_schema = os.getenv("CODEX_CLI_USE_OUTPUT_SCHEMA", "1").strip() != "0"
    extra_args = os.getenv("CODEX_CLI_EXTRA_ARGS", "").strip()

    with tempfile.TemporaryDirectory(prefix="codex-cli-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        output_path = tmp_path / "last-message.txt"
        schema_path = tmp_path / "schema.json"

        if use_schema:
            schema_path.write_text(json.dumps(json_schema))

        prompt = _build_prompt(system_prompt, user_prompt)
        try:
            result = _run_codex(
                codex_bin=codex_bin,
                sandbox=sandbox,
                extra_args=extra_args,
                model=model,
                timeout_s=timeout_s,
                prompt=prompt,
                output_path=output_path,
                schema_path=schema_path if use_schema else None,
            )
        except subprocess.TimeoutExpired as exc:
            raise CodexCliError("timeout") from exc
        except FileNotFoundError as exc:
            raise CodexCliError("codex_cli_not_found") from exc

        if result.returncode != 0 and use_schema:
            err = (result.stderr or b"").decode("utf-8", errors="ignore")
            if "output-schema" in err or "unknown option" in err or "unrecognized option" in err:
                result = _run_codex(
                    codex_bin=codex_bin,
                    sandbox=sandbox,
                    extra_args=extra_args,
                    model=model,
                    timeout_s=timeout_s,
                    prompt=prompt,
                    output_path=output_path,
                    schema_path=None,
                )

        if result.returncode != 0:
            err = (result.stderr or b"").decode("utf-8", errors="ignore").strip()
            raise CodexCliError(err or f"codex_cli_exit_{result.returncode}")

        if output_path.exists():
            content = output_path.read_text().strip()
        else:
            content = (result.stdout or b"").decode("utf-8", errors="ignore").strip()

        if not content:
            raise CodexCliError("empty_response")
        return content
