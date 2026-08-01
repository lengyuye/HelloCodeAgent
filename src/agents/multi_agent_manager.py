import re

from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM, SimpleAgent

from src.agents.code_review_agent import CodeReviewAgent
from src.agents.prompts import code_checkout_prompt
from src.tools.code_slice_tool import create_code_slice_registry
from src.utils.extract_code_util import extract_pure_text, extract_heuristic


class MultiAgentManager:
    def __init__(self):
        """初始化多智能体系统"""

        load_dotenv()#加载环境变量

        print("🔄 开始初始化多智能体系统...")
        try:
            self.llm = HelloAgentsLLM()
            self.tool_registry = create_code_slice_registry()  # 注册代码切片工具
            self.code_review_agent = CodeReviewAgent(llm_client=self.llm, registry=self.tool_registry )
            self.reflection_agent = SimpleAgent(
                name="python代码审查专家",
                llm=self.llm,
                system_prompt=code_checkout_prompt
            )
            self.max_reflection_rounds = 3
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
        review_response = self.code_review_agent.run_react(pure_text, code_only)

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
            review_response = self.code_review_agent.run_no_react(pure_text, code_only,review_response,reflection_response)
        print(f"最终答案{review_response}")

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
