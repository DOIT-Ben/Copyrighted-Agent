from __future__ import annotations

import re
import zlib
from pathlib import Path

from app.core.utils.text import best_effort_decode, clean_text


class PdfParser:
    _stream_pattern = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.S)

    def _decoded_streams(self, data: bytes) -> list[bytes]:
        streams: list[bytes] = []
        for match in self._stream_pattern.finditer(data):
            blob = match.group(1)
            try:
                streams.append(zlib.decompress(blob))
            except Exception:
                continue
        return streams

    def _extract_cmap(self, streams: list[bytes]) -> dict[str, str]:
        code_map: dict[str, str] = {}
        for stream in streams:
            if b"begincmap" not in stream:
                continue
            for source_hex, target_hex in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", stream):
                if len(source_hex) != 4:
                    continue
                try:
                    target_text = bytes.fromhex(target_hex.decode("ascii")).decode("utf-16-be", errors="ignore")
                except ValueError:
                    continue
                if target_text:
                    code_map[source_hex.decode("ascii").upper()] = target_text
        return code_map

    def _decode_hex_text(self, hex_text: bytes, code_map: dict[str, str]) -> str:
        value = hex_text.decode("ascii", errors="ignore").upper()
        chars: list[str] = []
        for index in range(0, len(value), 4):
            chunk = value[index:index + 4]
            if len(chunk) < 4:
                continue
            chars.append(code_map.get(chunk, ""))
        return "".join(chars)

    def _extract_text_from_streams(self, streams: list[bytes], code_map: dict[str, str]) -> str:
        parts: list[str] = []
        for stream in streams:
            if b"Tj" not in stream and b"TJ" not in stream:
                continue
            for hex_text in re.findall(rb"<([0-9A-Fa-f]+)>\s*Tj", stream):
                decoded = self._decode_hex_text(hex_text, code_map)
                if decoded:
                    parts.append(decoded)
            for array_payload in re.findall(rb"\[(.*?)\]\s*TJ", stream, flags=re.S):
                for hex_text in re.findall(rb"<([0-9A-Fa-f]+)>", array_payload):
                    decoded = self._decode_hex_text(hex_text, code_map)
                    if decoded:
                        parts.append(decoded)
        return "".join(parts)

    def parse(self, file_path: str | Path) -> str:
        data = Path(file_path).read_bytes()
        streams = self._decoded_streams(data)
        text = ""
        if streams:
            code_map = self._extract_cmap(streams)
            if code_map:
                text = self._extract_text_from_streams(streams, code_map)
        if not text:
            chunks = re.findall(rb"\(([^()]{1,200})\)", data)
            if chunks:
                text = "\n".join(best_effort_decode(chunk) for chunk in chunks)
            else:
                text = best_effort_decode(data)
        return clean_text(text)
