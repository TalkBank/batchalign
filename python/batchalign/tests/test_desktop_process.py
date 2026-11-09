"""Real process ownership and daemon responsiveness without downloading models."""
import os
import signal
import subprocess
import sys
import time
from unittest.mock import Mock

from fastapi.testclient import TestClient
import psutil
import pytest

from batchalign import api, desktop_process


def wait_for(predicate, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.05)
    raise AssertionError("condition did not become true before deadline")


def supervisor_command(directory, worker):
    # Only substitute model execution; lifetime supervision is production code.
    script = ("from pathlib import Path; import sys; "
              "from batchalign import desktop_process as p; "
              f"p._command=lambda mode,directory: [sys.executable,{str(worker)!r},str(directory)]; "
              "raise SystemExit(p._supervise(Path(sys.argv[1])))")
    return [sys.executable, "-c", script, str(directory)]


@pytest.fixture
def native_blocker(tmp_path):
    worker = tmp_path / "blocking_worker.py"
    worker.write_text("import ctypes, os, subprocess, sys\nfrom pathlib import Path\n"
                      "child = subprocess.Popen([sys.executable, '-c', "
                      "'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)'])\n"
                      "Path(sys.argv[1], 'grandchild.pid').write_text(str(child.pid))\n"
                      "Path(sys.argv[1], 'ready').touch()\n"
                      "if os.name == 'nt': ctypes.PyDLL('kernel32').Sleep(60000)\n"
                      "else: ctypes.PyDLL(None).sleep(60)\n")
    return worker


def process_stopped(pid):
    try:
        return psutil.Process(pid).status() == psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return True


@pytest.mark.parametrize("sig", [signal.SIGTERM, 9])
@pytest.mark.parametrize("snapshot", ["", "912 Z\n913 S\n", "912 Z+\n912 Z\n"])
def test_macos_cleanup_accepts_only_exited_process_groups(monkeypatch, sig, snapshot):
    monkeypatch.setattr(desktop_process.sys, "platform", "darwin")
    monkeypatch.setattr(desktop_process.os, "killpg", Mock(side_effect=PermissionError(1, "denied")),
                        raising=False)
    inspect = Mock(return_value=subprocess.CompletedProcess([], 0, stdout=snapshot))
    monkeypatch.setattr(desktop_process.subprocess, "run", inspect)
    assert desktop_process._signal_worker_group(912, sig) is False
    inspect.assert_called_once_with(["/bin/ps", "-axo", "pgid=,stat="],
                                    capture_output=True, text=True, check=True, timeout=5)


@pytest.mark.parametrize("platform,snapshot", [
    ("darwin", "912 Z\n912 S\n"), ("darwin", "912 R+\n"), ("linux", "912 Z\n"),
])
def test_group_cleanup_preserves_genuine_permission_errors(monkeypatch, platform, snapshot):
    monkeypatch.setattr(desktop_process.sys, "platform", platform)
    denied = PermissionError(1, "denied")
    monkeypatch.setattr(desktop_process.os, "killpg", Mock(side_effect=denied), raising=False)
    monkeypatch.setattr(desktop_process.subprocess, "run",
                        Mock(return_value=subprocess.CompletedProcess([], 0, stdout=snapshot)))
    with pytest.raises(PermissionError) as error:
        desktop_process._signal_worker_group(912, signal.SIGTERM)
    assert error.value is denied


def test_macos_group_cleanup_requires_a_successful_process_snapshot(monkeypatch):
    monkeypatch.setattr(desktop_process.sys, "platform", "darwin")
    monkeypatch.setattr(desktop_process.os, "killpg", Mock(side_effect=PermissionError(1, "denied")),
                        raising=False)
    monkeypatch.setattr(desktop_process.subprocess, "run",
                        Mock(side_effect=subprocess.CalledProcessError(1, "/bin/ps")))
    with pytest.raises(subprocess.CalledProcessError):
        desktop_process._signal_worker_group(912, signal.SIGTERM)


@pytest.mark.skipif(os.name == "nt", reason="Unix zombie process groups")
def test_signal_zombie_only_group():
    # Leave the session leader unreaped to exercise Darwin's real EPERM path.
    worker = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
    try:
        wait_for(lambda: psutil.Process(worker.pid).status() == psutil.STATUS_ZOMBIE)
        desktop_process._signal_worker_group(worker.pid, signal.SIGTERM)
        desktop_process._signal_worker_group(worker.pid, signal.SIGKILL)
        assert worker.wait(timeout=10) == 0
    finally:
        worker.wait(timeout=10)


