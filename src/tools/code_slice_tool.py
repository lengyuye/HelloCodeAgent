from hello_agents import ToolRegistry

from src.utils.tree_sitter_util import TreeSitterUtil

"""
代码切片工具 （目前只支持了python,可扩展）
内部调用 tree-sitter
"""

def my_code_slice(source_code:str)->str:
    sitterUtil = TreeSitterUtil()
    result = sitterUtil.get_syntax_chunks(source_code)
    if result["has_syntax_error"]:
        warn_text = "\n> 警告：代码存在语法错误，审查仅供参考\n"
        print(warn_text)
    slice_content = ""
    for idx, chunk in enumerate(result["chunks"]):
        print(f"\n====切片 {idx + 1} byte[{chunk['start_byte']}‑{chunk['end_byte']}]====")
        slice_content +=chunk["text"]
    return slice_content

def create_code_slice_registry() ->ToolRegistry:
    """创建包含代码切片的工具注册表"""
    registry = ToolRegistry()

    # 注册切片函数
    registry.register_function(
        name="my_code_slicer",
        description="用于代码切片的工具",
        func=my_code_slice
    )

    return registry