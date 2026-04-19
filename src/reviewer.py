"""
软著审查智能体
核心逻辑：分析软著文档是否达标
"""

import os
import sys

# 添加项目根目录到路径，支持相对导入和直接运行
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import json
import logging
import re
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict

from src.pdf_extractor import PDFTextExtractor, extract_source_code_pages, extract_document_pages
from src.word_to_pdf import WordToPDFConverter
from prompts.review_prompt import (
    build_source_review_prompt,
    build_document_review_prompt,
    build_consistency_check_prompt,
    build_comprehensive_review_prompt
)

logger = logging.getLogger(__name__)


@dataclass
class SoftwareInfo:
    """软件基本信息"""
    name: str = ""
    version: str = ""
    company: str = ""


@dataclass
class ReviewResult:
    """审查结果"""
    category: str
    passed: bool
    score: float  # 0-100
    issues: List[str]
    suggestions: List[str]
    details: Dict[str, Any]


class CopyrightReviewer:
    """软著审查智能体"""

    def __init__(self, api_key: Optional[str] = None, model: str = "minimax/minimax"):
        """
        初始化审查智能体

        Args:
            api_key: API密钥，默认从环境变量读取
            model: 使用的模型
        """
        import os
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("MINIMAX_API_KEY")
        self.model = model

        if not self.api_key:
            logger.warning("未设置 API_KEY，将使用模拟模式进行测试")

    def review(
        self,
        source_file: Optional[str] = None,
        document_file: Optional[str] = None,
        source_pdf: Optional[str] = None,
        document_pdf: Optional[str] = None,
        software_info: Optional[SoftwareInfo] = None,
        api_key: Optional[str] = None
    ) -> Dict:
        """
        执行完整审查流程

        Args:
            source_file: 源码 Word 文件
            document_file: 说明书 Word 文件
            source_pdf: 源码 PDF 文件（直接提供）
            document_pdf: 说明书 PDF 文件（直接提供）
            software_info: 软件基本信息
            api_key: API密钥（覆盖初始化时的设置）

        Returns:
            审查结果字典
        """
        api_key = api_key or self.api_key

        results = {
            "source_review": None,
            "document_review": None,
            "consistency_check": None,
            "comprehensive_report": None
        }

        # 1. 转换 Word 到 PDF（如果需要）
        if source_file and not source_pdf:
            logger.info(f"转换源码 Word -> PDF: {source_file}")
            converter = WordToPDFConverter()
            source_pdf = converter.convert(source_file)

        if document_file and not document_pdf:
            logger.info(f"转换文档 Word -> PDF: {document_file}")
            converter = WordToPDFConverter()
            document_pdf = converter.convert(document_file)

        # 2. 提取源码内容
        source_first = ""
        source_last = ""
        if source_pdf:
            logger.info(f"提取源码 PDF 内容: {source_pdf}")
            source_first, source_last = extract_source_code_pages(source_pdf)

        # 3. 提取文档内容
        doc_first = ""
        doc_last = ""
        if document_pdf:
            logger.info(f"提取文档 PDF 内容: {document_pdf}")
            doc_first, doc_last = extract_document_pages(document_pdf)

        # 4. 执行审查（使用 AI）
        if api_key:
            # 源码审查
            if source_first or source_last:
                source_prompt = build_source_review_prompt(source_first, source_last)
                results["source_review"] = self._call_ai(source_prompt, api_key)

            # 文档审查
            if doc_first or doc_last:
                doc_prompt = build_document_review_prompt(doc_first, doc_last)
                results["document_review"] = self._call_ai(doc_prompt, api_key)

            # 一致性检查
            if software_info:
                consistency_prompt = self._build_consistency_prompt(
                    software_info, source_first, doc_first
                )
                results["consistency_check"] = self._call_ai(consistency_prompt, api_key)

            # 综合报告
            if results["source_review"] or results["document_review"]:
                report_prompt = build_comprehensive_review_prompt(
                    json.dumps(results["source_review"] or {}, ensure_ascii=False),
                    json.dumps(results["document_review"] or {}, ensure_ascii=False),
                    json.dumps(results["consistency_check"] or {}, ensure_ascii=False)
                )
                results["comprehensive_report"] = self._call_ai(report_prompt, api_key)
        else:
            # 模拟模式 - 本地分析
            results["source_review"] = self._mock_review("源码", source_first, source_last)
            results["document_review"] = self._mock_review("文档", doc_first, doc_last)
            results["comprehensive_report"] = self._mock_comprehensive(
                results["source_review"],
                results["document_review"]
            )

        return results

    def _call_ai(self, prompt: str, api_key: str) -> Dict:
        """调用 AI 进行分析"""
        import requests

        url = "https://api.minimax.chat/v1/text/chatcompletion_pro"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "MiniMax-Text-01",
            "messages": [
                {"role": "system", "content": "你是一位专业的软著登记审查员，严格按照官方规范审查。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=120)
            response.raise_for_status()
            result = response.json()

            content = result["choices"][0]["message"]["content"]

            # 尝试解析 JSON
            try:
                # 提取 ```json ... ``` 格式
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))

                # 直接解析
                return json.loads(content)
            except json.JSONDecodeError:
                logger.warning("AI 返回内容不是有效 JSON")
                return {"raw_content": content, "error": "JSON解析失败"}

        except Exception as e:
            logger.error(f"AI 调用失败: {e}")
            return {"error": str(e)}

    def _build_consistency_prompt(
        self,
        software_info: SoftwareInfo,
        source_text: str,
        doc_text: str
    ) -> str:
        """构建一致性检查提示词"""
        # 从源码和文档中提取软件名称和版本号
        source_name = self._extract_software_name(source_text) if source_text else ""
        doc_name = self._extract_software_name(doc_text) if doc_text else ""
        source_version = self._extract_version(source_text) if source_text else ""
        doc_version = self._extract_version(doc_text) if doc_text else ""

        return build_consistency_check_prompt(
            application_name=software_info.name or "[未提供]",
            source_name=source_name or "[未识别]",
            document_name=doc_name or "[未识别]",
            application_version=software_info.version or "[未提供]",
            source_version=source_version or "[未识别]",
            document_version=doc_version or "[未识别]"
        )

    def _extract_software_name(self, text: str) -> str:
        """从文本中提取软件名称"""
        if not text:
            return ""

        # 常见模式
        patterns = [
            r'软件名称[：:]\s*(.+?)(?:\n|$)',
            r'产品名称[：:]\s*(.+?)(?:\n|$)',
            r'"([^"]+(?:系统|软件|平台|应用|客户端|APP))"',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return ""

    def _extract_version(self, text: str) -> str:
        """从文本中提取版本号"""
        if not text:
            return ""

        patterns = [
            r'版本[号]?[：:]\s*(v?\d+\.\d+(?:\.\d+)?)',
            r'[vV](\d+\.\d+(?:\.\d+)?)',
            r'Version\s*(v?\d+\.\d+(?:\.\d+)?)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return ""

    def _mock_review(self, category: str, first: str, last: str) -> Dict:
        """模拟审查（无 API Key 时使用）"""
        total_chars = len(first) + len(last)
        total_lines = first.count('\n') + last.count('\n')

        return {
            "格式检查": {
                "页眉规范": total_chars > 100,
                "页码连续": True,
                "行数达标": total_lines > 100,
                "空行过多": False,
                "注释超标": False,
                "问题列表": []
            },
            "内容检查": {
                "核心模块完整": total_chars > 500,
                "逻辑衔接": True,
                "原创代码": True,
                "问题列表": []
            },
            "总体评估": {
                "通过率": "85%" if total_chars > 500 else "60%",
                "主要问题": "模拟审查仅供参考，请提供 API Key 获取真实审查结果",
                "修改建议": ["使用真实 API Key 获取详细建议"]
            }
        }

    def _mock_comprehensive(self, source: Dict, document: Dict) -> Dict:
        """模拟综合报告"""
        source_rate = source.get("总体评估", {}).get("通过率", "0%")
        doc_rate = document.get("总体评估", {}).get("通过率", "0%")

        try:
            avg_rate = (int(source_rate.strip('%')) + int(doc_rate.strip('%'))) // 2
        except:
            avg_rate = 70

        return {
            "综合通过率": f"{avg_rate}%",
            "审查结论": "修改后通过" if avg_rate < 90 else "通过",
            "风险等级": "中",
            "必须修改项": [],
            "建议修改项": [
                {
                    "类别": "提示",
                    "问题": "当前为模拟审查结果",
                    "修改建议": "请提供有效的 API Key 以获取真实审查结果"
                }
            ],
            "最终报告": f"""## 软著申请材料审查报告（模拟）

### 总体评估
- **综合通过率**: {avg_rate}%
- **审查结论**: 请提供 API Key 获取真实审查结果

### 注意事项
当前显示的是基于本地规则的初步分析，
完整的合规性审查需要配置 AI API。

### 下一步
1. 配置有效的 API Key
2. 重新提交材料进行完整审查
"""
        }


def review_copyright(
    source_file: Optional[str] = None,
    document_file: Optional[str] = None,
    source_pdf: Optional[str] = None,
    document_pdf: Optional[str] = None,
    software_name: str = "",
    software_version: str = "",
    company_name: str = "",
    api_key: Optional[str] = None
) -> Dict:
    """
    便捷函数：执行软著审查

    Args:
        source_file: 源码 Word 文件
        document_file: 说明书 Word 文件
        source_pdf: 源码 PDF 文件
        document_pdf: 说明书 PDF 文件
        software_name: 软件名称
        software_version: 版本号
        company_name: 公司名称
        api_key: API密钥

    Returns:
        审查结果
    """
    reviewer = CopyrightReviewer()

    software_info = SoftwareInfo(
        name=software_name,
        version=software_version,
        company=company_name
    )

    return reviewer.review(
        source_file=source_file,
        document_file=document_file,
        source_pdf=source_pdf,
        document_pdf=document_pdf,
        software_info=software_info,
        api_key=api_key
    )


if __name__ == "__main__":
    # 测试
    import sys

    if len(sys.argv) > 1:
        result = review_copyright(
            source_pdf=sys.argv[1],
            api_key=os.getenv("MINIMAX_API_KEY")
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("用法: python reviewer.py <source_pdf>")
