"""Local desktop jobs: ordered recipes and durable output artifacts.

The GUI sends relative source IDs for its file rows. Native pipelines receive
absolute original source paths so alignment/diarization can locate media even
when an intermediate transcript lives in the job's temporary directory.
"""
from __future__ import annotations

import asyncio
import inspect
import os
from pathlib import Path
import shutil
import tempfile
import time
from typing import Any, Literal
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from batchalign import inputs as ba_inputs

router = APIRouter()
Verb = Literal["transcribe", "diarize", "align", "morphotag", "translate", "compare"]
TASKS = {"transcribe": "Asr", "diarize": "Speaker", "align": "Fa",
         "morphotag": "Morphosyntax", "translate": "Translate", "compare": "Compare"}


class DesktopStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipe: Verb
    kwargs: dict[str, Any] = Field(default_factory=dict)
    gold_path: str | None = None
    use_cache: bool = True
    strip_word_timing: bool = False


class DesktopRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    folder: str
    source_ids: list[str] = Field(min_length=1)
    steps: list[DesktopStep] = Field(min_length=1)
    in_place: bool = False
    output_path: str | None = None
    workers: int = Field(default=4, ge=1, le=64)
    force_cpu: bool = False

    @model_validator(mode="after")
    def valid_pipeline(self):
        names = [step.recipe for step in self.steps]
        if len(set(names)) != len(names):
            raise ValueError("pipeline steps must be unique")
        if "transcribe" in names[1:]:
            raise ValueError("transcribe must be the first step")
        if not self.in_place and not self.output_path:
            raise ValueError("choose an output folder or enable in-place output")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("input files must be unique")
        return self


def _output_relative(req: DesktopRequest, sid: str) -> Path:
    relative = Path(sid)
    return relative.with_suffix(".cha") if req.steps[0].recipe == "transcribe" else relative


def _sources(req: DesktopRequest) -> tuple[Path, dict[str, Path]]:
    root = Path(req.folder).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("input folder is not a directory")
    sources: dict[str, Path] = {}
    resolved_sources: set[Path] = set()
    targets: set[Path] = set()
    out = root if req.in_place else Path(req.output_path or "").resolve()
    for sid in req.source_ids:
        relative = Path(sid)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"source must be relative to the input folder: {sid}")
        path = (root / relative).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f"input is not a file inside the selected folder: {sid}")
        if path in resolved_sources:
            raise ValueError(f"input was selected more than once: {sid}")
        resolved_sources.add(path)
        media = req.steps[0].recipe == "transcribe"
        allowed = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".mp4", ".mov", ".m4v"} if media else {".cha", ".chat"}
        if path.suffix.lower() not in allowed:
            raise ValueError(f"{req.steps[0].recipe} cannot process {sid}")
        target = (out / _output_relative(req, sid)).resolve()
        if not target.is_relative_to(out):
            raise ValueError(f"output escapes the selected folder: {sid}")
        if target in targets:
            raise ValueError(f"multiple inputs would overwrite {target}")
        targets.add(target)
        sources[sid] = path
    return root, sources


def _gold(step: DesktopStep, source: Path, relative: str) -> Path:
    if step.gold_path:
        supplied = Path(step.gold_path).resolve()
        if supplied.is_file():
            return supplied
        candidate = supplied / Path(relative).with_suffix(".cha")
        if candidate.is_file():
            return candidate
        directory = supplied / Path(relative).parent
    else:
        directory = source.parent
    for candidate in (directory / f"{source.stem}.gold.cha", directory / "template.gold.cha"):
        if candidate.is_file():
            return candidate
    raise ValueError(f"no gold reference for {relative}")


