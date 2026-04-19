import olefile, re

path = 'input/合作协议/2510_合作协议.doc'
ole = olefile.OleFileIO(path)
data = ole.openstream('WordDocument').read()
text = data.decode('utf-16-le', errors='ignore')
ole.close()

# 去除控制字符
text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)

# 删除 CJK Extension 乱码字符（替换为空格）
text = re.sub(r'[\u3400-\u4dbf]', ' ', text)
text = re.sub(r'[\u4dc0-\u4dff]', ' ', text)
text = re.sub(r'[\u20000-\u2a6df\u2a700-\u2b73f\u2b740-\u2b81f\u2b820-\u2ceaf\u2ceb0-\u2ebef\u30000-\u3134f]', ' ', text)
text = re.sub(r'[\u3300-\u33ff\ufe30-\ufe4f\uf900-\ufaff]', ' ', text)
text = re.sub(r'[\uac00-\ud7af]', ' ', text)
text = re.sub(r'[\u2500-\u257f]', ' ', text)

# 按段落分割（双换行）
paragraphs = re.split(r'\n{2,}', text)

def paragraph_score(p):
    """计算段落的有意义程度分数"""
    chinese_main = len(re.findall(r'[\u4e00-\u9fff]', p))
    # 常用法律词汇（高度有意义）
    legal_terms = re.findall(
        r'甲方|乙方|丙方|丁方|戊方|己方|庚方|辛方|壬方|癸方|次甲方|'
        r'协议|合同|条款|签字|签章|日期|生效|终止|版权|著作权|'
        r'版本号|共同|各方|协商|软件开发|需求|测试|调试|编程|注册|'
        r'[一二三四五六七八九十]+[条款部款]', p
    )
    legal_score = len(legal_terms)
    # 总分 = 汉字数 * 2 + 法律词汇数 * 5
    return chinese_main * 2 + legal_score * 5

clean_paras = []
for para in paragraphs:
    para = re.sub(r'\s+', ' ', para).strip()
    if len(para) < 5:
        continue
    score = paragraph_score(para)
    chinese_main = len(re.findall(r'[\u4e00-\u9fff]', para))
    # 至少3个汉字 且 分数>=10
    if chinese_main >= 3 and score >= 10:
        clean_paras.append(para)

result = '\n\n'.join(clean_paras)
print(result[:5000])
print(f'\n--- Total: {len(result)} chars, {len(clean_paras)} paragraphs ---')
