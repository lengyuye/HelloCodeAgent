import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Query, QueryCursor

from src.utils.test_case import question_normal

# 初始化解析器 目前仅仅是python
PY_LANG = Language(tspython.language())
parser = Parser(PY_LANG)

# ==========配置参数==========
# 单切片最大token，python大概1token≈4字符，按需调整
MAX_CHUNK_TOKENS = 800
TOKEN_PER_CHAR = 0.25

# Query：捕获顶层：类、函数、导入、注释
# . 表示相邻，捕获紧贴函数/类前面的注释
QUERY_SRC = """
(module
  [
    (comment) @comment
    (import_statement) @import
    (import_from_statement) @import_from
    (class_definition) @class
    (function_definition) @function
  ]
)
"""
query = Query(PY_LANG, QUERY_SRC)


def check_has_error(node):
    """检查语法树是否存在错误节点"""
    if node.type == "ERROR":
        return True
    for child in node.children:
        if check_has_error(child):
            return True
    return False


def get_syntax_chunks(source_code: str):
    """
    基于tree‑sitter语法做代码切片
    返回 list[dict]
    """
    source_bytes = source_code.encode("utf‑8")
    tree = parser.parse(source_bytes)
    root = tree.root_node

    has_error = check_has_error(root)

    # 捕获所有顶层语法节点，按源码出现顺序
    query_cursor = QueryCursor(query)
    captures = query_cursor.captures(root)
    # captures 是一个字典，key是capture名称，value是节点列表
    # 我们需要按顺序提取所有节点
    nodes = []
    for capture_name in captures:
        nodes.extend(captures[capture_name])
    # 按起始位置排序
    nodes.sort(key=lambda n: n.start_byte)

    chunks = []
    current_group = []
    current_token_est = 0

    for node in nodes:
        node_text_bytes = source_bytes[node.start_byte: node.end_byte]
        node_text = node_text_bytes.decode("utf‑8")
        node_token = int(len(node_text) * TOKEN_PER_CHAR)

        # 如果加入本节点就超限，则先输出当前组
        if current_group and (current_token_est + node_token) > MAX_CHUNK_TOKENS:
            first = current_group[0]
            last = current_group[-1]
            chunk_bytes = source_bytes[first.start_byte:last.end_byte]
            chunks.append({
                "text": chunk_bytes.decode("utf‑8"),
                "start_byte": first.start_byte,
                "end_byte": last.end_byte,
                "start_point": (first.start_point.row, first.start_point.column),
                "end_point": (last.end_point.row, last.end_point.column),
                "node_types": [n.type for n in current_group],
            })
            current_group = []
            current_token_est = 0

        current_group.append(node)
        current_token_est += node_token

    # 处理剩余节点
    if current_group:
        first = current_group[0]
        last = current_group[-1]
        chunk_bytes = source_bytes[first.start_byte:last.end_byte]
        chunks.append({
            "text": chunk_bytes.decode("utf‑8"),
            "start_byte": first.start_byte,
            "end_byte": last.end_byte,
            "start_point": (first.start_point.row, first.start_point.column),
            "end_point": (last.end_point.row, last.end_point.column),
            "node_types": [n.type for n in current_group],
        })

    return {
        "chunks": chunks,
        "has_syntax_error": has_error
    }


# ==========测试示例==========
if __name__ == "__main__":
    demo_code = question_normal
    result = get_syntax_chunks(demo_code)
    if result["has_syntax_error"]:
        warn_text = "\n> 警告：代码存在语法错误，审查仅供参考\n"
    print(f"检测语法错误：{result['has_syntax_error']}")
    for idx, chunk in enumerate(result["chunks"]):
        print(f"\n====切片 {idx+1} byte[{chunk['start_byte']}‑{chunk['end_byte']}]====")
        print(chunk["text"])
