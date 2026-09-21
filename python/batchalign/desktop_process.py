"""Owned desktop inference processes, with a lightweight lifetime supervisor.

The daemon never imports a job's models. A supervisor watches its stdin pipe:
even abrupt daemon exit closes that pipe and stops the inference process tree.
Model code runs in a separate interpreter from both control processes.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time


def _command(mode: str, directory: Path) -> list[str]:
    return [sys.executable, "-m", "batchalign.desktop_process", mode, str(directory)]


def _stop_worker(worker: subprocess.Popen) -> None:
    if os.name == "nt":
        if worker.poll() is not None:
            return
        subprocess.run(["taskkill", "/PID", str(worker.pid), "/T", "/F"],
                       capture_output=True, timeout=10, check=False,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        try:
            os.killpg(worker.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            worker.wait(timeout=3)
        except subprocess.TimeoutExpired:
            pass
        # A child may ignore SIGTERM even if the main worker already exited.
        # This group belongs exclusively to this job's model process tree.
        try:
            os.killpg(worker.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    worker.wait(timeout=10)


def _supervise(directory: Path) -> int:
    worker = subprocess.Popen(_command("--worker", directory), stdin=subprocess.DEVNULL,
                              start_new_session=os.name != "nt",
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    (directory / "worker.pid").write_text(str(worker.pid))
    owner_closed = threading.Event()

    def watch_owner():
        # No model imports or native inference can hold this interpreter's GIL.
        # A raw fd avoids leaving a BufferedReader lock held by this daemon
        # thread when a normally completed supervisor exits its interpreter.
        while os.read(sys.stdin.fileno(), 1):
            pass
        owner_closed.set()

    threading.Thread(target=watch_owner, daemon=True).start()
    while worker.poll() is None and not owner_closed.wait(0.1):
        pass
    # Cleanup runs on the supervisor's main thread. It must finish before
    # interpreter exit, including when SIGTERM stops the worker immediately.
    if owner_closed.is_set() or os.name != "nt":
        _stop_worker(worker)
    code = worker.wait()
    return code if code >= 0 else 128 - code


async def _worker(directory: Path) -> None:
    from batchalign import api
    from batchalign.desktop import DesktopRequest, _run

    config = json.loads((directory / "request.json").read_text(encoding="utf-8"))
    job = api.Job(id=config["id"], recipe=config["recipe"], workdir=directory / "staging")
    job.workdir.mkdir()
    job.state = api.JobState.RUNNING
    job.started_at = time.time()

    async def collect_events():
        with (directory / "events.jsonl").open("w", encoding="utf-8") as stream:
            while (event := await job.events.get()) is not None:
                stream.write(json.dumps(event) + "\n")
                stream.flush()

    collector = asyncio.create_task(collect_events())
    await asyncio.to_thread(_run, job, DesktopRequest.model_validate(config["request"]),
                            Path(config["root"]),
                            {sid: Path(path) for sid, path in config["sources"].items()},
                            asyncio.get_running_loop())
    await collector
    result = {"state": job.state.value, "error": job.error, "result": job.result}
    temporary = directory / "result.tmp"
    temporary.write_text(json.dumps(result), encoding="utf-8")
    temporary.replace(directory / "result.json")


async def run_job(job, request, root: Path, sources: dict[str, Path]) -> None:
    from batchalign import api
    from batchalign.desktop import TASKS

    directory = job.workdir
    process = None
    stream = None
    pending = ""

    async def drain_events():
        nonlocal stream, pending
        if stream is None:
            try:
                stream = (directory / "events.jsonl").open(encoding="utf-8")
            except FileNotFoundError:
                return
        pending += stream.read()
        while "\n" in pending:
            line, pending = pending.split("\n", 1)
            if job.state != api.JobState.CANCELLED:
                await job.events.put(json.loads(line))

    try:
        config = {"id": job.id, "recipe": job.recipe,
                  "request": request.model_dump(mode="json"), "root": str(root),
                  "sources": {sid: str(path) for sid, path in sources.items()}}
        (directory / "request.json").write_text(json.dumps(config), encoding="utf-8")
        # Preserve the interpreter's import roots for Bazel runfiles as well as
        # installed wheels. Do not download or create another environment.
        environment = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}
        process = await asyncio.create_subprocess_exec(
            *_command("--supervise", directory), stdin=asyncio.subprocess.PIPE,
            env=environment,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        while process.returncode is None and job.state != api.JobState.CANCELLED:
            await drain_events()
            await asyncio.sleep(0.1)
        if job.state != api.JobState.CANCELLED:
            await process.wait()
            await drain_events()
            if process.returncode != 0:
                raise RuntimeError(f"model worker exited with code {process.returncode}")
            result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
            job.state = api.JobState(result["state"])
            job.error = result["error"]
            job.result = result["result"]
    except asyncio.CancelledError:
        job.state = api.JobState.CANCELLED
        raise
    except Exception as error:
        if job.state != api.JobState.CANCELLED:
            job.state = api.JobState.FAILED
            job.error = f"{type(error).__name__}: {error}"
            for sid in sources:
                await job.events.put({"source_id": sid, "kind": "StageFailed",
                                      "task": TASKS[request.steps[-1].recipe],
                                      "completed": 0, "total": 0, "label": job.error})
    finally:
        if process is not None:
            process.stdin.close()
            try:
                await asyncio.wait_for(process.wait(), timeout=25)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
        if stream is not None:
            stream.close()
        job.finished_at = time.time()
        shutil.rmtree(directory, ignore_errors=True)
        await job.events.put(None)


if __name__ == "__main__":
    mode, path = sys.argv[1:]
    if mode == "--supervise":
        raise SystemExit(_supervise(Path(path)))
    if mode != "--worker":
        raise SystemExit("invalid desktop worker mode")
    asyncio.run(_worker(Path(path)))
