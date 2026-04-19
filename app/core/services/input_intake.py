from __future__ import annotations

import shutil
from pathlib import Path

from app.core.services.zip_ingestion import BLOCKED_SUFFIXES, _safe_member_path
from app.core.utils.text import ensure_dir


IGNORED_FILE_NAMES = {".ds_store"}
IGNORED_DIR_NAMES = {"__macosx"}


def should_ignore_path(path: str | Path) -> bool:
    path = Path(path)
    name = path.name.lower()
    if name in IGNORED_FILE_NAMES:
        return True
    if name.startswith("._"):
        return True
    return any(part.lower() in IGNORED_DIR_NAMES for part in path.parts)


def stage_directory_input(source_dir: str | Path, destination: str | Path) -> list[Path]:
    source_dir = Path(source_dir).resolve()
    destination = ensure_dir(destination).resolve()
    staged: list[Path] = []

    for file_path in sorted(source_dir.rglob("*")):
        if not file_path.is_file():
            continue
        relative_path = file_path.relative_to(source_dir)
        if should_ignore_path(relative_path):
            continue
        if file_path.suffix.lower() in BLOCKED_SUFFIXES:
            raise ValueError(f"Blocked executable content in directory input: {relative_path}")

        safe_relative_path = _safe_member_path(relative_path.as_posix())
        final_path = (destination / safe_relative_path).resolve()
        if destination not in final_path.parents and final_path != destination:
            raise ValueError(f"Unsafe path detected in directory input: {relative_path}")

        ensure_dir(final_path.parent)
        shutil.copy2(file_path, final_path)
        staged.append(final_path)

    return staged
