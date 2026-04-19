"""
Word 转 PDF 转换模块
支持多种转换方式：
1. Windows COM (需安装 MS Office)
2. LibreOffice (跨平台)
3. DocxWriter (仅支持简单文档)
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class WordToPDFConverter:
    """Word 文档转 PDF 转换器"""

    def __init__(self, method: str = "auto"):
        """
        初始化转换器

        Args:
            method: 转换方式 "auto", "com", "libreoffice", "docx"
        """
        self.method = method

    def convert(self, word_path: str, output_dir: Optional[str] = None) -> str:
        """
        将 Word 文档转换为 PDF

        Args:
            word_path: Word 文件路径
            output_dir: 输出目录，默认与源文件相同目录

        Returns:
            生成的 PDF 文件路径
        """
        word_path = Path(word_path)
        if not word_path.exists():
            raise FileNotFoundError(f"Word 文件不存在: {word_path}")

        if output_dir is None:
            output_dir = word_path.parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        pdf_path = output_dir / f"{word_path.stem}.pdf"

        # 自动检测最佳转换方式
        if self.method == "auto":
            self.method = self._detect_best_method()

        if self.method == "com":
            return self._convert_via_com(word_path, pdf_path)
        elif self.method == "libreoffice":
            return self._convert_via_libreoffice(word_path, output_dir)
        elif self.method == "docx":
            return self._convert_via_docx(word_path, pdf_path)
        else:
            raise ValueError(f"不支持的转换方式: {self.method}")

    def _detect_best_method(self) -> str:
        """自动检测最佳转换方式"""
        # Windows 且安装了 Office
        if sys.platform == "win32":
            try:
                import win32com.client
                win32com.client.Dispatch("Word.Application")
                logger.info("检测到 Windows COM，可使用 Office 进行转换")
                return "com"
            except ImportError:
                logger.warning("未安装 pywin32，尝试其他方式")
            except Exception:
                logger.warning("Office COM 不可用，尝试其他方式")

        # 检查 LibreOffice
        if self._check_libreoffice():
            return "libreoffice"

        # 回退到简单转换
        return "docx"

    def _check_libreoffice(self) -> bool:
        """检查 LibreOffice 是否可用"""
        try:
            result = subprocess.run(
                ["libreoffice", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"检测到 LibreOffice: {result.stdout.strip()}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return False

    def _convert_via_com(self, word_path: Path, pdf_path: Path) -> str:
        """通过 Windows COM 使用 MS Office 转换"""
        try:
            import win32com.client
            import pythoncom
        except ImportError:
            raise ImportError("需要安装 pywin32: pip install pywin32")

        # 初始化 COM
        pythoncom.CoInitialize()

        try:
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            word.DisplayAlerts = False

            # 打开文档
            doc = word.Documents.Open(str(word_path.absolute()))

            # 转换为 PDF
            # wdFormatPDF = 17
            doc.SaveAs(str(pdf_path.absolute()), FileFormat=17)

            doc.Close()
            word.Quit()

            logger.info(f"Word -> PDF 转换成功: {pdf_path}")
            return str(pdf_path)

        finally:
            pythoncom.CoUninitialize()

    def _convert_via_libreoffice(self, word_path: Path, output_dir: Path) -> str:
        """通过 LibreOffice 转换"""
        cmd = [
            "libreoffice",
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(output_dir.absolute()),
            str(word_path.absolute())
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice 转换失败: {result.stderr}")

        # LibreOffice 输出到同一目录
        pdf_path = output_dir / f"{word_path.stem}.pdf"

        if not pdf_path.exists():
            raise FileNotFoundError(f"转换后 PDF 不存在: {pdf_path}")

        logger.info(f"Word -> PDF 转换成功: {pdf_path}")
        return str(pdf_path)

    def _convert_via_docx(self, word_path: Path, pdf_path: Path) -> str:
        """简单转换（仅文本，无格式）"""
        try:
            from docx import Document
        except ImportError:
            raise ImportError("需要安装 python-docx: pip install python-docx")

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
        except ImportError:
            raise ImportError("需要安装 reportlab: pip install reportlab")

        doc = Document(word_path)

        # 创建 PDF
        pdf_doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                story.append(Paragraph(text, styles['Normal']))
                story.append(Spacer(1, 12))

        pdf_doc.build(story)
        logger.warning("使用简单转换，格式和图片可能丢失")
        logger.info(f"Word -> PDF 转换成功: {pdf_path}")
        return str(pdf_path)


def batch_convert(word_dir: str, output_dir: Optional[str] = None,
                  pattern: str = "*.docx") -> list:
    """
    批量转换 Word 文件到 PDF

    Args:
        word_dir: Word 文件目录
        output_dir: 输出目录
        pattern: 文件匹配模式

    Returns:
        转换成功的 PDF 路径列表
    """
    word_dir = Path(word_dir)
    converter = WordToPDFConverter()

    results = []
    for word_path in word_dir.glob(pattern):
        try:
            pdf_path = converter.convert(str(word_path), output_dir)
            results.append(pdf_path)
        except Exception as e:
            logger.error(f"转换失败 {word_path}: {e}")

    return results


if __name__ == "__main__":
    # 测试转换
    import sys
    if len(sys.argv) > 1:
        converter = WordToPDFConverter()
        pdf_path = converter.convert(sys.argv[1])
        print(f"生成 PDF: {pdf_path}")
    else:
        print("用法: python word_to_pdf.py <word_file>")
