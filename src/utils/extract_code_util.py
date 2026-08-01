
import re

from src.utils.test_case import question_normal_short

#这个工具是对用户的输入进行预处理，拆分自然语言和代码


def extract_heuristic(text: str) -> str:
    """提取文本中所有看起来像 Python 代码的连续块（保留缩进，处理空行）"""
    lines = text.splitlines()
    result_blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # 空行或非代码行跳过
        if not line.strip() or not is_code_line(line):
            i += 1
            continue

        # 记录块起始
        start = i
        # 计算基准缩进（该行的缩进空格数）
        base_indent = len(line) - len(line.lstrip())

        # 初始化括号深度（仅用于续行判断）
        depth = 0
        for ch in line:
            if ch in '({[':
                depth += 1
            elif ch in ')}]':
                depth -= 1

        j = i + 1
        while j < len(lines):
            cur_line = lines[j]
            cur_stripped = cur_line.strip()

            # 空行：保留，继续扫描
            if not cur_stripped:
                j += 1
                continue

            # 计算当前行的缩进
            cur_indent = len(cur_line) - len(cur_line.lstrip())

            # 条件：深度归零、缩进小于基准、且不是行续行（括号、逗号、反斜杠结尾）
            if depth == 0 and cur_indent < base_indent:
                if not cur_line.rstrip().endswith(('(', '{', '[', ',', '\\')):
                    # 还需检查当前行是否为代码行，若是自然语言则也应结束
                    # 这里用 is_code_line 判断，如果非代码则视为自然语言，结束
                    if not is_code_line(cur_line):
                        break
                    # 如果是代码但缩进小于基准，通常表示新块开始，结束当前块
                    break

            # 更新当前行括号深度
            for ch in cur_line:
                if ch in '({[':
                    depth += 1
                elif ch in ')}]':
                    depth -= 1

            j += 1
            if depth < 0:
                break

        # 构建块：保留所有缩进，仅去除首尾换行符
        block = '\n'.join(lines[start:j]).strip('\n')
        if block:
            result_blocks.append(block)
        i = j

    return '\n\n'.join(result_blocks)

def is_code_line(line: str) -> bool:
    """判断一行是否属于 Python 代码（而非自然语言）"""
    stripped = line.strip()
    if not stripped:
        return False

    # 1. 多行字符串标记 (""" 或 ''')
    if stripped.startswith('"""') or stripped.startswith("'''"):
        # 如果除了引号还有代码特征，则视为代码行
        if any(kw in stripped for kw in ['def ', 'class ', 'if ', 'for ', 'while ', 'return ', 'import ', 'from ', '=']):
            return True
        return False  # 否则当作普通文本

    # 2. 明确的关键字开头（def, class, if, for...）
    code_keywords = ('def ', 'class ', 'import ', 'from ', '@',
                     'if ', 'elif ', 'else:', 'for ', 'while ',
                     'try:', 'except ', 'finally:', 'with ',
                     'return ', 'yield ', 'raise ', 'lambda:',
                     'self.', 'cls.', 'super(', 'print(',
                     'assert ', 'pass', 'break', 'continue')
    if stripped.startswith(code_keywords):
        return True

    # 3. 缩进（至少2个空格或一个Tab）—— 通常为代码
    if line.startswith(('  ', '\t')):
        return True

    # 4. 赋值或类型注解（如 x: int = 5）
    if re.match(r'^[a-zA-Z_]\w*\s*[:=]', stripped):
        # 检查等号右侧是否包含中文且无括号/lambda等代码特征
        if any('\u4e00' <= ch <= '\u9fff' for ch in stripped):
            # 包含中文，且没有括号和 lambda -> 大概率是自然语言描述
            if '(' not in stripped and ')' not in stripped and 'lambda' not in stripped:
                return False
        return True

    # 5. 函数调用（如 func( ... )）
    if re.match(r'^[a-zA-Z_]\w*\s*\(', stripped):
        return True

    # 6. 包含特殊代码标记
    if 'lambda' in stripped or 'self.' in stripped or 'cls.' in stripped:
        return True

    # 7. 含有中文且无上述代码特征 -> 视为自然语言
    if any('\u4e00' <= ch <= '\u9fff' for ch in stripped):
        return False

    # 8. 默认视为非代码（保底）
    return False

def extract_pure_text(text: str) -> str:
    """保留所有非代码行（自然语言），剔除代码行"""
    lines = text.splitlines()
    pure_lines = []
    for line in lines:
        if not is_code_line(line):
            pure_lines.append(line)
    # 合并并清理多余空行
    result = '\n'.join(pure_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)  # 最多保留两个换行

    # 后处理：去除可能残留的赋值前缀（如 question = """）
    # 更鲁棒：去掉行首的变量赋值和引号，只保留自然语言内容
    # 简单示例：如果第一行包含 '"""'，裁剪掉前面的部分
    lines2 = result.splitlines()
    if lines2:
        first = lines2[0].strip()
        # 如果第一行包含 """ 或 '''，尝试只保留引号后面的内容
        if '"""' in first or "'''" in first:
            # 找到第一个引号后的内容
            match = re.search(r'["\']{3}\s*(.*?)\s*$', first)
            if match:
                lines2[0] = match.group(1).strip()
            else:
                # 如果没匹配，去除引号本身
                lines2[0] = re.sub(r'["\']{3}', '', first).strip()
        # 去掉末尾可能残留的引号行
        if lines2 and lines2[-1].strip() in ('"""', "'''"):
            lines2.pop()
        result = '\n'.join(lines2).strip()

    return result

# ================= 测试示例 =================
if __name__ == '__main__':
    test_input = question_normal_short

    print("=" * 60)
    print("【原始输入】")
    print(test_input)
    print("=" * 60)

    # 1. 提取纯文字（给大模型当指令）
    pure_text = extract_pure_text(test_input)
    print("\n【剥离代码后的纯文字指令】(适合作为 User Prompt 的背景)")
    print(pure_text)
    print("=" * 60)

    # 2. 提取纯代码
    code_only = extract_heuristic(test_input)
    print("\n【提取出的干净代码】(适合作为待处理的数据)")
    print(code_only)
    print("=" * 60)
