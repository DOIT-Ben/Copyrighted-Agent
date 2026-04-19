from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from app.core.utils.text import clean_text


class DocxParser:
    def parse(self, file_path: str | Path) -> str:
        file_path = Path(file_path)
        texts: list[str] = []
        with zipfile.ZipFile(file_path, "r") as archive:
            xml_data = archive.read("word/document.xml")
        root = ET.fromstring(xml_data)
        for node in root.iter():
            if node.tag.endswith("}t") and node.text:
                texts.append(node.text)
        return clean_text("\n".join(texts))

