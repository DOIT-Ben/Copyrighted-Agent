"""
PDF 文本提取模块
支持：
1. PyMuPDF (fitz) - 快速、保留布局信息
2. PyPDF2 - 简单文本提取
3. pdfplumber - 表格和布局分析
"""

import re
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PageInfo:
    """页面信息"""
    page_num: int
    text: str
    line_count: int
    has_header: bool  # 是否有页眉
    header_text: str = ""


class PDFTextExtractor:
    """PDF 文本提取器"""

    def __init__(self):
        self.pages: List[PageInfo] = []

    def extract(self, pdf_path: str, max_pages: Optional[int] = None) -> List[PageInfo]:
        """
        提取 PDF 文本内容

        Args:
            pdf_path: PDF 文件路径
            max_pages: 最大提取页数，None 表示全部

        Returns:
            页面信息列表
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

        # 优先使用 PyMuPDF
        try:
            return self._extract_with_pymupdf(pdf_path, max_pages)
        except ImportError:
            pass

        try:
            return self._extract_with_pypdf2(pdf_path, max_pages)
        except ImportError:
            pass

        raise ImportError("需要安装 PyMuPDF 或 PyPDF2")

    def _extract_with_pymupdf(self, pdf_path: Path, max_pages: Optional[int]) -> List[PageInfo]:
        """使用 PyMuPDF 提取"""
        import fitz  # pymupdf

        self.pages = []
        doc = fitz.open(str(pdf_path))

        total_pages = len(doc)
        extract_pages = min(total_pages, max_pages) if max_pages else total_pages

        # 常见页眉模式
        header_patterns = [
            r'^.+[vV]\d+\.\d+.+第?\d+页',
            r'^.+软件.+\d+\.\d+.+第?\d+页',
            r'^第\d+页',
        ]

        for page_num in range(extract_pages):
            page = doc[page_num]
            text = page.get_text("text")

            # 计算行数
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            line_count = len(lines)

            # 检测页眉
            header_text = ""
            has_header = False
            first_line = lines[0] if lines else ""

            for pattern in header_patterns:
                if re.match(pattern, first_line):
                    has_header = True
                    header_text = first_line
                    break

            page_info = PageInfo(
                page_num=page_num + 1,
                text=text,
                line_count=line_count,
                has_header=has_header,
                header_text=header_text
            )
            self.pages.append(page_info)

        doc.close()
        logger.info(f"提取 {len(self.pages)} 页文本 (PyMuPDF)")
        return self.pages

    def _extract_with_pypdf2(self, pdf_path: Path, max_pages: Optional[int]) -> List[PageInfo]:
        """使用 PyPDF2 提取"""
        from PyPDF2 import PdfReader

        self.pages = []
        reader = PdfReader(str(pdf_path))

        total_pages = len(reader.pages)
        extract_pages = min(total_pages, max_pages) if max_pages else total_pages

        header_patterns = [
            r'^.+[vV]\d+\.\d+.+第?\d+页',
            r'^.+软件.+\d+\.\d+.+第?\d+页',
            r'^第\d+页',
        ]

        for page_num in range(extract_pages):
            page = reader.pages[page_num]
            text = page.extract_text()

            lines = [l.strip() for l in text.split('\n') if l.strip()]
            line_count = len(lines)

            header_text = ""
            has_header = False
            first_line = lines[0] if lines else ""

            for pattern in header_patterns:
                if re.match(pattern, first_line):
                    has_header = True
                    header_text = first_line
                    break

            page_info = PageInfo(
                page_num=page_num + 1,
                text=text,
                line_count=line_count,
                has_header=has_header,
                header_text=header_text
            )
            self.pages.append(page_info)

        logger.info(f"提取 {len(self.pages)} 页文本 (PyPDF2)")
        return self.pages

    def get_full_text(self, start_page: int = 1, end_page: Optional[int] = None) -> str:
        """
        获取指定范围的完整文本

        Args:
            start_page: 起始页 (1-indexed)
            end_page: 结束页 (1-indexed)，None 表示到末尾

        Returns:
            拼接后的文本
        """
        if not self.pages:
            return ""

        texts = []
        for page in self.pages:
            if start_page <= page.page_num <= (end_page or float('inf')):
                texts.append(f"\n=== 第 {page.page_num} 页 ===\n")
                texts.append(page.text)

        return "\n".join(texts)

    def analyze_pages(self, pages: List[int] = None) -> Dict:
        """
        分析指定页面或全部页面的统计信息

        Args:
            pages: 页面列表，None 表示全部

        Returns:
            统计分析结果
        """
        target_pages = self.pages if pages is None else [
            p for p in self.pages if p.page_num in pages
        ]

        if not target_pages:
            return {}

        total_lines = sum(p.line_count for p in target_pages)
        avg_lines = total_lines / len(target_pages)
        pages_with_header = sum(1 for p in target_pages if p.has_header)
        min_lines = min(p.line_count for p in target_pages)
        max_lines = max(p.line_count for p in target_pages)

        return {
            "page_count": len(target_pages),
            "total_lines": total_lines,
            "avg_lines_per_page": round(avg_lines, 1),
            "min_lines": min_lines,
            "max_lines": max_lines,
            "pages_with_header": pages_with_header,
            "header_percentage": round(pages_with_header / len(target_pages) * 100, 1)
        }


def extract_source_code_pages(pdf_path: str, first_n: int = 30, last_n: int = 30) -> Tuple[str, str]:
    """
    提取源码鉴别材料：前30页 + 后30页

    Args:
        pdf_path: PDF 文件路径
        first_n: 前n页数量
        last_n: 后n页数量

    Returns:
        (前30页文本, 后30页文本)
    """
    extractor = PDFTextExtractor()
    extractor.extract(pdf_path)

    total = len(extractor.pages)

    # 前30页
    first_pages = extractor.get_full_text(1, first_n)

    # 后30页
    last_start = max(1, total - last_n + 1)
    last_pages = extractor.get_full_text(last_start, total)

    return first_pages, last_pages


def extract_document_pages(pdf_path: str, first_n: int = 30, last_n: int = 30) -> Tuple[str, str]:
    """
    提取文档鉴别材料：前30页 + 后30页

    Args:
        pdf_path: PDF 文件路径
        first_n: 前n页数量
        last_n: 后n页数量

    Returns:
        (前30页文本, 后30页文本)
    """
    return extract_source_code_pages(pdf_path, first_n, last_n)


if __name__ == "__main__":
    # 测试提取
    import sys
    if len(sys.argv) > 1:
        extractor = PDFTextExtractor()
        extractor.extract(sys.argv[1])

        for page in extractor.pages[:5]:  # 前5页
            print(f"\n=== 第 {page.page_num} 页 (行数: {page.line_count}) ===")
            print(page.text[:500] + "..." if len(page.text) > 500 else page.text)

        # 统计分析
        stats = extractor.analyze_pages()
        print("\n=== 统计分析 ===")
        for k, v in stats.items():
            print(f"  {k}: {v}")
    else:
        print("用法: python pdf_extractor.py <pdf_file>")
