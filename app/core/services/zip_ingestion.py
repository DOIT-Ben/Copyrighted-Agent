from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

from app.core.utils.text import ensure_dir


BLOCKED_SUFFIXES = {".exe", ".bat", ".cmd", ".sh", ".ps1", ".dll", ".msi", ".com"}
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]+')
IGNORED_FILE_NAMES = {".ds_store"}
IGNORED_DIR_NAMES = {"__macosx"}
FILENAME_HINTS = (
    "\u8f6f\u8457",
    "\u7533\u8bf7",
    "\u4fe1\u606f\u91c7\u96c6\u8868",
    "\u7528\u6237\u4f7f\u7528\u8bf4\u660e\u4e66",
    "\u8bf4\u660e\u4e66",
    "\u6e90\u4ee3\u7801",
    "\u8f6f\u4ef6\u6587\u6863",
    "\u6587\u6863",
    "\u534f\u8bae",
)
LIKELY_MOJIBAKE_CHARS = {"\ufffd", "\u03c3", "\u03a6", "\u2551", "\u2568", "\u2592", "\u2500"}


def _sanitize_part(part: str) -> str:
    part = INVALID_FILENAME_CHARS.sub("_", part).strip().rstrip(".")
    return part or "_"


def _score_member_name(value: str) -> int:
    score = 0
    for hint in FILENAME_HINTS:
        if hint in value:
            score += 12

    for char in value:
        if char in "/._-()[] " or char.isdigit():
            score += 1
            continue
        code_point = ord(char)
        if 0x4E00 <= code_point <= 0x9FFF:
            score += 4
            continue
        if char.isascii() and char.isalnum():
            score += 2
            continue
        if char in LIKELY_MOJIBAKE_CHARS:
            score -= 8
            continue
        if 0x2500 <= code_point <= 0x259F or 0x0370 <= code_point <= 0x03FF:
            score -= 6
            continue
        if code_point < 32:
            score -= 8
            continue
        score -= 1

    return score


def _decode_member_name(member_name: str, encoding: str) -> str | None:
    try:
        raw_bytes = member_name.encode("cp437")
    except UnicodeEncodeError:
        return None

    try:
        return raw_bytes.decode(encoding)
    except UnicodeDecodeError:
        return None


def _repair_member_name(member_name: str) -> str:
    best_name = member_name
    best_score = _score_member_name(member_name)

    for encoding in ("utf-8", "gb18030"):
        candidate = _decode_member_name(member_name, encoding)
        if not candidate or candidate == member_name:
            continue
        candidate_score = _score_member_name(candidate)
        if candidate_score > best_score + 3:
            best_name = candidate
            best_score = candidate_score

    return best_name


def _safe_member_path(member_name: str) -> Path:
    raw_parts = [part for part in Path(member_name).parts if part not in ("", ".", "..")]
    safe_parts = [_sanitize_part(part) for part in raw_parts]
    return Path(*safe_parts) if safe_parts else Path("_")


def _should_ignore_member(member_name: str) -> bool:
    member_path = Path(member_name)
    if member_path.name.lower() in IGNORED_FILE_NAMES:
        return True
    if member_path.name.startswith("._"):
        return True
    return any(part.lower() in IGNORED_DIR_NAMES for part in member_path.parts)


def safe_extract_zip(zip_path: str | Path, destination: str | Path) -> list[Path]:
    zip_path = Path(zip_path)
    destination = ensure_dir(destination).resolve()
    extracted: list[Path] = []

    with zipfile.ZipFile(zip_path, "r") as archive:
        for member in archive.infolist():
            member_name = _repair_member_name(member.filename)
            member_path = Path(member_name)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"Zip Slip attempt detected: {member_name}")
            if member.is_dir():
                continue
            if _should_ignore_member(member_name):
                continue
            if member_path.suffix.lower() in BLOCKED_SUFFIXES:
                raise ValueError(f"Blocked executable content in archive: {member_name}")

            safe_relative_path = _safe_member_path(member_name)
            final_path = (destination / safe_relative_path).resolve()
            if destination not in final_path.parents and final_path != destination:
                raise ValueError(f"Zip Slip attempt detected: {member_name}")

            ensure_dir(final_path.parent)
            with archive.open(member, "r") as source, open(final_path, "wb") as target:
                shutil.copyfileobj(source, target)
            extracted.append(final_path)

    return extracted
