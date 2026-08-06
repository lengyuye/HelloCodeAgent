import re
from typing import Optional
from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM, SimpleAgent
from src.Configs.config import REFLECTION_OVER_FLAG, AGENT_ANSWER_FLAG, MAX_TOKENS, AGENT_ERROR_FLAG
from src.agents.code_review_agent import CodeReviewAgent
from src.agents.interfaces import IManager
from src.agents.prompts import code_checkout_prompt
from src.tools.code_slice_tool import create_code_slice_registry
from src.utils.extract_code_util import extract_pure_text, extract_heuristic
from src.utils.knowledge_util import KnowledgeUtil
from src.utils.memory_util import MemoryUtil
from src.agents.agent_factory import AgentFactory


class MultiAgentManager(IManager):
    def __init__(
            self,
            user_id: str,
            llm_client: Optional[HelloAgentsLLM] = None,
            code_review_agent: Optional[CodeReviewAgent] = None,
            reflection_agent: Optional[SimpleAgent] = None,
            memory_util: Optional[MemoryUtil] = None,
            knowledge_util: Optional[KnowledgeUtil] = None,
            tool_registry=None,
            max_reflection_rounds: int = 3
    ):
        """初始化多智能体系统"""

        load_dotenv()#加载环境变量

        print("🔄 开始初始化多智能体系统...")
        try:
            self.llm = llm_client or HelloAgentsLLM()
            self.tool_registry = tool_registry or create_code_slice_registry()  # 注册代码切片工具

            # 添加记忆工具
            self.memory_util = memory_util or MemoryUtil(user_id=user_id)

            # 添加知识库管理工具
            self.knowledge_util = knowledge_util or KnowledgeUtil()

            # 使用工厂创建 Agent（如果未提供）

            self.code_review_agent = code_review_agent  or AgentFactory.create_code_review_agent(llm_client=self.llm, tool_registry=self.tool_registry)
            self.reflection_agent = reflection_agent or AgentFactory.create_reflection_agent(
                llm_client=self.llm,
                tool_registry = self.tool_registry,
                system_prompt=code_checkout_prompt
            )

            # 反思最大轮数
            self.max_reflection_rounds = max_reflection_rounds

            #预加载知识
            self.knowledge_util.preload_knowledge_info()
        except Exception as e:
            print(f"❌ 多智能体系统初始化失败: {str(e)}")
            raise

    def run(self,question:str):
        # 1.先对 用户输入做预处理，拆分文本和代码
        # 提取纯文字（给大模型当指令）
        pure_text = extract_pure_text(question)
        # print(f"提取出的文本:\n{pure_text}")
        # 提取代码
        code_only = extract_heuristic(question)
        # print(f"提取出的代码:\n{code_only}")

        # 2.调用代码审查Agent
        review_response = self.code_review_agent.run_react(pure_text, code_only,self)

        #3.LLM调用出错的情况
        if review_response.startswith(AGENT_ERROR_FLAG):
            print(review_response)
            return

        # 直到反思结束，整个流程结束；否则继续调用代码审查Agent持续修改
        is_reflection_over = False
        reflection_round = 0
        while not is_reflection_over and reflection_round < self.max_reflection_rounds:
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
        self.memory_util.forget_memory()

        #6. 存入记忆
        self.memory_util.add_memory(question,review_response)

        print(f"🎉 最终答案:{review_response}")

    def get_memory_and_knowledge(self, question: str, tool_response: str) -> str:
        """
        获取记忆信息和 知识库信息
        :param question:
        :param tool_response:
        :return:
        """
        # 搜索记忆
        search_content = f"{question},{tool_response}"
        working_memory = self.memory_util.search_working_memory(search_content)
        episodic_memory = ""
        if self.memory_util.is_need_search_episodic_memory(question):
            episodic_memory = self.memory_util.search_episodic_memory(search_content)
        # 搜索RAG
        rag_result = self.knowledge_util.get_knowledge_search_result(search_content)
        # 合并 记忆和 RAG内容，做Token截断 . 情景记忆>工作记忆
        merge_result = ""
        if episodic_memory:
            merge_result += f"episodic_memory:{episodic_memory}"
        if working_memory:
            merge_result += f"working_memory:{working_memory}"
        if rag_result:
            merge_result += f"rag_result:{rag_result}"
        merge_result = self.process_token_limit(merge_result, 0.3)
        return  merge_result

    @staticmethod
    def process_token_limit(content: str, limit_rate: float) -> str:
        """
        截断字符，避免token过大
        :param content:
        :param limit_rate:
        :return:
        """
        limit_rate = min(1.0, max(0.0, limit_rate))
        limit_token = int(max(0.0, limit_rate * MAX_TOKENS))

        # 计算当前内容的token数
        current_tokens = CodeReviewAgent._count_tokens_by_chars(content)

        # 如果未超过限制，直接返回
        if current_tokens <= limit_token:
            return content

        # 根据字符比例截断（token ≈ 字符数/4）
        max_chars = limit_token * 4
        return content[:int(max_chars)]

    @staticmethod
    def _get_reflection_input(question,review_response):
        """获取反思Agent的输入内容"""
        return f"Question:{question},Suggestion:{review_response}"

    @staticmethod
    def _check_is_reflection_over(reflection_response):
        """检测是否反思结束了"""
        answer = MultiAgentManager._get_agent_answer(reflection_response)
        return answer.startswith(REFLECTION_OVER_FLAG)

    @staticmethod
    def _get_agent_answer(response):
        if response.startswith(AGENT_ANSWER_FLAG):
            # 如果是Finish指令，提取最终答案并结束
            final_answer = MultiAgentManager._parse_response(response)
            print(f"🎉 答案: {final_answer}")
            return final_answer
        print("Agent的回复中没有找到Finish块,将返回原始内容")
        return response

    @staticmethod
    def _parse_response(action_text: str):
        match = re.match(r"\w+\[(.*)\]", action_text, re.DOTALL)
        return match.group(1) if match else ""
