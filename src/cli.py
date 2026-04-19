"""
软著智能体 CLI 接口
用法：
    python -m 软著智能体.cli --source 源码.pdf --doc 说明书.pdf --name "XX系统" --version "V1.0"
"""

import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.reviewer import CopyrightReviewer, SoftwareInfo, review_copyright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_report(results: dict):
    """格式化打印审查报告"""
    print("\n" + "=" * 60)
    print("📋 软著申请材料审查报告")
    print("=" * 60)

    # 综合报告
    if results.get("comprehensive_report"):
        report = results["comprehensive_report"]

        print(f"\n📊 综合通过率: {report.get('综合通过率', 'N/A')}")
        print(f"📝 审查结论: {report.get('审查结论', 'N/A')}")
        print(f"⚠️  风险等级: {report.get('风险等级', 'N/A')}")

        # 必须修改项
        must_fix = report.get("必须修改项", [])
        if must_fix:
            print("\n🔴 必须修改项 (P0):")
            for i, item in enumerate(must_fix, 1):
                print(f"  {i}. [{item.get('类别', '未知')}] {item.get('问题', 'N/A')}")
                print(f"     依据: {item.get('依据', 'N/A')}")
                print(f"     方案: {item.get('修改方案', 'N/A')}")

        # 建议修改项
        suggest_fix = report.get("建议修改项", [])
        if suggest_fix:
            print("\n🟡 建议修改项 (P1):")
            for i, item in enumerate(suggest_fix, 1):
                print(f"  {i}. [{item.get('类别', '未知')}] {item.get('问题', 'N/A')}")
                print(f"     建议: {item.get('修改建议', 'N/A')}")

        # 最终报告
        if report.get("最终报告"):
            print("\n" + "-" * 60)
            print(report["最终报告"])

    # 源码审查详情
    if results.get("source_review"):
        source = results["source_review"]
        print("\n" + "-" * 60)
        print("📄 源码审查结果")

        format_check = source.get("格式检查", {})
        content_check = source.get("内容检查", {})

        print(f"\n  格式检查:")
        print(f"    - 页眉规范: {'✅' if format_check.get('页眉规范') else '❌'}")
        print(f"    - 页码连续: {'✅' if format_check.get('页码连续') else '❌'}")
        print(f"    - 行数达标: {'✅' if format_check.get('行数达标') else '❌'}")

        issues = format_check.get("问题列表", [])
        if issues:
            print(f"    - 问题: {', '.join(issues)}")

    # 文档审查详情
    if results.get("document_review"):
        doc = results["document_review"]
        print("\n" + "-" * 60)
        print("📑 文档审查结果")

        format_check = doc.get("格式检查", {})
        struct_check = doc.get("结构检查", {})

        print(f"\n  结构检查:")
        print(f"    - 目录完整: {'✅' if struct_check.get('目录完整') else '❌'}")
        print(f"    - 功能概述有: {'✅' if struct_check.get('功能概述有') else '❌'}")
        print(f"    - 运行环境有: {'✅' if struct_check.get('运行环境有') else '❌'}")

        print(f"\n  格式检查:")
        print(f"    - 页眉规范: {'✅' if format_check.get('页眉规范') else '❌'}")
        print(f"    - 页码连续: {'✅' if format_check.get('页码连续') else '❌'}")
        print(f"    - 行数达标: {'✅' if format_check.get('行数达标') else '❌'}")

    print("\n" + "=" * 60)
    print("💡 提示: 完整报告请查看 JSON 输出")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="软著智能体 - 源码与说明书审查工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 审查 PDF 文件
  python -m 软著智能体.cli --source 源码.pdf --doc 说明书.pdf

  # 转换 Word 后审查
  python -m 软著智能体.cli --source-word 源码.docx --doc-word 说明书.docx

  # 指定软件信息
  python -m 软著智能体.cli --source 源码.pdf --doc 说明书.pdf \\
      --name "订单管理系统" --version "V1.0" --company "XX科技有限公司"

  # 输出 JSON 格式
  python -m 软著智能体.cli --source 源码.pdf --doc 说明书.pdf --json

  # 设置 API Key
  export MINIMAX_API_KEY=your_key
  python -m 软著智能体.cli --source 源码.pdf --doc 说明书.pdf
        """
    )

    # 文件参数
    file_group = parser.add_argument_group("文件输入")
    file_group.add_argument("--source", "-s", help="源码 PDF 文件路径")
    file_group.add_argument("--doc", "-d", help="说明书 PDF 文件路径")
    file_group.add_argument("--source-word", help="源码 Word 文件 (自动转PDF)")
    file_group.add_argument("--doc-word", help="说明书 Word 文件 (自动转PDF)")

    # 软件信息
    info_group = parser.add_argument_group("软件信息")
    info_group.add_argument("--name", "-n", help="软件名称")
    info_group.add_argument("--version", "-v", help="版本号")
    info_group.add_argument("--company", "-c", help="著作权人/公司名称")

    # 输出选项
    output_group = parser.add_argument_group("输出选项")
    output_group.add_argument("--json", "-j", action="store_true", help="输出 JSON 格式")
    output_group.add_argument("--output", "-o", help="结果输出到文件")

    # API 配置
    api_group = parser.add_argument_group("API 配置")
    api_group.add_argument("--api-key", help="API Key (或设置环境变量 MINIMAX_API_KEY)")

    args = parser.parse_args()

    # 检查输入
    if not any([args.source, args.doc, args.source_word, args.doc_word]):
        parser.print_help()
        print("\n❌ 错误: 请提供至少一个文件 (--source, --doc, --source-word, 或 --doc-word)")
        sys.exit(1)

    # 构建软件信息
    software_info = SoftwareInfo(
        name=args.name or "",
        version=args.version or "",
        company=args.company or ""
    )

    # 执行审查
    logger.info("开始软著审查...")

    reviewer = CopyrightReviewer(api_key=args.api_key)

    try:
        results = reviewer.review(
            source_file=args.source_word,
            document_file=args.doc_word,
            source_pdf=args.source,
            document_pdf=args.doc,
            software_info=software_info,
            api_key=args.api_key
        )

        # 输出结果
        if args.json:
            output = json.dumps(results, ensure_ascii=False, indent=2)
            if args.output:
                Path(args.output).write_text(output, encoding='utf-8')
                print(f"结果已保存到: {args.output}")
            else:
                print(output)
        else:
            print_report(results)
            if args.output:
                # 保存 JSON 格式的结果
                Path(args.output).write_text(
                    json.dumps(results, ensure_ascii=False, indent=2),
                    encoding='utf-8'
                )
                print(f"详细结果已保存到: {args.output}")

    except Exception as e:
        logger.error(f"审查失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
