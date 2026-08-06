from abc import ABC, abstractmethod


class IManager(ABC):
    """Manager 接口，定义 CodeReviewAgent 需要的方法"""

    @abstractmethod
    def get_memory_and_knowledge(self, question: str, tool_response: str) -> str:
        """获取记忆和知识库"""
        return ""