def _publish(staged: Path, target: Path, root: Path) -> None:
    """Replace a destination only after a complete output has been written."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"output escapes the selected folder: {target}")
    fd, temporary = tempfile.mkstemp(prefix=".batchalign-", dir=target.parent)
    os.close(fd)
    try:
        shutil.copyfile(staged, temporary)
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _run(job, req: DesktopRequest, root: Path, sources: dict[str, Path], loop) -> None:
    from batchalign import api

    current = dict(sources)
    errors: dict[str, str] = {}
    artifacts: list[dict[str, str]] = []
    metrics: dict[str, Path] = {}
    absolute_ids = {str(path): sid for sid, path in sources.items()}

    def emit(sid: str, kind: str, step: DesktopStep, label: str | None = None):
        payload = {"source_id": sid, "kind": kind, "task": TASKS[step.recipe],
                   "completed": int(kind == "StageInjected"),
                   "total": int(kind == "StageInjected"), "label": label}
        asyncio.run_coroutine_threadsafe(job.events.put(payload), loop)

    try:
        for index, step in enumerate(req.steps):
            if job.state == api.JobState.CANCELLED or not current:
                break
            kwargs = dict(step.kwargs)
            for key, value in list(kwargs.items()):
                if api._is_backend_spec_dict(value):
                    value = {**value, "kwargs": dict(value.get("kwargs") or {})}
                    cls = api.BACKEND_CLASSES.get(value["kind"])
                    if req.force_cpu and cls and "device" in inspect.signature(cls.__init__).parameters:
                        value["kwargs"]["device"] = "cpu"
                    kwargs[key] = api.build_backend(value)
            if step.recipe == "align" and "utr_backend" not in kwargs:
                from batchalign.desktop_timing import DesktopTimingRecovery
                kwargs["utr_backend"] = DesktopTimingRecovery(device="cpu" if req.force_cpu else None)
            opts: dict[str, Any] = {"workers": req.workers}
            if not step.use_cache:
                from batchalign._core import CacheSpec
                opts["cache"] = CacheSpec.bypass()
            pipeline = api.RECIPES[step.recipe](**kwargs, **opts)
            pending = {}
            inputs = []
            for sid, path in current.items():
                absolute = str(sources[sid])
                emit(sid, "StageStarted", step)
                try:
                    if step.recipe == "transcribe":
                        inp = ba_inputs.media_from_path(path, source_id=absolute)
                    elif step.recipe == "compare":
                        inp = ba_inputs.paired_from_paths(path, _gold(step, sources[sid], sid), source_id=absolute)
                    else:
                        inp = ba_inputs.chat_from_path(path, source_id=absolute)
                    inputs.append(inp)
                except Exception as exc:
                    errors[sid] = str(exc)
                    emit(sid, "StageFailed", step, str(exc))

            def progress(event):
                payload = api._event_to_dict(event)
                sid = absolute_ids.get(payload.get("source_id"))
                if sid is None or payload.get("kind") == "SourceCompleted":
                    return
                payload["source_id"] = sid
                if payload.get("kind") == "StageFailed":
                    errors[sid] = payload.get("label") or "pipeline stage failed"
                # Each recipe can include internal tasks; all belong to the
                # selected GUI step until its output has been staged.
                payload["task"] = TASKS[step.recipe]
                asyncio.run_coroutine_threadsafe(job.events.put(payload), loop)

            def outcome(value):
                sid = absolute_ids[str(value.source_id)]
                if job.state == api.JobState.CANCELLED:
                    return
                try:
                    if value.is_failed:
                        raise RuntimeError(value.error)
                    target = job.workdir / str(index) / Path(sid).with_suffix(".cha")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    value.write(str(target), strip_word_timing=step.strip_word_timing)
                    comparison = target.with_suffix(".compare.csv")
                    if comparison.is_file():
                        metrics[sid] = comparison
                    pending[sid] = target
                    emit(sid, "StageInjected", step)
                except Exception as exc:
                    errors[sid] = str(exc)
                    emit(sid, "StageFailed", step, str(exc))

            pipeline.run(inputs, callbacks=[(str(sources[sid]), progress) for sid in current],
                         outcome_callback=outcome, retain_outcomes=False)
            del pipeline
            for sid in current:
                if sid not in pending and sid not in errors and job.state != api.JobState.CANCELLED:
                    errors[sid] = "pipeline returned no outcome"
                    emit(sid, "StageFailed", step, errors[sid])
            current = pending
        if job.state != api.JobState.CANCELLED:
            output_root = root if req.in_place else Path(req.output_path or "").resolve()
            for sid, staged in current.items():
                target = output_root / _output_relative(req, sid)
                try:
                    if sid in metrics:
                        metric_target = target.with_suffix(".compare.csv")
                        _publish(metrics[sid], metric_target, output_root)
                        artifacts.append({"source_id": sid, "path": str(metric_target)})
                    _publish(staged, target, output_root)
                    artifacts.append({"source_id": sid, "path": str(target)})
                    emit(sid, "SourceCompleted", req.steps[-1])
                except Exception as exc:
                    errors[sid] = str(exc)
                    emit(sid, "StageFailed", req.steps[-1], str(exc))
            job.result = artifacts
            job.error = "\n".join(f"{sid}: {error}" for sid, error in errors.items()) or None
            job.state = api.JobState.FAILED if errors else api.JobState.COMPLETED
    except Exception as exc:
        job.error = f"{type(exc).__name__}: {exc}"
        if job.state != api.JobState.CANCELLED:
            job.state = api.JobState.FAILED
            for sid in current:
                emit(sid, "StageFailed", step, job.error)
    finally:
        job.finished_at = time.time()
        shutil.rmtree(job.workdir, ignore_errors=True)
        asyncio.run_coroutine_threadsafe(job.events.put(None), loop)


@router.post("/desktop/jobs")
async def start_desktop_job(req: DesktopRequest) -> dict[str, str]:
    from batchalign import api

    if not api._allow_paths():
        raise HTTPException(status_code=403, detail="desktop jobs require local filesystem access")
    try:
        root, sources = _sources(req)
        # Validate recipe arguments without loading models on the event loop.
        for step in req.steps:
            api.RECIPE_REQUEST_MODELS[step.recipe].model_validate({
                **step.kwargs, "inputs": [{"path": str(next(iter(sources.values())))}],
            })
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    job_id = uuid.uuid4().hex
    workdir = api._WORKDIR / "jobs" / job_id
    workdir.mkdir(parents=True)
    job = api.Job(id=job_id, recipe=" → ".join(s.recipe for s in req.steps), workdir=workdir)
    job.state = api.JobState.RUNNING
    job.started_at = time.time()
    api.JOBS[job_id] = job
    asyncio.create_task(asyncio.to_thread(_run, job, req, root, sources, asyncio.get_running_loop()))
    return {"job_id": job_id}
