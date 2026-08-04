from datetime import datetime
import re

from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM, SimpleAgent
from hello_agents.tools import MemoryTool,RAGTool


from src.agents.code_review_agent import CodeReviewAgent
from src.agents.interfaces import IManager
from src.agents.prompts import code_checkout_prompt
from src.tools.code_slice_tool import create_code_slice_registry
from src.utils.extract_code_util import extract_pure_text, extract_heuristic


class MultiAgentManager(IManager):
    def __init__(self):
        """初始化多智能体系统"""

        load_dotenv()#加载环境变量

        print("🔄 开始初始化多智能体系统...")
        try:
            self.llm = HelloAgentsLLM()
            self.tool_registry = create_code_slice_registry()  # 注册代码切片工具

            # 添加记忆工具
            self.memory_tool = MemoryTool(user_id="user123")

            # 添加RAG工具
            self.rag_tool = RAGTool( knowledge_base_path="./knowledge_base")

            self.code_review_agent = CodeReviewAgent(llm_client=self.llm, registry=self.tool_registry )
            self.reflection_agent = SimpleAgent(
                name="python代码审查专家",
                llm=self.llm,
                system_prompt=code_checkout_prompt
            )
            # 为Agent配置工具
            self.reflection_agent.tool_registry = self.tool_registry
            # 反思最大轮数
            self.max_reflection_rounds = 3

            #预加载知识
            self._preload_knowledge_info()
        except Exception as e:
            print(f"❌ 多智能体系统初始化失败: {str(e)}")
            raise

    def run(self,question):
        # 1.先对 用户输入做预处理，拆分文本和代码
        # 提取纯文字（给大模型当指令）
        pure_text = extract_pure_text(question)
        # print(f"提取出的文本:\n{pure_text}")
        # 提取代码
        code_only = extract_heuristic(question)
        # print(f"提取出的代码:\n{code_only}")

        # 2.调用代码审查Agent
        review_response = self.code_review_agent.run_react(pure_text, code_only,self)

        # 直到反思结束，整个流程结束；否则继续调用代码审查Agent持续修改
        is_reflection_over = False
        reflection_round = 0
        while not is_reflection_over or reflection_round < self.max_reflection_rounds:
            # 3.调用反思Agent
            reflection_round +=1
            reflection_input = self._get_reflection_input(question, review_response)
            print(f"检查优化建议 第{reflection_round}轮")
            reflection_response = self.reflection_agent.run(reflection_input)
            is_reflection_over = self._check_is_reflection_over(reflection_response)
            if is_reflection_over:
                print(f"反思结束")
                break
            if reflection_round >= self.max_reflection_rounds:
                print("反思结束：达到最大步数")
                break

            #4. 调用代码审查Agent 持续修改建议
            print("审查Agent 根据建议进行修改，：")
            review_response = self.code_review_agent.run_no_react(pure_text, code_only,review_response,reflection_response)


        #5 先遗忘记忆，避免记忆量过大
        self._forget_memory()

        #6. 存入记忆
        self.add_memory(question,review_response)

        print(f"🎉 最终答案:{review_response}")

    def _preload_knowledge_info(self):
        """预加载知识 信息"""
        txt_path = "./data/code_standard.txt"
        result1 = self.rag_tool.run({
            "action":"add_document",
            "file_path" : txt_path,
            "document_id":"code_standard" })
        print(f"预加载知识: {result1}")

    def get_knowledge_search_result(self,content:str):
        """获取知识搜索结果"""
        result = self.rag_tool.run({
            "action":"search",
            "query":content
        })
        print(f"search knowledge :\n{result}")
        return result

    def is_need_search_episodic_memory(self,user_input):
        """
        是否搜索情景记忆
        用关键词判断是否需要记忆搜索
        """
        if ("之前" or "上次" or "还记得吗") in user_input:
            return True
        return  False

    def add_memory(self,user_input,response):
        """将对话存入记忆"""
        self._auto_record_conversation(user_input, response)

    def _auto_record_conversation(self, user_input: str, agent_response: str):
        """自动记录对话
        memory_tool中的auto_record_conversation 方法有问题，这个改下在外面用
        这个方法可以被Agent调用来自动记录对话历史
        """
        time_id_str = datetime.now().strftime("%Y%m%d%H%M%S")
        # 记录用户输入
        self.memory_tool.run({
            "action": "add",
            "content":f"用户: {user_input}",
            "memory_type":"working",
            "importance":0.6,
        })

        # 记录Agent响应
        self.memory_tool.run({
            "action": "add",
            "content":f"助手: {agent_response}",
            "memory_type":"working",
            "importance":0.7,
        })

        # 如果是重要对话，记录为情景记忆
        if len(agent_response) > 100 or "重要" in user_input or "记住" in user_input:
            interaction_content = f"对话 - 用户: {user_input}\n助手: {agent_response}"
            self.memory_tool.run({
                "action": "add",
                "content":interaction_content,
                "memory_type":"episodic",
                "importance":0.8,
            })

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

    def _forget_memory(self):
        # 基于容量的遗忘 - 当记忆数量超限时删除最不重要的
        self.memory_tool.run({
            "action":"forget",
              "strategy":"capacity_based",
               "threshold":0.3
        })

    def _get_reflection_input(self,question,review_response):
        """获取反思Agent的输入内容"""
        return f"Question:{question},Suggestion:{review_response}"

    def _check_is_reflection_over(self,reflection_response):
        """检测是否反思结束了"""
        answer = self._get_agent_answer(reflection_response)
        return answer.startswith("没有问题")

    def _get_agent_answer(self, response):
        if response.startswith("Finish"):
            # 如果是Finish指令，提取最终答案并结束
            final_answer = self._parse_response(response)
            print(f"🎉 答案: {final_answer}")
            return final_answer
        print("Agent的回复中没有找到Finish块,将返回原始内容")
        return response

    def _parse_response(self, action_text: str):
        match = re.match(r"\w+\[(.*)\]", action_text, re.DOTALL)
        return match.group(1) if match else ""
