from __future__ import annotations

from pathlib import Path

from app.core.utils.text import read_text_file, clean_text


class CodeMaterialParser:
    def parse(self, file_path: str | Path) -> str:
        try:
            return clean_text(read_text_file(file_path))
        except Exception:
            data = Path(file_path).read_bytes()
            return clean_text(data.decode("utf-8", errors="ignore"))

