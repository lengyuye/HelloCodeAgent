import math
import re
from typing import Iterator

from hello_agents import HelloAgentsLLM, ToolRegistry, HelloAgentsException

from src.Configs.config import AGENT_ANSWER_FLAG, TOOL_EXEC_ERROR
from src.agents.interfaces import IManager
from src.agents.prompts import code_reviewer_prompt, code_reviewer_again_prompt


class CodeReviewAgent:
    def __init__(self, llm_client: HelloAgentsLLM, registry: ToolRegistry,max_steps: int = 5):
        self.llm_client = llm_client
        self.registry = registry
        self.max_steps = max_steps
        self.history = []
        #缓存搜索结果
        self.cache_search_result = ""

    def run_react(self, question: str, code_only: str,manager: IManager)->str:
        """运行代码审查Agent_ReAct模式"""
        print("\n--- 开始代码审查 ---")
        self.history = []
        current_step = 0

        #先获取记忆和知识库信息
        self.cache_search_result = manager.get_memory_and_knowledge(question, code_only)
        print(f"merge_result:{self.cache_search_result}")
        # 将处理后的记忆、RAG结果加入历史信息
        self.history.append(f"Other Info:{self.cache_search_result}")

        while current_step < self.max_steps:
            current_step += 1
            print(f"\n--- 第 {current_step} 步 ---")

            history_str = "\n".join(self.history)
            prompt = code_reviewer_prompt.format(question=question, code_only=code_only,history= history_str)

            messages = [{"role": "user", "content": prompt}]
            response_text, err = self._safe_think(messages)
            if err:
                print(f"LLM 调用异常：{err}")
                self.history.append(f"Observation:LLM调用异常:{err}")
                # 视为一次失败的步骤，终止循环
                return "Error: LLM调用失败，请稍后重试。"
            if not response_text:
                print("错误：LLM未能返回有效响应。")
                break

            thought, action = self._parse_output(response_text)
            if thought: print(f"🤔 思考: {thought}")
            if not action: print("警告：未能解析出有效的Action，流程终止。"); break

            if action.startswith(AGENT_ANSWER_FLAG):
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
                if tool_response.startswith(TOOL_EXEC_ERROR):
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

    def _safe_think(self, messages):
        try:
            response = self.llm_client.think(messages=messages)
            if isinstance(response, str):
                return response, None
            response_text = ''.join(response)
            return response_text, None
        except HelloAgentsException as e:
            return "", str(e)

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

    def run_no_react(self, question: str, code_only: str,last_suggestion: str,feedback: str)->str:
        """运行代码审查Agent_NoReact模式
            只运行一轮，用于修改建议
        """
        prompt = code_reviewer_again_prompt.format(question=question, code_only=code_only,last_suggestion = last_suggestion,feedback = feedback)
        messages = [{"role": "user", "content": prompt}]
        response = self.llm_client.think(messages=messages)
        response_text = self._get_text(response)

        if not response_text:
            error_tip = "错误：LLM未能返回有效响应。"
            print(error_tip)
            return error_tip

        if response_text.startswith(AGENT_ANSWER_FLAG):
            # 如果是Finish指令，提取最终答案并结束
            final_answer = self._parse_action_input(response_text)
            print(f"🎉 答案: {final_answer}")
            return final_answer

        print(f"Agent 没有返回Finish块，将输出原始内容")
        return response_text

    @staticmethod
    def  _get_text(response: Iterator[str])->str:
        return  ''.join(response) if (hasattr(response, '__iter__') and
                                      not isinstance(response,str)) else response

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


