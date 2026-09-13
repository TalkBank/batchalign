"""Shared helpers for the batchalign Typer CLI.

Centralizes:
* Recursive input collection — walk a folder for CHAT or media files and
  build `BAValue` inputs whose `source_id` is the absolute source path,
  so the writer can map each outcome back to its origin.
* Output writing — replace the source file in place when no output dir
  is given, or mirror the source's relative path under an output dir.
  Transcribe rewrites the suffix to `.cha`; other commands preserve it.
* Config-key resolution with a clear error message naming the INI key
  and env var when a credential is missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from os.path import abspath, commonpath
from pathlib import Path
from typing import Any, Iterable

import typer

from batchalign import config as _ba_config

CHAT_EXTENSIONS = (".cha", ".chat")
MEDIA_EXTENSIONS = (".wav", ".mp3", ".m4a", ".flac", ".ogg", ".mp4", ".mov", ".m4v")


@dataclass(frozen=True)
class InputSelection:
    """Discovered files and the root used to mirror outputs."""

    paths: tuple[Path, ...]
    root: Path


def resolve_inputs(
    paths: list[Path] | None,
    input_list: Path | None,
    suffixes: Iterable[str],
) -> InputSelection:
    """Expand positional paths and a UTF-8 list into one deduplicated selection."""
    entries = list(paths or [])
    if input_list is not None:
        try:
            lines = input_list.read_text(encoding="utf-8-sig").splitlines()
        except (OSError, UnicodeError) as exc:
            raise typer.BadParameter(f"cannot read input list {input_list}: {exc}") from exc
        for number, line in enumerate(lines, 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            entry = Path(line.strip()).expanduser()
            if not entry.is_absolute():
                entry = input_list.absolute().parent / entry
            if not entry.exists():
                raise typer.BadParameter(
                    f"{input_list}:{number}: input path does not exist: {entry}"
                )
            entries.append(entry)
    if not entries:
        raise typer.BadParameter("provide input paths or -i/--input-list FILE")

    suffixes = tuple(suffixes)
    roots = []
    files: dict[Path, Path] = {}
    for entry in entries:
        entry = Path(abspath(entry.expanduser()))
        if not entry.is_file() and not entry.is_dir():
            raise typer.BadParameter(f"input is not a file or directory: {entry}")
        roots.append(_root_for(entry))
        for path in _walk(entry, suffixes):
            files.setdefault(path.resolve(), path)
    return InputSelection(tuple(files.values()), Path(commonpath(roots)))


def selected_inputs(source: Path | InputSelection, suffixes: Iterable[str]) -> InputSelection:
    """Keep single-path callers compatible with explicit CLI selections."""
    if isinstance(source, InputSelection):
        return source
    return InputSelection(tuple(_walk(source, suffixes)), _root_for(source))


def _walk(folder: Path, suffixes: Iterable[str]) -> list[Path]:
    sset = {s.lower() for s in suffixes}
    if folder.is_file():
        return [] if folder.name.startswith(".") else [folder.absolute()]
    out: list[Path] = []
    for p in sorted(folder.rglob("*")):
        if not p.is_file() or p.name.startswith("."):
            continue
        if p.suffix.lower() in sset:
            out.append(p.absolute())
    out.sort(key=lambda path: (-path.stat().st_size, str(path)))
    return out


def _root_for(folder: Path) -> Path:
    return folder.absolute() if folder.is_dir() else folder.parent.absolute()


def collect_chat_inputs(
    source: Path | InputSelection, *, group_by_language: bool = False
) -> tuple[list[Any], Path]:
    """Discover inputs for CHAT files; return (inputs, root).

    Each input carries its absolute path as `source_id` so outcomes can
    be written back next to their source. Morphosyntax callers may group
    files by their `@Languages` value so the bounded Stanza pipeline cache
    does not repeatedly evict and reload models in a mixed-language corpus.
    """
    from batchalign.inputs import chat_from_path

    selection = selected_inputs(source, CHAT_EXTENSIONS)
    paths = list(selection.paths)
    if group_by_language:
        paths.sort(key=_chat_language_sort_key)
    inputs = [chat_from_path(p, source_id=str(p)) for p in paths]
    return inputs, selection.root


def _chat_language_sort_key(path: Path) -> tuple[str, int, str]:
    """Group CHAT paths by their raw language-set header, largest first."""
    language_set = ""
    try:
        with path.open("r", encoding="utf-8") as source:
            for line in source:
                if line.startswith("@Languages:"):
                    language_set = " ".join(
                        sorted(
                            part.strip().casefold()
                            for part in line[11:].split(",")
                            if part.strip()
                        )
                    )
                    break
                if line.startswith("*"):
                    break
    except (OSError, UnicodeError):
        # Parsing will report the actual source error later. Keep discovery
        # total and place unreadable/headerless files in one stable group.
        pass
    return language_set, -path.stat().st_size, str(path)


def collect_ai_inputs(source: Path | InputSelection, *, instruction: str) -> tuple[list[Any], Path]:
    """Discover inputs for CHAT files and attach one AI instruction to each."""
    from batchalign.inputs import ai_from_path

    selection = selected_inputs(source, CHAT_EXTENSIONS)
    inputs = [
        ai_from_path(p, source_id=str(p), instruction=instruction)
        for p in selection.paths
    ]
    return inputs, selection.root


def collect_media_inputs(source: Path | InputSelection, *, language: str | None = None) -> tuple[list[Any], Path]:
    """Discover inputs for media files; return (inputs, root)."""
    from batchalign.inputs import media_from_path

    selection = selected_inputs(source, MEDIA_EXTENSIONS)
    inputs = [
        media_from_path(p, source_id=str(p), language=language)
        for p in selection.paths
    ]
    return inputs, selection.root


def safe_resolve(path: Path | str, root: Path | str) -> Path:
    """Resolve `path` and verify it stays within `root`.

    Prevents path-traversal attacks where a symlink, `..` segment, or
    absolute-path override would lead a writer outside the directory the
    user intended (e.g. paths-mode where a daemon resolves user-supplied
    relative paths against a `media_paths_root`).

    Raises `typer.BadParameter` on any escape attempt. Returns the
    resolved absolute path on success.
    """
    p = Path(path).expanduser().resolve()
    r = Path(root).expanduser().resolve()
    try:
        p.relative_to(r)
    except ValueError as exc:
        raise typer.BadParameter(
            f"path {p} escapes root {r}; refusing to operate outside the "
            "configured root",
        ) from exc
    return p


def write_outcomes(
    outcomes: list[Any],
    root: Path,
    out_dir: Path | None,
    *,
    output_suffix: str | None = None,
    strip_word_timing: bool = False,
) -> None:
    """Write each outcome to disk.

    `out_dir is None` writes next to the source (in-place); `output_suffix`
    rewrites the source's suffix (transcribe: `.wav` → `.cha`). When
    `out_dir` is given, the source's relative path under `root` is mirrored
    under `out_dir`, with the same suffix rule applied.

    When `out_dir` is given, the resolved target is verified to stay under
    `out_dir` via `safe_resolve` — guards against symlinked source paths
    that would otherwise land outputs outside the user's chosen output
    directory.
    """
    for outcome in outcomes:
        write_outcome(
            outcome,
            root,
            out_dir,
            output_suffix=output_suffix,
            strip_word_timing=strip_word_timing,
        )


def write_outcome(
    outcome: Any,
    root: Path,
    out_dir: Path | None,
    *,
    output_suffix: str | None = None,
    strip_word_timing: bool = False,
) -> None:
    """Write one outcome to disk."""
    src_str = getattr(outcome, "source_id", None)
    if not src_str:
        raise typer.BadParameter("outcome missing source_id; cannot determine output path")
    src = Path(src_str)
    if out_dir is None:
        target = src.with_suffix(output_suffix) if output_suffix else src
    else:
        rel = src.relative_to(root)
        if output_suffix:
            rel = rel.with_suffix(output_suffix)
        target = out_dir / rel
        # Ensure the symlink-resolved target stays under out_dir.
        target.parent.mkdir(parents=True, exist_ok=True)
        safe_resolve(target.parent, out_dir.resolve())
    target.parent.mkdir(parents=True, exist_ok=True)
    outcome.write(str(target), strip_word_timing=strip_word_timing)


def require_api_key(provider: str, ini_key: str, env_var: str) -> str:
    """Return the configured key or raise a Typer-friendly error.

    The error message names the exact INI key and env var so users can
    immediately fix the configuration.
    """
    key = _ba_config.get_api_key(provider, interactive=True)
    if key:
        return key
    raise typer.BadParameter(
        f"No {provider} key. Set {env_var} env var or "
        f"`{ini_key}` in ~/.batchalign.ini",
    )


__all__ = [
    "CHAT_EXTENSIONS",
    "MEDIA_EXTENSIONS",
    "collect_ai_inputs",
    "collect_chat_inputs",
    "collect_media_inputs",
    "safe_resolve",
    "write_outcome",
    "write_outcomes",
    "require_api_key",
]
