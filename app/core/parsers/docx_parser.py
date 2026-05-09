from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from app.core.utils.text import clean_text


class DocxParser:
    def parse_blocks(self, file_path: str | Path) -> list[dict]:
        file_path = Path(file_path)
        blocks: list[dict] = []
        with zipfile.ZipFile(file_path, "r") as archive:
            xml_data = archive.read("word/document.xml")
        root = ET.fromstring(xml_data)
        body = next((node for node in root.iter() if node.tag.endswith("}body")), None)
        if body is None:
            return blocks
        for child in list(body):
            if not child.tag.endswith("}p"):
                continue
            texts: list[str] = []
            for node in child.iter():
                if node.tag.endswith("}t") and node.text:
                    texts.append(node.text)
            text = clean_text("".join(texts))
            if not text:
                continue
            style_name = ""
            for node in child.iter():
                if node.tag.endswith("}pStyle"):
                    style_name = str(node.attrib.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "") or "")
                    break
            is_heading = style_name.lower().startswith("heading")
            blocks.append({"page": None, "text": text, "is_heading": is_heading, "source": "docx_paragraph"})
        return blocks

    def parse(self, file_path: str | Path) -> str:
        blocks = self.parse_blocks(file_path)
        return clean_text("\n".join(str(block.get("text", "") or "") for block in blocks))
