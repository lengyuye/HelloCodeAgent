from hello_agents.tools import MemoryTool


class MemoryUtil:
    def __init__(self,user_id):
        # 添加记忆工具 这里暂时只启用两种记忆
        self.memory_tool = MemoryTool(user_id=user_id, memory_types=["working", "episodic"])

    def _auto_record_conversation(self, user_input: str, agent_response: str):
        """自动记录对话
        memory_tool中的auto_record_conversation 方法有问题，这个改下在外面用
        这个方法可以被Agent调用来自动记录对话历史
        """

        # 记录用户输入
        self.memory_tool.run({
            "action": "add",
            "content": f"用户: {user_input}",
            "memory_type": "working",
            "importance": 0.6,
        })

        # 记录Agent响应
        self.memory_tool.run({
            "action": "add",
            "content": f"助手: {agent_response}",
            "memory_type": "working",
            "importance": 0.7,
        })

        # 如果是重要对话，记录为情景记忆
        if len(agent_response) > 100 or "重要" in user_input or "记住" in user_input:
            interaction_content = f"对话 - 用户: {user_input}\n助手: {agent_response}"
            self.memory_tool.run({
                "action": "add",
                "content": interaction_content,
                "memory_type": "episodic",
                "importance": 0.8,
            })

    def add_memory(self,user_input,response):
        """将对话存入记忆"""
        self._auto_record_conversation(user_input, response)

    def search_working_memory(self,param:str):
        """
        工作记忆作为的上下文历史，每次默认获取
        """

        result_working = self.memory_tool.run({
            "action": "search",
            "query": param,
            "memory_type": "working",
            "limit": 2
        })
        print(f"\n搜索 - 工作记忆中的'记忆':{result_working}")
        if result_working.startswith("🔍 未找到"):
            return ""
        else:
            return result_working

    def search_episodic_memory(self,param:str):
        """
        有需要时搜索情景记忆
        :param param:
        :return:
        """
        result_episodic = self.memory_tool.run({
            "action": "search",
            "query": param,
            "memory_type": "episodic",
            "limit": 2
        })
        print(f"\n搜索 - 情景记忆中的'记忆':{result_episodic}")
        if result_episodic.startswith("🔍 未找到"):
            return ""
        else:
            return result_episodic

    def forget_memory(self):
        # 基于容量的遗忘 - 当记忆数量超限时删除最不重要的
        self.memory_tool.run({
            "action":"forget",
              "strategy":"capacity_based",
               "threshold":0.3
        })

    @staticmethod
    def is_need_search_episodic_memory(user_input):
        """
        是否搜索情景记忆
        用关键词判断是否需要记忆搜索
        """
        keywords = ["之前", "上次", "还记得吗"]
        if any(keyword in user_input for keyword in keywords):
            return True
        return False