@pytest.mark.skipif(os.name == "nt", reason="Unix process-group shutdown")
def test_successful_worker_exit_still_cleans_live_descendants(tmp_path):
    worker = tmp_path / "finished_worker.py"
    worker.write_text(
        "import subprocess, sys, time\nfrom pathlib import Path\n"
        "directory = Path(sys.argv[1])\n"
        "child = subprocess.Popen([sys.executable, '-c', "
        "'import signal,sys,time; from pathlib import Path; '"
        "'signal.signal(signal.SIGTERM, signal.SIG_IGN); '"
        "'Path(sys.argv[1]).touch(); time.sleep(60)', str(directory / 'ready')])\n"
        "(directory / 'grandchild.pid').write_text(str(child.pid))\n"
        "while not (directory / 'ready').exists(): time.sleep(0.01)\n")
    supervisor = subprocess.Popen(supervisor_command(tmp_path, worker), stdin=subprocess.PIPE,
                                  env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)})
    try:
        wait_for(lambda: (tmp_path / "grandchild.pid").exists())
        descendant = int((tmp_path / "grandchild.pid").read_text())
        assert supervisor.wait(timeout=15) == 0
        wait_for(lambda: process_stopped(descendant))
    finally:
        supervisor.stdin.close()
        supervisor.wait(timeout=15)
        pid_file = tmp_path / "grandchild.pid"
        if pid_file.exists() and not process_stopped(int(pid_file.read_text())):
            psutil.Process(int(pid_file.read_text())).kill()


@pytest.mark.skipif(os.name != "nt", reason="Windows process exit status")
@pytest.mark.parametrize("code", [23, 0xC0000005])
def test_supervisor_preserves_windows_worker_exit_status(tmp_path, code):
    worker = tmp_path / "exit_worker.py"
    worker.write_text("import ctypes\n"
                      "ctypes.windll.kernel32.ExitProcess.argtypes = [ctypes.c_uint32]\n"
                      f"ctypes.windll.kernel32.ExitProcess({code})\n")
    process = subprocess.Popen(supervisor_command(tmp_path, worker),
                               stdin=subprocess.PIPE,
                               env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)})
    try:
        assert process.wait(timeout=15) == code
    finally:
        process.stdin.close()
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)


def test_owner_pipe_closure_stops_native_worker_tree(tmp_path, native_blocker):
    directory = tmp_path / "work"
    directory.mkdir()
    supervisor = subprocess.Popen(supervisor_command(directory, native_blocker),
                                  stdin=subprocess.PIPE,
                                  env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)})
    pid = None
    try:
        wait_for(lambda: (directory / "worker.pid").exists())
        pid = int((directory / "worker.pid").read_text())
        wait_for(lambda: (directory / "ready").exists())
        descendant = int((directory / "grandchild.pid").read_text())
        time.sleep(0.1)
        assert psutil.pid_exists(pid)
        # The same EOF occurs if the daemon is killed without running cleanup.
        supervisor.stdin.close()
        supervisor.wait(timeout=15)
        wait_for(lambda: not psutil.pid_exists(pid))
        wait_for(lambda: process_stopped(descendant))
    finally:
        if supervisor.stdin and not supervisor.stdin.closed:
            supervisor.stdin.close()
        supervisor.wait(timeout=15)
        if pid and psutil.pid_exists(pid):
            psutil.Process(pid).kill()


