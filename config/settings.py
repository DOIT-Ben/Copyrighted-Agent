# 软著智能体配置

import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 默认设置
DEFAULT_CONFIG = {
    "api_provider": "minimax",
    "model": "MiniMax-Text-01",
    "api_base": "https://api.minimax.chat/v1/text/chatcompletion_pro",

    # PDF 转换设置
    "pdf_method": "auto",  # auto, com, libreoffice, docx

    # 审查设置
    "first_n_pages": 30,  # 前N页
    "last_n_pages": 30,  # 后N页
    "source_min_lines": 50,  # 源码每页最少行数
    "document_min_lines": 30,  # 文档每页最少行数

    # 输出设置
    "output_format": "text",  # text, json
    "report_template": "standard",  # standard, detailed
}

# 环境变量配置
ENV_VARS = {
    "MINIMAX_API_KEY": "MiniMax API Key",
    "OPENAI_API_KEY": "OpenAI API Key (备用)",
}

# 支持的 API 提供商
API_PROVIDERS = {
    "minimax": {
        "name": "MiniMax",
        "model": "MiniMax-Text-01",
        "api_base": "https://api.minimax.chat/v1/text/chatcompletion_pro",
    },
    "openai": {
        "name": "OpenAI",
        "model": "gpt-4o",
        "api_base": "https://api.openai.com/v1/chat/completions",
    },
}


def load_config():
    """加载配置"""
    config = DEFAULT_CONFIG.copy()

    # 从环境变量覆盖
    for key in ENV_VARS:
        if key in os.environ:
            config[key.lower()] = os.environ[key]

    return config


def get_api_key() -> str:
    """获取 API Key"""
    return os.environ.get("MINIMAX_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
