from hello_agents.tools import RAGTool

from src.Configs.config import PRELOAD_KNOWLEDGE_PATH

# 管理知识库工具，内部使用RAG
class KnowledgeUtil:
    def __init__(self):
        # 初始化RAG工具
        self.rag_tool = RAGTool(knowledge_base_path="./knowledge_base")

    def preload_knowledge_info(self):
        """预加载知识 信息"""
        txt_path = PRELOAD_KNOWLEDGE_PATH
        result1 = self.rag_tool.run({
            "action": "add_document",
            "file_path": txt_path,
            "document_id": "code_standard"})
        print(f"预加载知识: {result1}")

    def get_knowledge_search_result(self,content:str):
        """获取知识搜索结果"""
        result = self.rag_tool.run({
            "action":"search",
            "query":content
        })
        print(f"search knowledge :\n{result}")
        return result