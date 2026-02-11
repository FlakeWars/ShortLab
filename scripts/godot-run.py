#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _project_dir() -> Path:
    return _repo_root() / "renderer" / "godot"


def _generated_dir(project_dir: Path) -> Path:
    return project_dir / "generated"


def _log_dir(repo_root: Path) -> Path:
    return repo_root / "out" / "godot" / "logs"


def _copy_script(source: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_name = f"llm_{uuid.uuid4().hex}.gd"
    dest_path = dest_dir / dest_name
    shutil.copyfile(source, dest_path)
    return dest_path


def _run_cmd(cmd: list[str], env: dict[str, str] | None = None) -> int:
    print("[godot-run]", " ".join(cmd))
    completed = subprocess.run(cmd, check=False, env=env)
    return completed.returncode


def _movie_ext_supported(path: Path) -> bool:
    return path.suffix.lower() in {".ogv", ".avi", ".png"}


def _transcode_movie(src: Path, dest: Path) -> int:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("[godot-run] ffmpeg not found (required to convert movie)")
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(src),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    return _run_cmd(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Godot runner for GDScript")
    parser.add_argument("--mode", choices=["validate", "preview", "render"], required=True)
    parser.add_argument("--script", required=True, help="Path to .gd script to run")
    parser.add_argument("--seconds", type=float, default=5.0)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--max-nodes", type=int, default=200)
    parser.add_argument("--out", default="out/godot/render.mp4")
    args = parser.parse_args()

    script_path = Path(args.script).resolve()
    if not script_path.exists():
        raise SystemExit(f"[godot-run] script not found: {script_path}")
    if script_path.suffix != ".gd":
        raise SystemExit("[godot-run] script must be .gd")

    repo_root = _repo_root()
    project_dir = _project_dir()
    generated_dir = _generated_dir(project_dir)
    local_script = _copy_script(script_path, generated_dir)
    log_dir = _log_dir(repo_root)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"godot-run-{uuid.uuid4().hex}.log"

    godot_bin = os.getenv("GODOT_BIN", "godot")
    res_script = f"res://generated/{local_script.name}"
    cmd = [
        godot_bin,
        "--log-file",
        str(log_file),
        "--path",
        str(project_dir),
        "--script",
        "res://runner.gd",
    ]
    env = os.environ.copy()
    env["GODOT_SCRIPT_PATH"] = res_script
    env["GODOT_SECONDS"] = str(args.seconds)
    env["GODOT_MAX_NODES"] = str(args.max_nodes)

    if args.mode == "validate":
        cmd.insert(1, "--headless")
        return _run_cmd(cmd, env)

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    movie_path = out_path
    needs_transcode = not _movie_ext_supported(out_path)
    if needs_transcode:
        movie_path = out_path.with_suffix(".ogv")
    cmd.extend(["--write-movie", str(movie_path), "--fixed-fps", str(args.fps)])
    exit_code = _run_cmd(cmd, env)
    if exit_code != 0:
        return exit_code
    if needs_transcode:
        return _transcode_movie(movie_path, out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