@pytest.mark.skipif(os.name == "nt", reason="Unix process-group shutdown")
def test_daemon_group_sigterm_preserves_supervisor_cleanup(tmp_path, native_blocker):
    directory = tmp_path / "work"
    directory.mkdir()
    launcher = tmp_path / "daemon.py"
    launcher.write_text(
        "import asyncio\nfrom pathlib import Path\n"
        "from batchalign import api, desktop_process as p\n"
        "from batchalign.desktop import DesktopRequest\n"
        f"directory = Path({str(directory)!r})\n"
        f"p._command = lambda mode, directory: {supervisor_command(directory, native_blocker)!r}\n"
        "job = api.Job(id='group-test', recipe='compare', workdir=directory)\n"
        "job.state = api.JobState.RUNNING\n"
        "request = DesktopRequest(folder=str(directory), source_ids=['sample.cha'], "
        "output_path=str(directory / 'output'), steps=[{'recipe': 'compare'}])\n"
        "asyncio.run(p.run_job(job, request, directory, {}))\n")
    daemon = subprocess.Popen([sys.executable, str(launcher)], start_new_session=True,
                              env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)})
    owned = []
    worker_pid = None
    try:
        wait_for(lambda: (directory / "ready").exists())
        worker_pid = int((directory / "worker.pid").read_text())
        descendant = int((directory / "grandchild.pid").read_text())
        owned = [child.pid for child in psutil.Process(daemon.pid).children(recursive=True)]
        time.sleep(0.1)
        # Matches the packaged harness and process-group based app shutdown.
        os.killpg(daemon.pid, signal.SIGTERM)
        daemon.wait(timeout=10)
        wait_for(lambda: process_stopped(worker_pid), timeout=10)
        wait_for(lambda: process_stopped(descendant), timeout=10)
        for pid in owned:
            wait_for(lambda: process_stopped(pid), timeout=10)
    finally:
        if daemon.poll() is None:
            os.killpg(daemon.pid, signal.SIGKILL)
            daemon.wait(timeout=10)
        if worker_pid:
            try:
                os.killpg(worker_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        for pid in owned:
            if not process_stopped(pid):
                psutil.Process(pid).kill()


@pytest.mark.parametrize("crash", [False, True])
def test_native_worker_cannot_freeze_daemon_and_failure_allows_recovery(
        tmp_path, monkeypatch, native_blocker, crash):
    monkeypatch.setenv("BATCHALIGN_API_ALLOW_PATHS", "1")
    folder = tmp_path / "input"
    folder.mkdir()
    text = ("@UTF8\n@Begin\n@Languages:\teng\n@Participants:\tPAR Participant\n"
            "@ID:\teng|test|PAR|||||Participant|||\n*PAR:\thello world .\n@End\n")
    (folder / "sample.cha").write_text(text)
    (folder / "sample.gold.cha").write_text(text)
    output = tmp_path / "output"
    request = {"folder": str(folder), "source_ids": ["sample.cha"],
               "output_path": str(output), "steps": [{"recipe": "compare", "use_cache": False}]}
    worker = native_blocker
    if crash:
        worker = tmp_path / "crash.py"
        worker.write_text("raise SystemExit(23)\n")
    with TestClient(api.app) as client:
        with monkeypatch.context() as patch:
            patch.setattr(desktop_process, "_command",
                          lambda mode, directory: supervisor_command(directory, worker))
            response = client.post("/desktop/jobs", json=request)
            assert response.status_code == 200, response.text
            job_id = response.json()["job_id"]
            job = api.JOBS[job_id]
            if not crash:
                wait_for(lambda: (job.workdir / "worker.pid").exists())
                pid = int((job.workdir / "worker.pid").read_text())
                wait_for(lambda: (job.workdir / "ready").exists())
                descendant = int((job.workdir / "grandchild.pid").read_text())
                time.sleep(0.1)
                started = time.monotonic()
                assert client.get(f"/jobs/{job_id}").json()["state"] == "running"
                assert client.get("/capabilities").status_code == 200
                assert time.monotonic() - started < 2
                assert client.delete(f"/jobs/{job_id}").status_code == 200
            events = client.get(f"/jobs/{job_id}/events").text
            assert "event: done" in events
            state = client.get(f"/jobs/{job_id}").json()
            assert state["state"] == ("failed" if crash else "cancelled"), state
            if crash:
                assert "23" in state["error"]
                assert "StageFailed" in events
            else:
                assert not psutil.pid_exists(pid)
                wait_for(lambda: process_stopped(descendant))
            assert not job.workdir.exists()
            assert not (output / "sample.cha").exists()
            assert (folder / "sample.cha").read_text() == text
        # A real native comparison in a fresh process must still work.
        response = client.post("/desktop/jobs", json=request)
        next_id = response.json()["job_id"]
        assert "event: done" in client.get(f"/jobs/{next_id}/events").text
        state = client.get(f"/jobs/{next_id}").json()
        assert state["state"] == "completed", state
        assert "%xcmp:" in (output / "sample.cha").read_text()
