#!/usr/bin/env python3
"""Black-box smoke test for the Rust Batchalign server.

Default mode starts a temporary local server in `--test-echo` mode, then
verifies basic HTTP lifecycle behavior.

Usage:
    python book/src/developer/smoke-test-server.py
    python book/src/developer/smoke-test-server.py --server http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest


_MINIMAL_CHAT = """\
@UTF8
@Begin
@Languages:\teng
@Participants:\tPAR0 Participant
@ID:\teng|test|PAR0|||||Participant|||
*PAR0:\thello .
@End
"""


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        return int(s.getsockname()[1])


def _http_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    timeout_s: float = 5.0,
) -> tuple[int, Any]:
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urlrequest.Request(url=url, method=method, data=body, headers=headers)
    try:
        with urlrequest.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read()
            parsed = json.loads(raw.decode("utf-8")) if raw else None
            return int(resp.status), parsed
    except urlerror.HTTPError as exc:
        raw = exc.read()
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else None
        except json.JSONDecodeError:
            parsed = raw.decode("utf-8", errors="replace")
        return int(exc.code), parsed


def _wait_for_health(base_url: str, timeout_s: float = 20.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    last_err: str | None = None
    while time.monotonic() < deadline:
        try:
            status, data = _http_json("GET", f"{base_url}/health", timeout_s=2.0)
            if status == 200 and isinstance(data, dict):
                return data
        except Exception as exc:  # pragma: no cover - defensive polling
            last_err = str(exc)
        time.sleep(0.2)

    raise TimeoutError(f"server did not become healthy at {base_url} ({last_err or 'timeout'})")


def _poll_job_terminal(base_url: str, job_id: str, timeout_s: float = 30.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        status, data = _http_json("GET", f"{base_url}/jobs/{job_id}", timeout_s=3.0)
        if status != 200 or not isinstance(data, dict):
            raise RuntimeError(f"job status request failed: status={status}, body={data!r}")
        if data.get("status") in {"completed", "failed", "cancelled"}:
            return data
        time.sleep(0.2)
    raise TimeoutError(f"job {job_id} did not finish within {timeout_s}s")


def _start_test_echo_server(repo_root: Path) -> tuple[subprocess.Popen[str], str]:
    port = _pick_free_port()
    base_url = f"http://127.0.0.1:{port}"

    home_dir = Path(tempfile.mkdtemp(prefix="ba-smoke-home-"))
    env = os.environ.copy()
    env["HOME"] = str(home_dir)
    env["PYTHONUNBUFFERED"] = "1"

    direct_cmd = [
        "batchalign",
        "serve",
        "start",
        "--foreground",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--test-echo",
    ]
    fallback_cmd = [
        "uv",
        "run",
        "--project",
        ".",
        "batchalign",
        "serve",
        "start",
        "--foreground",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--test-echo",
    ]

    try:
        proc = subprocess.Popen(
            direct_cmd,
            cwd=repo_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        proc = subprocess.Popen(
            fallback_cmd,
            cwd=repo_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    return proc, base_url


def _stop_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def _choose_chat_command(capabilities: list[str]) -> str | None:
    candidates = ["morphotag", "translate", "utseg", "coref"]
    if not capabilities or "test-echo" in capabilities:
        return "morphotag"
    for cmd in candidates:
        if cmd in capabilities:
            return cmd
    return None


def run_smoke(base_url: str) -> tuple[int, int]:
    passed = 0
    failed = 0

    # Health
    status, health = _http_json("GET", f"{base_url}/health")
    if status == 200 and isinstance(health, dict) and health.get("status") == "ok":
        print("  [ok] /health")
        passed += 1
    else:
        print(f"  [fail] /health -> status={status}, body={health!r}")
        failed += 1
        return passed, failed

    capabilities = health.get("capabilities", [])
    if not isinstance(capabilities, list):
        capabilities = []

    # Unknown command should be rejected.
    status, body = _http_json(
        "POST",
        f"{base_url}/jobs",
        payload={
            "command": "not_a_real_command",
            "files": [{"filename": "x.cha", "content": _MINIMAL_CHAT}],
        },
    )
    if status == 400:
        print("  [ok] unknown command rejected")
        passed += 1
    else:
        print(f"  [fail] unknown command rejection -> status={status}, body={body!r}")
        failed += 1

    # Submit one real chat command if supported.
    cmd = _choose_chat_command([str(c) for c in capabilities])
    if cmd is None:
        print(f"  [skip] no chat command capability available: {capabilities!r}")
    else:
        status, submit = _http_json(
            "POST",
            f"{base_url}/jobs",
            payload={
                "command": cmd,
                "lang": "eng",
                "num_speakers": 1,
                "files": [{"filename": "sample.cha", "content": _MINIMAL_CHAT}],
            },
            timeout_s=10.0,
        )
        if status != 200 or not isinstance(submit, dict):
            print(f"  [fail] submit {cmd} -> status={status}, body={submit!r}")
            failed += 1
        else:
            job_id = str(submit["job_id"])
            job = _poll_job_terminal(base_url, job_id)
            if job.get("status") != "completed":
                print(f"  [fail] job {job_id} ended as {job.get('status')!r}")
                failed += 1
            else:
                status, results = _http_json("GET", f"{base_url}/jobs/{job_id}/results")
                files = results.get("files") if isinstance(results, dict) else None
                if status == 200 and isinstance(files, list) and files:
                    out = files[0].get("content", "")
                    if isinstance(out, str) and "*PAR0:\thello ." in out:
                        print(f"  [ok] {cmd} job lifecycle")
                        passed += 1
                    else:
                        print(f"  [fail] result payload missing expected CHAT content: {out!r}")
                        failed += 1
                else:
                    print(f"  [fail] results fetch -> status={status}, body={results!r}")
                    failed += 1

    # List jobs
    status, jobs = _http_json("GET", f"{base_url}/jobs")
    if status == 200 and isinstance(jobs, list):
        print(f"  [ok] /jobs list ({len(jobs)} jobs)")
        passed += 1
    else:
        print(f"  [fail] /jobs list -> status={status}, body={jobs!r}")
        failed += 1

    return passed, failed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--server",
        default="",
        help="Use an already-running server URL instead of starting a local test-echo server.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    proc: subprocess.Popen[str] | None = None

    if args.server:
        base_url = args.server.rstrip("/")
        print(f"Using external server: {base_url}")
    else:
        print("Starting local Rust server in --test-echo mode...")
        proc, base_url = _start_test_echo_server(repo_root)

    try:
        _wait_for_health(base_url)
        print(f"Server healthy at {base_url}")
        passed, failed = run_smoke(base_url)
    finally:
        if proc is not None:
            _stop_process(proc)

    total = passed + failed
    print(f"\nResults: {passed} passed, {failed} failed, {total} total")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
