import math
import re

from hello_agents import HelloAgentsLLM, ToolRegistry

from src.agents.interfaces import IManager
from src.agents.prompts import code_reviewer_prompt, code_reviewer_again_prompt


class CodeReviewAgent:
    def __init__(self, llm_client: HelloAgentsLLM, registry:ToolRegistry,max_steps: int = 5):
        self.llm_client = llm_client
        self.registry = registry
        self.max_steps = max_steps
        self.history = []
        self.maxToken = 128000
        #缓存搜索结果
        self.cache_search_result = ""

    def run_react(self, question: str, code_only:str,manager: IManager)->str:
        """运行代码审查Agent_ReAct模式"""
        print("\n--- 开始代码审查 ---")
        self.history = []
        current_step = 0

        #先获取记忆和知识库信息
        if not self.cache_search_result:
            self.get_memory_and_knowledge(manager, question, code_only)
        print(f"merge_result:{self.cache_search_result}")
        # 将处理后的记忆、RAG结果加入历史信息
        self.history.append(f"Other Info:{self.cache_search_result}")

        while current_step < self.max_steps:
            current_step += 1
            print(f"\n--- 第 {current_step} 步 ---")

            history_str = "\n".join(self.history)
            prompt = code_reviewer_prompt.format(question=question, code_only=code_only,history= history_str)

            messages = [{"role": "user", "content": prompt}]
            response = self.llm_client.think(messages=messages)
            response_text = ''.join(response) if hasattr(response, '__iter__') and not isinstance(response,str) else response

            if not response_text:
                print("错误：LLM未能返回有效响应。")
                break

            thought, action = self._parse_output(response_text)
            if thought: print(f"🤔 思考: {thought}")
            if not action: print("警告：未能解析出有效的Action，流程终止。"); break

            if action.startswith("Finish"):
                # 如果是Finish指令，提取最终答案并结束
                final_answer = self._parse_action_input(action)
                print(f"🎉 答案: {final_answer}")
                return final_answer

            tool_name, tool_input = self._parse_action(action)
            if not tool_name or not tool_input:
                self.history.append("Observation: 无效的Action格式，请检查。")
                continue

            print(f"🎬 行动: {tool_name}[{tool_input}]")
            tool_response = ""
            if tool_name == "my_code_slicer":
                tool_response = self.registry.execute_tool(tool_name, tool_input)
                if tool_response.startswith("错误"):
                    observation = f"代码切片结果有错误，错误信息：{tool_response}"
                elif not tool_response:
                    observation = f"代码切片结果有错误，切片结果为空"
                else:
                    observation = f"代码切片成功，结果：{tool_response}"
            else:
                observation = f"错误：未找到名为 '{tool_name}' 的工具。"

            print(f"👀 观察: {observation}")
            self.history.append(f"Action: {action}")
            self.history.append(f"Observation: {observation}")


        print("已达到最大步数，流程终止。")
        return response_text

    def get_memory_and_knowledge(self, manager: IManager, question: str, tool_response: str):
        """
        获取记忆信息和 知识库信息
        :param manager:
        :param question:
        :param tool_response:
        :return:
        """
        # 搜索记忆
        search_content = f"{question},{tool_response}"
        working_memory = manager.search_working_memory(search_content)
        episodic_memory = ""
        if manager.is_need_search_episodic_memory(question):
            episodic_memory = manager.search_episodic_memory(search_content)
        # 搜索RAG
        rag_result = manager.get_knowledge_search_result(search_content)
        # 合并 记忆和 RAG内容，做Token截断 . 情景记忆>工作记忆
        merge_result = ""
        if episodic_memory:
            merge_result += f"episodic_memory:{episodic_memory}"
        if working_memory:
            merge_result +=f"working_memory:{working_memory}"
        if rag_result:
            merge_result +=f"rag_result:{rag_result}"
        merge_result = self.process_token_limit(merge_result, 0.3)
        # 缓存上下文
        self.cache_search_result = merge_result

    def process_token_limit(self,content:str,limit_rate:float) -> str:
        """
        截断字符，避免token过大
        :param content:
        :param limit_rate:
        :return:
        """
        limit_rate = min(1.0, max(0.0, limit_rate))
        limit_token = int(max(0.0,limit_rate*self.maxToken))
        
        # 计算当前内容的token数
        current_tokens = self._count_tokens_by_chars(content)
        
        # 如果未超过限制，直接返回
        if current_tokens <= limit_token:
            return content
        
        # 根据字符比例截断（token ≈ 字符数/4）
        max_chars = limit_token * 4
        return content[:int(max_chars)]

    @staticmethod
    def _count_tokens_by_chars(text: str) -> int:
        """
        通过字符数估算Token（英文专用）
        经验法则：Token数 ≈ 字符数 / 4
        """
        # 去除首尾空格，但保留内部空格
        char_count = len(text)
        # 向上取整，避免出现0
        return  int(max(1.0, math.ceil(char_count / 4)))

    def run_no_react(self, question: str, code_only:str,last_suggestion:str,feedback:str)->str:
        """运行代码审查Agent_NoReact模式
            只运行一轮，用于修改建议
        """
        prompt = code_reviewer_again_prompt.format(question=question, code_only=code_only,last_suggestion = last_suggestion,feedback = feedback)
        messages = [{"role": "user", "content": prompt}]
        response = self.llm_client.think(messages=messages)
        response_text = ''.join(response) if hasattr(response, '__iter__') and not isinstance(response,
                                                                                              str) else response

        if not response_text:
            error_tip = "错误：LLM未能返回有效响应。"
            print(error_tip)
            return error_tip

        if response_text.startswith("Finish"):
            # 如果是Finish指令，提取最终答案并结束
            final_answer = self._parse_action_input(response_text)
            print(f"🎉 答案: {final_answer}")
            return final_answer

        print(f"Agent 没有返回Finish块，将输出原始内容")
        return response_text

    @staticmethod
    def _parse_output(text: str):
        # Thought: 匹配到 Action: 或文本末尾
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        # Action: 匹配到文本末尾
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action

    @staticmethod
    def _parse_action(action_text: str):
        match = re.match(r"(\w+)\[(.*)\]", action_text, re.DOTALL)
        return (match.group(1), match.group(2)) if match else (None, None)

    @staticmethod
    def _parse_action_input(action_text: str):
        match = re.match(r"\w+\[(.*)\]", action_text, re.DOTALL)
        return match.group(1) if match else ""


