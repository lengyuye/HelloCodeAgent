from abc import ABC, abstractmethod


class IManager(ABC):
    """Manager 接口，定义 CodeReviewAgent 需要的方法"""

    @abstractmethod
    def search_working_memory(self, param: str):
        """搜索工作记忆"""
        pass

    @abstractmethod
    def is_need_search_episodic_memory(self, user_input: str) -> bool:
        """判断是否需要搜索情景记忆"""
        pass

    @abstractmethod
    def search_episodic_memory(self, param: str):
        """搜索情景记忆"""
        pass

    @abstractmethod
    def get_knowledge_search_result(self, content: str):
        """获取知识搜索结果"""
        pass