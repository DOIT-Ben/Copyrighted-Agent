#!/usr/bin/env python3
"""
软著智能体 - 统一CLI入口
整合：内容提取、脱敏、审查、报告生成

用法:
    python cli.py --folder <文件夹路径>           # 批量审查
    python cli.py --folder . --type 合作协议      # 只审查合作协议
    python cli.py --source <源码> --doc <说明书>  # 单项目审查
    python cli.py --desensitize <文件>           # 仅脱敏
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import olefile

# ============ 配置 ============
VERSION = "2.0.0"
PROJECT_NAME = "软著智能体"

# 错误等级
SEV_SEVERE = "严重"    # 事实性矛盾，影响合同有效性
SEV_MODERATE = "中度" # 一致性问题，条款间不协调
SEV_MINOR = "轻微"    # 文字表达问题，不影响合同效力

# 脱敏规则
DESENSITIZE_RULES = [
    # 公司名称
    (r'南京追光智研技术咨询有限公司', '[公司A]'),
    (r'江西中医药大学', '[大学B]'),
    (r'杭州极光灵愈人工智能科技有限公司', '[公司B]'),
    # 人名（拼音首字母缩写）
    (r'寻文洁', '[xwj]'),
    (r'钟文杰', '[zwj]'),
    (r'范宋祺', '[fsq]'),
    (r'张贤', '[zx]'),
    (r'江晨希', '[jcx]'),
    (r'廖建宇', '[ljy]'),
    (r'彭惠', '[ph]'),
    (r'傅劲哲', '[fjz]'),
    (r'黄奔', '[hb]'),
    # 身份证号
    (r'\d{15,18}', '[身份证号]'),
    (r'[0-9X]{14,18}', '[身份证号]'),
    # 信用代码
    (r'91320191MAEF0NAB2Q', '[统一社会信用代码]'),
    (r'123600004910159513', '[事业单位法人证书号]'),
]

# 错字检测（轻微级）- 通用
TYPO_PATTERNS = [
    (r'签定', '签订', '法律文件应用"签订"'),
    (r'定合同', '订合同', '应用"订"'),
]

# 错字检测 - 软著文档专用
DOC_TYPO_PATTERNS = [
    # 命名不一致
    (r'Media\s+Pipe', 'MediaPipe', 'Google官方产品名为MediaPipe，不应分开写作Media Pipe'),
    # 标点符号连续
    (r'[。；，、]\.{2,}', r'。', '连续标点符号'),
    (r'\.{2,}[。；，、]', r'。', '连续标点符号'),
    (r'[。；，、]\.{3,}', r'。。。', '连续标点符号'),
    # 常见错别字
    (r'份', '份', '需确认"份"的使用是否正确'),  # 占位，待确认
]

# 常见错别字字典（软著文档）
COMMON_DOC_TYPOS = {
    '编程': '编程',  # 正确
    '程序': '程序',  # 正确
    '代码': '代码',  # 正确
    '函数': '函数',  # 正确
    '模块': '模块',  # 正确
}


# ============ 工具函数 ============

def read_doc_file(path):
    """读取旧版 .doc 文件，返回纯文本"""
    try:
        ole = olefile.OleFileIO(path)
        data = ole.openstream('WordDocument').read()
        text = data.decode('utf-16-le', errors='ignore')
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        ole.close()
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)
    except Exception as e:
        return f"[读取失败: {e}]"


def read_pdf_file(path):
    """读取 PDF 文件（简单文本提取）"""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        text = '\n'.join([page.get_text() for page in doc])
        doc.close()
        return text
    except Exception:
        return ""


def read_file(path):
    """根据文件类型读取内容"""
    p = Path(path)
    if p.suffix.lower() == '.pdf':
        return read_pdf_file(path)
    return read_doc_file(path)


def extract_code_from_doc(path):
    """从.doc提取代码内容"""
    try:
        ole = olefile.OleFileIO(path)
        data = ole.openstream('WordDocument').read()
        text = data.decode('utf-16-le', errors='ignore')
        ole.close()
        parts = text.split('\x00')
        code_parts = []
        for part in parts:
            if not part.strip():
                continue
            chinese_count = len(re.findall(r'[\u4e00-\u9fff]', part))
            english_count = len(re.findall(r'[a-zA-Z]', part))
            total = chinese_count + english_count
            if total == 0:
                continue
            if english_count / total > 0.5 and english_count > 10:
                code_parts.append(part)
        return ' '.join(code_parts)
    except Exception as e:
        return f"[提取失败: {e}]"


def desensitize(text):
    """执行脱敏处理"""
    result = text
    for pattern, replacement in DESENSITIZE_RULES:
        result = re.sub(pattern, replacement, result)
    return result


def get_project_root(file_path):
    """从任意层级路径回到项目根目录"""
    return Path(file_path).resolve().parent.parent.parent


def save_file(content, output_path):
    """保存文件（自动创建目录）"""
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(content)


# ============ 合作协议一致性检查函数 ============

def check_date_contradictions(text):
    """
    检查日期矛盾（严重）：
    提取所有日期引用，按"事件语义"分组，同一组内出现不同日期则报警。
    策略：按行提取日期，根据上下文（前后各15字）判断是否为同一事件。
    """
    issues = []

    # 提取所有带上下文的日期
    # 匹配：YYYY年MM月DD日 或 YYYY年MM月 或 MM月DD日
    # (?P<prefix>.{0,20})(?P<full>\d{4}年\d{1,2}月\d{1,2}日)(?P<suffix>.{0,20})
    # |(?P<partial>\d{1,2}月\d{1,2}日)
    date_pattern = re.compile(
        r'(?P<prefix>.{0,20})(?P<full>\d{4}年\d{1,2}月\d{1,2}日)(?P<suffix>.{0,20})'
        r'|(?P<partial>\d{1,2}月\d{1,2}日)'
    )

    # 按"关键语义标签"对日期分组
    # 例如："签订日期"组、"生效日期"组、"终止日期"组
    semantic_groups = defaultdict(list)
    # 提取每行并匹配日期
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        for m in date_pattern.finditer(line):
            full = m.group('full')
            partial = m.group('partial')
            date_str = full or partial
            if not date_str:
                continue
            prefix = (m.group('prefix') or '').strip()
            suffix = (m.group('suffix') or '').strip()
            ctx = (prefix + '|' + suffix).strip()

            # 识别语义标签（常见关键词）
            semantics = []
            for kw in ['签订', '签署', '生效', '开始', '起始', '终止', '结束', '解除', '到期', '续签']:
                if kw in ctx:
                    semantics.append(kw)
            tag = '|'.join(sorted(semantics)) if semantics else '__other__'

            # 标准化：补全年份（如果是MM月DD日格式，尝试从文中推断）
            normalized = normalize_date(date_str, text)
            semantic_groups[tag].append({
                'date': date_str,
                'normalized': normalized,
                'context': ctx,
                'line': line[:60],
            })

    # 检查每个语义组内是否有矛盾
    for tag, entries in semantic_groups.items():
        if tag == '__other__':
            continue
        if len(entries) < 2:
            continue
        dates = [e['normalized'] for e in entries]
        unique_dates = set(dates)
        if len(unique_dates) > 1:
            date_strs = ', '.join([e['date'] for e in entries])
            issues.append({
                'severity': SEV_SEVERE,
                'category': '日期矛盾',
                'desc': f'同一语义节点（{tag}）出现多个不同日期：{date_strs}',
                'details': [e['line'] for e in entries],
            })

    return issues


def normalize_date(date_str, text):
    """
    标准化日期字符串为 comparable 格式。
    若只有月日，尝试从合同标题或上下文推断年份。
    """
    # 完整日期
    m = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # 只有月日，尝试从合同标题提取年份
    title_year = re.search(r'20\d{2}年', text[:500])
    year = title_year.group().replace('年', '') if title_year else '____'
    m2 = re.match(r'(\d{1,2})月(\d{1,2})日', date_str)
    if m2:
        return f"{year}-{int(m2.group(1)):02d}-{int(m2.group(2)):02d}"

    return date_str


def check_party_name_consistency(text):
    """
    检查当事人名称一致性（严重）：
    提取所有当事人名称，检查同一实体是否有多重表述。
    策略：收集所有"甲/乙方"、"公司名"出现情况，检查数量是否匹配。
    """
    issues = []

    # 提取所有被引用为公司/实体的名称（脱敏后文本）
    # 查找 [公司A] [公司B] [大学B] 等格式
    desensitized_names = re.findall(r'\[(?:公司|大学|单位)[A-Z]\]', text)
    # 查找甲、乙、丙方
    party_refs = re.findall(r'((?:甲|乙|丙|丁)(?:方|方代表?|方当事人?))', text)
    # 查找全名出现次数
    full_names = re.findall(r'南京追光智研技术咨询有限公司|江西中医药大学|杭州极光灵愈人工智能科技有限公司', text)

    # 如果文中出现公司全名，也应该出现脱敏标记，二者数量应该接近
    if full_names and desensitized_names:
        if len(full_names) != len(desensitized_names):
            issues.append({
                'severity': SEV_SEVERE,
                'category': '当事人名称不一致',
                'desc': f'公司全名出现 {len(full_names)} 次，脱敏标记出现 {len(desensitized_names)} 次，数量不匹配',
                'details': [],
            })

    # 甲乙丙方计数（正常应有2-3方，且应与签名块数量一致）
    party_count = len(set(party_refs))
    if party_count >= 2:
        # 检查合同期限里是否有矛盾的时间表述
        pass

    return issues


def check_amount_consistency(text):
    """
    检查金额一致性（中度）：
    提取所有金额，统计出现次数，多次出现应一致。
    """
    issues = []

    # 提取所有金额：X元、X万元、X.X万元
    amounts = re.findall(r'(\d+(?:\.\d+)?\s*(?:万)?元)', text)
    if not amounts:
        return issues

    # 归一化：去掉空格
    amounts = [a.replace(' ', '') for a in amounts]
    unique_amounts = set(amounts)

    if len(unique_amounts) > 1 and len(amounts) > 1:
        # 有多个不同金额，逐一列出（可能是合理的设计费、违约金等）
        # 只在金额完全相同数字但写法不一时报警
        # 例如 "10万元" 和 "100000元" 同时出现
        issues.append({
            'severity': SEV_MODERATE,
            'category': '金额多次出现',
            'desc': f'合同中出现 {len(unique_amounts)} 种不同金额：{", ".join(unique_amounts)}，请确认是否存在笔误或需统一写法',
            'details': [],
        })

    return issues


def check_contract_number_consistency(text):
    """
    检查合同编号一致性（中度）：
    提取合同编号，检查全文是否一致。
    """
    issues = []

    # 匹配各种合同编号格式
    contract_nums = re.findall(
        r'(?:合同[号]?[：:]\s*)?(\d{4}[-_]\d{3,4}(?:[_-]\d+)?|'
        r'20\d{2}[年]\d{2}[月]\d{2}[日])',
        text
    )
    contract_nums = list(set(contract_nums))

    if len(contract_nums) > 1:
        issues.append({
            'severity': SEV_MODERATE,
            'category': '合同编号不一致',
            'desc': f'发现多个不同编号：{", ".join(contract_nums)}',
            'details': [],
        })

    return issues


def check_signature_blocks(text):
    """
    检查签章块一致性（中度）：
    统计"签章"、"甲方"、"乙方"等关键词出现次数，判断是否匹配。
    """
    issues = []

    # 提取甲乙丙出现次数
    parties = re.findall(r'((?:甲|乙|丙|丁)(?:方|方代表?|方当事人?|签章?))', text)
    party_counts = defaultdict(int)
    for p in parties:
        first_char = p[0]
        party_counts[first_char] += 1

    # 签章区块数量（通过连续空行+关键词判断）
    sig_blocks = len(re.findall(r'签章[：:]|甲方\s*[：:]|乙方\s*[：:]', text))

    unique_parties = len(party_counts)
    if unique_parties >= 2 and sig_blocks > 0:
        if abs(unique_parties - sig_blocks) > 1:
            issues.append({
                'severity': SEV_MODERATE,
                'category': '签章块数量异常',
                'desc': f'合同提及 {unique_parties} 方当事人，但签章区域出现 {sig_blocks} 处，请确认是否完整',
                'details': [],
            })

    return issues


def check_typos(text):
    """检查错字（轻微）"""
    issues = []
    for pattern, correction, desc in TYPO_PATTERNS:
        for m in re.finditer(pattern, text):
            issues.append({
                'severity': SEV_MINOR,
                'category': '用词不当',
                'desc': f'"{m.group(0)}" 应改为 "{correction}"（{desc}）',
                'location': f'位置 {m.start()} 字符',
                'suggest': correction,
            })
    return issues


def check_duration_dates_consistency(text):
    """
    检查合同期限与日期的一致性（中度）：
    例如：写"合作期限一年（2024年1月1日至2024年12月31日）"则天数应为365天。
    """
    issues = []

    # 提取类似 "一年"、"两年"、"6个月" 的期限描述
    duration_patterns = re.findall(
        r'((?:合作|履行|有效|保密)?期限)\s*[:：]?\s*'
        r'(\d+)\s*(?:年|个月|month|year)',
        text
    )

    for label, num in duration_patterns:
        num = int(num)
        # 检查是否有对应的日期范围
        date_range = re.search(
            r'(\d{4})年(\d{1,2})月(\d{1,2})日\s*[至-]\s*(\d{4})年(\d{1,2})月(\d{1,2})日',
            text
        )
        if date_range and num >= 1:
            y1, m1, d1 = int(date_range.group(1)), int(date_range.group(2)), int(date_range.group(3))
            y2, m2, d2 = int(date_range.group(4)), int(date_range.group(5)), int(date_range.group(6))
            from datetime import date
            try:
                start = date(y1, m1, d1)
                end = date(y2, m2, d2)
                days = (end - start).days
                expected_days = num * 365 if '年' in text[date_range.start():date_range.end()+10] else num * 30
                if abs(days - expected_days) > 35:  # 允许一个月误差
                    issues.append({
                        'severity': SEV_MODERATE,
                        'category': '期限与日期不匹配',
                        'desc': f'期限写{num}{"年" if "年" in text[date_range.start():date_range.end()+10] else "个月"}，'
                                f'但对应日期区间为{days}天（约{int(days/365)}年），请核对',
                        'details': [date_range.group(0)],
                    })
            except Exception:
                pass

    return issues


# ============ 软著文档错别字检测 ============

def check_doc_typos(text):
    """
    检查软著文档错别字（轻微）：
    - Media Pipe vs MediaPipe 命名不一致
    - 连续标点符号
    - 其他常见错别字
    """
    issues = []
    
    # Media Pipe 命名不一致
    media_pipe_variants = re.findall(r'Media\s+Pipe', text)
    if media_pipe_variants:
        count = len(media_pipe_variants)
        issues.append({
            'severity': SEV_MINOR,
            'category': '命名不一致',
            'desc': f'发现"Media Pipe"写法{count}处，应统一为官方名称"MediaPipe"',
            'suggest': 'MediaPipe',
        })
    
    # 连续标点符号检测
    double_punct = re.findall(r'[。；，、]{2,}', text)
    if double_punct:
        unique_punct = set(double_punct)
        issues.append({
            'severity': SEV_MINOR,
            'category': '标点符号问题',
            'desc': f'发现连续标点符号：{", ".join(unique_punct)}',
            'suggest': '修正为单个标点',
        })
    
    # 句号连续（"。。"或"。。。"）
    double_dots = re.findall(r'\.{2,}', text)
    if double_dots:
        issues.append({
            'severity': SEV_MINOR,
            'category': '标点符号问题',
            'desc': f'发现连续句号：{", ".join(set(double_dots))}',
            'suggest': '删除多余句号',
        })
    
    return issues


# ============ 源码乱码检测 ============

def check_code_garbled_ratio(code_text):
    """
    检查源码乱码比例（中度）：
    - 检测不可读字符比例
    - 超过阈值则报警
    """
    issues = []
    
    if not code_text or len(code_text) < 100:
        return issues
    
    # 计算乱码字符（不可打印字符、控制字符）
    total_chars = len(code_text)
    garbled_chars = 0
    
    # 检测非ASCII且非Unicode可读字符
    for char in code_text:
        code = ord(char)
        # 控制字符（排除换行、回车、制表符）
        if code < 32 and code not in (9, 10, 13):
            garbled_chars += 1
        # 非打印区域（中文标点范围外）
        elif 0x7F <= code <= 0x9F:
            garbled_chars += 1
        # 私用区域
        elif 0xE000 <= code <= 0xF8FF:
            garbled_chars += 1
    
    garbled_ratio = garbled_chars / total_chars if total_chars > 0 else 0
    
    if garbled_ratio > 0.05:  # 超过5%乱码
        issues.append({
            'severity': SEV_MODERATE,
            'category': '代码可读性问题',
            'desc': f'代码乱码比例为{garbled_ratio:.1%}（{garbled_chars}/{total_chars}字符），建议将.doc转为.py或.txt格式',
            'suggest': '转换源码格式',
        })
    
    return issues


# ============ 跨材料版本号一致性检查 ============

def check_cross_material_version(all_results):
    """
    检查跨材料版本号一致性（严重）：
    - 合作协议版本号
    - 软著文档版本号
    - 信息采集表版本号
    - 源代码版本号
    返回：各材料的版本号信息
    """
    issues = []
    version_info = {}
    
    for result in all_results:
        if result['type'] == '软著文档':
            # 从软著文档提取版本号
            doc = result.get('content', '')
            v1_count = len(re.findall(r'[vV]1\.0', doc))
            v2_count = len(re.findall(r'[vV]2\.0', doc))
            version_info['软著文档'] = {
                'V1.0': v1_count,
                'V2.0': v2_count,
                'dominant': 'V2.0' if v2_count > v1_count else 'V1.0',
            }
        elif result['type'] == '源码':
            code = result.get('content', '')
            v1_count = len(re.findall(r'[vV]1\.0', code))
            v2_count = len(re.findall(r'[vV]2\.0', code))
            version_info['源代码'] = {
                'V1.0': v1_count,
                'V2.0': v2_count,
                'dominant': 'V2.0' if v2_count > v1_count else 'V1.0',
            }
        elif result['type'] == '信息采集表':
            info = result.get('info', {})
            version_info['信息采集表'] = {
                'version': info.get('version', '未找到'),
            }
    
    # 比对软著文档和源代码版本号
    if '软著文档' in version_info and '源代码' in version_info:
        doc_ver = version_info['软著文档']['dominant']
        code_ver = version_info['源代码']['dominant']
        if doc_ver != code_ver:
            issues.append({
                'severity': SEV_SEVERE,
                'category': '跨材料版本不一致',
                'desc': f'软著文档主要版本为{doc_ver}，源代码主要版本为{code_ver}，版本不一致',
                'suggest': '统一版本号',
            })
    
    return issues, version_info


# ============ 信息采集表字段一致性检查 ============

def check_info_form_field_consistency(info_form_result, all_results):
    """
    检查信息采集表字段与其他材料的一致性（中度）：
    - 软件名称一致性
    - 版本号一致性
    - 源程序行数一致性
    """
    issues = []
    
    if not info_form_result or info_form_result.get('type') != '信息采集表':
        return issues
    
    info = info_form_result.get('info', {})
    info_name = info.get('name', '')
    info_version = info.get('version', '')
    info_lines = info.get('lines', 0)
    
    # 从其他材料提取信息进行比对
    for result in all_results:
        if result['type'] == '软著文档':
            doc = result.get('content', '')
            # 提取软件名称
            doc_name_match = re.search(r'基于Media\s*Pipe\s*Pose的[脑卒中患者]?[极光医疗]?[医疗粗大]?关节运动分析系统', doc)
            if doc_name_match and info_name:
                if doc_name_match.group(0) not in info_name and info_name not in doc_name_match.group(0):
                    issues.append({
                        'severity': SEV_MODERATE,
                        'category': '软件名称不一致',
                        'desc': f'信息采集表名称："{info_name[:30]}..." 与软著文档中的名称存在差异',
                        'suggest': '确认软件名称是否一致',
                    })
        
        elif result['type'] == '源码':
            code = result.get('content', '')
            # 提取代码行数
            code_lines = len(code.split('\n'))
            if info_lines > 0 and abs(code_lines - info_lines) > info_lines * 0.1:  # 差异超过10%
                issues.append({
                    'severity': SEV_MODERATE,
                    'category': '源程序行数不一致',
                    'desc': f'信息采集表填写{info_lines}行，源码提取{code_lines}行，差异超过10%',
                    'suggest': '确认源程序行数',
                })
    
    return issues


# ============ 合作协议审查 ============

def review_agreement(file_path):
    """审查合作协议，返回结构化结果"""
    print(f"\n  审查合作协议...")
    original_path = Path(file_path)
    base_path = get_project_root(file_path)

    content = read_file(file_path)
    if not content or content.startswith('[读取失败'):
        print(f"    ✗ 文件读取失败")
        return {
            'file': str(original_path),
            'type': '合作协议',
            'passed': False,
            'errors': [],
            'report_path': None,
        }

    desensitized = desensitize(content)

    # ---- 1. 保存脱敏版 ----
    des_dir = base_path / 'output' / '_desensitized'
    des_dir.mkdir(parents=True, exist_ok=True)
    des_path = des_dir / f"{original_path.stem}_脱敏版.md"
    save_file(f"# 合作协议\n\n```\n{desensitized}\n```", des_path)
    print(f"    ✓ 脱敏版已保存: {des_path.relative_to(base_path)}")

    # ---- 2. 执行各项检查 ----
    all_issues = []
    all_issues.extend(check_typos(content))
    all_issues.extend(check_date_contradictions(content))
    all_issues.extend(check_party_name_consistency(desensitized))
    all_issues.extend(check_amount_consistency(content))
    all_issues.extend(check_contract_number_consistency(content))
    all_issues.extend(check_signature_blocks(content))
    all_issues.extend(check_duration_dates_consistency(content))

    # ---- 3. 生成本文件独立报告 ----
    rep_dir = base_path / 'output' / '_reports' / '合作协议'
    rep_dir.mkdir(parents=True, exist_ok=True)
    rep_path = rep_dir / f"{original_path.stem}_审查报告.md"
    write_single_agreement_report(rep_path, original_path.name, all_issues)

    # ---- 4. 打印摘要 ----
    sev_count = sum(1 for i in all_issues if i['severity'] == SEV_SEVERE)
    mod_count = sum(1 for i in all_issues if i['severity'] == SEV_MODERATE)
    min_count = sum(1 for i in all_issues if i['severity'] == SEV_MINOR)

    if all_issues:
        print(f"    ⚠ 共 {len(all_issues)} 个问题（严重{sev_count} / 中度{mod_count} / 轻微{min_count}）")
        for i in all_issues:
            if i['severity'] == SEV_SEVERE:
                print(f"      🔴 [{i['severity']}] {i['category']}: {i['desc']}")
            elif i['severity'] == SEV_MODERATE:
                print(f"      🟡 [{i['severity']}] {i['category']}: {i['desc']}")
            else:
                print(f"      🟢 [{i['severity']}] {i['desc']}")
    else:
        print(f"    ✓ 未发现问题")

    return {
        'file': str(original_path),
        'file_name': original_path.name,
        'type': '合作协议',
        'passed': sev_count == 0,
        'errors': all_issues,
        'sev_count': sev_count,
        'mod_count': mod_count,
        'min_count': min_count,
        'des_path': str(des_path),
        'report_path': str(rep_path),
    }


def write_single_agreement_report(path, file_name, issues):
    """写单个合作协议的 Markdown 审查报告"""
    sev = [i for i in issues if i['severity'] == SEV_SEVERE]
    mod = [i for i in issues if i['severity'] == SEV_MODERATE]
    min_ = [i for i in issues if i['severity'] == SEV_MINOR]

    lines = []
    lines.append(f"# 合作协议审查报告")
    lines.append("")
    lines.append(f"**文件**: `{file_name}`")
    lines.append(f"**审查时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}")
    lines.append("")

    # 结论摘要
    lines.append("## 一、审查结论")
    lines.append("")
    if not issues:
        lines.append("| 等级 | 问题数 |")
        lines.append("|------|------|")
        lines.append("| 严重 | 0 |")
        lines.append("| 中度 | 0 |")
        lines.append("| 轻微 | 0 |")
        lines.append("")
        lines.append("✅ **未发现任何问题，审查通过。**")
    else:
        lines.append("| 等级 | 问题数 |")
        lines.append("|------|------|")
        lines.append(f"| 🔴 严重 | {len(sev)} |")
        lines.append(f"| 🟡 中度 | {len(mod)} |")
        lines.append(f"| 🟢 轻微 | {len(min_)} |")
        lines.append("")
        if sev:
            lines.append(f"⚠️ **存在 {len(sev)} 个严重问题，必须修改。**")
        elif mod:
            lines.append(f"⚠️ **存在 {len(mod)} 个中度问题，建议修改。**")
        else:
            lines.append("✅ **无严重问题，仅有轻微文字问题，可酌情修改。**")
    lines.append("")

    # 问题详情
    if issues:
        lines.append("## 二、问题详情")
        lines.append("")

        for idx, issue in enumerate(issues, 1):
            sev_label = issue['severity']
            icon = "🔴" if sev_label == SEV_SEVERE else "🟡" if sev_label == SEV_MODERATE else "🟢"
            lines.append(f"### {idx}. [{sev_label}] {issue['category']}")
            lines.append(f"**问题**: {issue['desc']}")
            if issue.get('details'):
                lines.append("**相关原文**:")
                for detail in issue['details'][:3]:
                    lines.append(f"> {detail}")
            if issue.get('suggest'):
                lines.append(f"**建议修改**: `{issue['suggest']}`")
            lines.append("")

    lines.append("---")
    lines.append(f"*本报告由软著智能体自动生成 | {datetime.now().strftime('%Y年%m月%d日 %H:%M')}*")

    save_file('\n'.join(lines), path)


# ============ 合作协议汇总报告 ============

def write_agreement_summary(results, output_path):
    """生成合作协议批量审查汇总报告"""
    total = len(results)
    sev_total = sum(r.get('sev_count', 0) for r in results)
    mod_total = sum(r.get('mod_count', 0) for r in results)
    min_total = sum(r.get('min_count', 0) for r in results)
    passed = sum(1 for r in results if r.get('passed', False))
    failed = total - passed

    lines = []
    lines.append("# 合作协议审查综合报告")
    lines.append("")
    lines.append(f"**审查时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}")
    lines.append(f"**审查依据**: 《中华人民共和国民法典》合同编、《计算机软件著作权登记办法》")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 一、总体概况")
    lines.append("")
    lines.append(f"共审查 **{total} 份**合作协议，发现问题情况如下：")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 审查总数 | {total} 份 |")
    lines.append(f"| ✅ 通过 | {passed} 份 |")
    lines.append(f"| ⚠️ 需修改 | {failed} 份 |")
    lines.append(f"| 🔴 严重问题合计 | {sev_total} 个 |")
    lines.append(f"| 🟡 中度问题合计 | {mod_total} 个 |")
    lines.append(f"| 🟢 轻微问题合计 | {min_total} 个 |")
    lines.append("")

    # 分类统计
    lines.append("## 二、按文件统计")
    lines.append("")
    lines.append("| 文件名 | 严重 | 中度 | 轻微 | 结论 |")
    lines.append("|--------|------|------|------|------|")
    for r in results:
        status = "✅ 通过" if r['passed'] else "⚠️ 需修改"
        lines.append(f"| {r['file_name']} | {r['sev_count']} | {r['mod_count']} | {r['min_count']} | {status} |")
    lines.append("")

    # 问题清单（按文件分组）
    lines.append("## 三、各文件问题详情")
    lines.append("")
    for idx, r in enumerate(results, 1):
        lines.append(f"### {idx}. {r['file_name']}")
        lines.append(f"**路径**: `output/_reports/合作协议/{r['file_name'].rsplit('.', 1)[0]}_审查报告.md`")
        lines.append("")
        if not r['errors']:
            lines.append("✅ 无问题")
        else:
            for e in r['errors']:
                icon = "🔴" if e['severity'] == SEV_SEVERE else "🟡" if e['severity'] == SEV_MODERATE else "🟢"
                lines.append(f"- {icon} **[{e['severity']}] {e['category']}**: {e['desc']}")
        lines.append("")

    # 严重问题汇总表
    sev_issues = [(r['file_name'], e) for r in results for e in r['errors'] if e['severity'] == SEV_SEVERE]
    if sev_issues:
        lines.append("## 四、严重问题汇总（必须修改）")
        lines.append("")
        lines.append("| 文件 | 问题 |")
        lines.append("|------|------|")
        for fname, e in sev_issues:
            lines.append(f"| {fname} | {e['category']}: {e['desc']} |")
        lines.append("")

    lines.append("---")
    lines.append(f"*本报告由软著智能体自动生成 | {datetime.now().strftime('%Y年%m月%d日 %H:%M')}*")

    save_file('\n'.join(lines), output_path)


# ============ 其他审查函数 ============

def review_info_form(file_path):
    """审查信息采集表"""
    print(f"\n  审查信息采集表...")
    original_path = Path(file_path)
    base_path = get_project_root(file_path)

    content = read_file(file_path)
    desensitized = desensitize(content)

    des_dir = base_path / 'output' / '_desensitized'
    des_dir.mkdir(parents=True, exist_ok=True)
    des_path = des_dir / f"{original_path.stem}_脱敏版.md"
    save_file(f"# 信息采集表\n\n```\n{desensitized}\n```", des_path)
    print(f"    ✓ 脱敏版已保存: {des_path.relative_to(base_path)}")

    # 提取信息
    info = {'name': '', 'version': '', 'lines': len(content.split('\n'))}
    m = re.search(r'软件名称[：:]\s*(.+?)(?:\n|$)', content)
    if m: info['name'] = m.group(1).strip()
    m = re.search(r'[vV](\d+\.\d+)', content)
    if m: info['version'] = f"V{m.group(1)}"
    m = re.search(r'著作权人[：:]\s*(.+?)(?:\n|$)', content)
    if m: info['company'] = m.group(1).strip()

    print(f"    ✓ 软件名称: {info['name']}")
    print(f"    ✓ 版本号: {info['version']}")

    return {
        'file': str(original_path),
        'file_name': original_path.name,
        'type': '信息采集表',
        'passed': True,
        'errors': [],
        'info': info,
        'report_path': None,
    }


def review_source_code(file_path):
    """审查源码"""
    print(f"\n  审查源码...")
    original_path = Path(file_path)
    base_path = get_project_root(file_path)

    code = extract_code_from_doc(file_path)
    desensitized = desensitize(code)

    clean_dir = base_path / 'output' / '_cleaned'
    clean_dir.mkdir(parents=True, exist_ok=True)
    out_path = clean_dir / f"{original_path.stem}_分析版.md"
    save_file(f"# 源码\n\n```python\n{desensitized}\n```", str(out_path))
    print(f"    ✓ 分析版已保存: {out_path.relative_to(base_path)}")

    # 保存脱敏版
    des_dir = base_path / 'output' / '_desensitized'
    des_dir.mkdir(parents=True, exist_ok=True)
    des_path = des_dir / f"{original_path.stem}_提取脱敏版.md"
    save_file(f"# 源码\n\n```python\n{desensitized}\n```", str(des_path))
    print(f"    ✓ 脱敏版已保存: {des_path.relative_to(base_path)}")

    # 执行各项检查
    all_issues = []

    # 1. 核心模块完整性检查
    checks = {
        'has_header': 'BasedMediaPipePose' in code or 'MediaPipePose' in code,
        'has_angle_calc': 'calculate_angle' in code or 'angle' in code.lower(),
        'has_pose_analyzer': 'PoseAnalyzer' in code or 'pose' in code.lower(),
        'has_export': 'export' in code.lower() or 'save' in code.lower(),
    }

    for key, value in checks.items():
        print(f"    {'✓' if value else '✗'} {key}")

    # 2. 乱码比例检查（新增）
    garbled_issues = check_code_garbled_ratio(code)
    all_issues.extend(garbled_issues)
    for issue in garbled_issues:
        print(f"    🟡 [中度] {issue['category']}: {issue['desc']}")

    passed = all(checks.values()) and len(garbled_issues) == 0

    return {
        'file': str(original_path),
        'file_name': original_path.name,
        'type': '源码',
        'passed': passed,
        'checks': checks,
        'errors': all_issues,
        'content': code,  # 用于跨材料比对
        'report_path': None,
    }


def review_document(file_path):
    """审查说明书"""
    print(f"\n  审查说明书...")
    original_path = Path(file_path)
    base_path = get_project_root(file_path)

    content = read_file(file_path)
    desensitized = desensitize(content)

    # 保存脱敏版
    des_dir = base_path / 'output' / '_desensitized'
    des_dir.mkdir(parents=True, exist_ok=True)
    des_path = des_dir / f"{original_path.stem}_脱敏版.md"
    save_file(f"# 软著文档\n\n```\n{desensitized}\n```", str(des_path))
    print(f"    ✓ 脱敏版已保存: {des_path.relative_to(base_path)}")

    clean_dir = base_path / 'output' / '_cleaned'
    clean_dir.mkdir(parents=True, exist_ok=True)
    out_path = clean_dir / f"{original_path.stem}_分析版.md"
    save_file(f"# 软著文档\n\n```\n{content}\n```", str(out_path))
    print(f"    ✓ 分析版已保存: {out_path.relative_to(base_path)}")

    # 执行各项检查
    all_issues = []

    # 1. 版本号一致性检查
    v1 = len(re.findall(r'[vV]1\.0', content))
    v2 = len(re.findall(r'[vV]2\.0', content))
    if v2 > 0 and v2 > v1:
        all_issues.append({
            'severity': SEV_MODERATE,
            'category': '版本号不一致',
            'desc': f'发现V2.0({v2}次)多于V1.0({v1}次)，同一文档内版本描述不一致',
        })
        print(f"    ⚠ {all_issues[-1]['desc']}")
    else:
        print(f"    ✓ 版本号一致")

    # 2. 错别字检查（新增）
    typo_issues = check_doc_typos(content)
    all_issues.extend(typo_issues)
    for issue in typo_issues:
        print(f"    🟢 [轻微] {issue['category']}: {issue['desc']}")

    # 统计
    sev_count = sum(1 for i in all_issues if i['severity'] == SEV_SEVERE)
    mod_count = sum(1 for i in all_issues if i['severity'] == SEV_MODERATE)
    min_count = sum(1 for i in all_issues if i['severity'] == SEV_MINOR)

    if all_issues:
        print(f"    ⚠ 共 {len(all_issues)} 个问题（严重{sev_count} / 中度{mod_count} / 轻微{min_count}）")

    return {
        'file': str(original_path),
        'file_name': original_path.name,
        'type': '软著文档',
        'passed': sev_count == 0,
        'errors': all_issues,
        'sev_count': sev_count,
        'mod_count': mod_count,
        'min_count': min_count,
        'content': content,  # 用于跨材料比对
        'report_path': None,
    }


def generate_summary_report(results, output_path):
    """生成综合汇总报告（多类型混合）"""
    lines = []
    lines.append("# 软著申请材料审查综合报告")
    lines.append(f"\n> 审查时间：{datetime.now().strftime('%Y年%m月%d日')}")
    lines.append("> 审查依据：《计算机软件著作权登记办法》及软著审查规范")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ---- 执行跨材料检查 ----
    cross_issues, version_info = check_cross_material_version(results)

    # 信息采集表一致性检查
    info_form_result = next((r for r in results if r['type'] == '信息采集表'), None)
    if info_form_result:
        info_consistency_issues = check_info_form_field_consistency(info_form_result, results)
        cross_issues.extend(info_consistency_issues)

    # ---- 统计 ----
    sev_total = sum(r.get('sev_count', 0) for r in results)
    mod_total = sum(r.get('mod_count', 0) for r in results)
    min_total = sum(r.get('min_count', 0) for r in results)

    # 加上跨材料问题
    cross_sev = sum(1 for i in cross_issues if i['severity'] == SEV_SEVERE)
    cross_mod = sum(1 for i in cross_issues if i['severity'] == SEV_MODERATE)
    cross_min = sum(1 for i in cross_issues if i['severity'] == SEV_MINOR)

    lines.append("## 一、审查结论总览")
    lines.append("")
    lines.append("| 材料 | 文件 | 结果 | 说明 |")
    lines.append("|------|------|------|------|")

    for r in results:
        status = "✅ 通过" if r['passed'] else "⚠️ 需修改"
        desc = ""
        if r['type'] == '合作协议':
            if r['errors']:
                desc = f"严重{r.get('sev_count',0)}/中度{r.get('mod_count',0)}/轻微{r.get('min_count',0)}"
            else:
                desc = "无问题"
        elif r['type'] == '软著文档':
            if r.get('errors'):
                errs = r['errors']
                desc = f"严重{r.get('sev_count',0)}/中度{r.get('mod_count',0)}/轻微{r.get('min_count',0)}"
            else:
                desc = "无问题"
        elif r['type'] == '源码':
            desc = "代码结构完整" if r['passed'] else f"缺少: {', '.join(k for k,v in r.get('checks',{}).items() if not v)}"
            if r.get('errors'):
                desc += f" | 另有{len(r['errors'])}个问题"
        elif r['type'] == '信息采集表':
            info = r.get('info', {})
            desc = f"软件: {info.get('name','N/A')[:20]}... / 版本: {info.get('version','N/A')}"
        lines.append(f"| {r['type']} | {r['file_name']} | {status} | {desc} |")

    lines.append("")
    lines.append(f"**问题汇总**：严重 {sev_total + cross_sev} / 中度 {mod_total + cross_mod} / 轻微 {min_total + cross_min}")
    lines.append("")

    # ---- 跨材料问题 ----
    if cross_issues:
        lines.append("## 二、跨材料一致性问题")
        lines.append("")
        lines.append("| 严重性 | 问题类型 | 说明 |")
        lines.append("|--------|----------|------|")
        for issue in cross_issues:
            icon = "🔴" if issue['severity'] == SEV_SEVERE else "🟡" if issue['severity'] == SEV_MODERATE else "🟢"
            lines.append(f"| {icon} {issue['severity']} | {issue['category']} | {issue['desc']} |")
        lines.append("")

    # ---- 版本号比对表 ----
    if version_info:
        lines.append("## 三、版本号跨材料比对")
        lines.append("")
        lines.append("| 材料 | V1.0出现次数 | V2.0出现次数 | 主要版本 |")
        lines.append("|------|--------------|--------------|----------|")
        for material, info in version_info.items():
            if 'V1.0' in info:
                lines.append(f"| {material} | {info.get('V1.0', 0)} | {info.get('V2.0', 0)} | {info.get('dominant', 'N/A')} |")
            else:
                lines.append(f"| {material} | - | - | {info.get('version', 'N/A')} |")
        lines.append("")

    lines.append(f"\n*本报告由软著智能体 v{VERSION} 自动生成*")

    save_file('\n'.join(lines), output_path)


# ============ CLI 主程序 ============

INPUT_SUBDIRS = {
    '合作协议':   '合作协议',
    '软著文档':   '软著文档',
    '源代码':     '源码',
    '信息采集表': '信息采集表',
}
ALL_TYPES = list(INPUT_SUBDIRS.keys())


def scan_input_dir(base_path):
    """扫描 input/ 下各子目录，返回 {类型: [文件路径列表]}"""
    input_path = base_path / 'input'
    categorized = {}
    for subdir_name, type_name in INPUT_SUBDIRS.items():
        subdir = input_path / subdir_name
        if subdir.is_dir():
            files = sorted(f for f in subdir.glob('*') if f.is_file() and f.suffix.lower() in ('.doc', '.docx', '.pdf', '.txt'))
            if files:
                categorized[type_name] = files
    return categorized


def main():
    parser = argparse.ArgumentParser(
        description=f"{PROJECT_NAME} v{VERSION} - 软著申请材料自动审查工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python cli.py --folder .                       # 审查所有材料
  python cli.py --folder . --type 合作协议       # 只审查合作协议
  python cli.py --folder . --type 软著文档       # 只审查软著文档
  python cli.py --folder . --type 源代码         # 只审查源码
  python cli.py --folder . --type 信息采集表     # 只审查信息采集表
  python cli.py --desensitize input/合作协议/xxx.doc  # 仅脱敏
        """
    )

    parser.add_argument('--version', '-v', action='version', version=f'{VERSION}')
    parser.add_argument('--folder', '-f', help='指定文件夹路径（input/ 子目录自动扫描）')
    parser.add_argument('--type', '-t', choices=ALL_TYPES, help=f'指定材料类型')
    parser.add_argument('--source', '-s', help='源码文件路径')
    parser.add_argument('--doc', '-d', help='说明书文件路径')
    parser.add_argument('--info', '-i', help='信息采集表文件路径')
    parser.add_argument('--agreement', '-a', help='合作协议文件路径')
    parser.add_argument('--desensitize', help='仅执行脱敏')
    parser.add_argument('--output', '-o', help='输出文件路径')

    args = parser.parse_args()

    print("=" * 70)
    print(f"{PROJECT_NAME} v{VERSION}")
    print("软著申请材料自动审查工具")
    print("=" * 70)

    results = []

    if args.folder:
        base_path = Path(args.folder).resolve()
    else:
        base_path = Path('.').resolve()

    print(f"\n工作目录: {base_path}")

    # -------- 批量模式 --------
    if args.folder and not any([args.source, args.doc, args.info, args.agreement]):
        categorized = scan_input_dir(base_path)
        if not categorized:
            print(f"\n未在 input/ 下找到任何材料")
            return

        types_to_process = [args.type] if args.type else list(categorized.keys())

        for type_name in types_to_process:
            files = categorized.get(type_name, [])
            if not files:
                continue
            print(f"\n{'='*60}")
            print(f"  [{type_name}] 共 {len(files)} 个文件")
            print('='*60)

            for file_path in files:
                print(f"\n  >> {file_path.name}")
                if type_name == '合作协议':
                    result = review_agreement(str(file_path))
                elif type_name == '信息采集表':
                    result = review_info_form(str(file_path))
                elif type_name == '源码':
                    result = review_source_code(str(file_path))
                elif type_name == '软著文档':
                    result = review_document(str(file_path))
                results.append(result)

        # -------- 生成汇总报告 --------
        if results:
            rep_dir = base_path / 'output' / '_reports'
            rep_dir.mkdir(parents=True, exist_ok=True)

            # 合作协议单独汇总
            ag_results = [r for r in results if r['type'] == '合作协议']
            if ag_results:
                ag_summary = rep_dir / '合作协议审查综合报告.md'
                write_agreement_summary(ag_results, str(ag_summary))
                print(f"\n{'='*60}")
                print(f"  合作协议汇总报告已生成: output/_reports/合作协议审查综合报告.md")
                print(f"  各文件独立报告在: output/_reports/合作协议/")

            # 通用汇总
            general_summary = rep_dir / '软著审查综合报告.md'
            generate_summary_report(results, str(general_summary))
            print(f"  综合报告: output/_reports/软著审查综合报告.md")

    # -------- 单文件模式 --------
    else:
        if args.agreement:
            results.append(review_agreement(args.agreement))
        if args.info:
            results.append(review_info_form(args.info))
        if args.source:
            results.append(review_source_code(args.source))
        if args.doc:
            results.append(review_document(args.doc))

        if results and args.output:
            generate_summary_report(results, args.output)

    # -------- 仅脱敏 --------
    if args.desensitize:
        content = read_file(args.desensitize)
        desensitized = desensitize(content)
        original_path = Path(args.desensitize)
        base_path = get_project_root(args.desensitize)
        out_dir = base_path / 'output' / '_desensitized'
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{original_path.stem}_脱敏版.txt"
        save_file(desensitized, str(out_path))
        print(f"\n✓ 脱敏完成: {out_path}")


if __name__ == "__main__":
    main()
