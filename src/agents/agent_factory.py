from hello_agents import HelloAgentsLLM, SimpleAgent
from hello_agents import ToolRegistry
from src.agents.code_review_agent import CodeReviewAgent
from src.agents.prompts import code_checkout_prompt


class AgentFactory:
    """Agent 工厂类，负责创建各种 Agent 实例"""

    @staticmethod
    def create_code_review_agent(
            llm_client: HelloAgentsLLM,
            tool_registry: ToolRegistry,
            max_steps: int = 5
    ) -> CodeReviewAgent:
        """创建代码审查 Agent"""
        return CodeReviewAgent(
            llm_client=llm_client,
            registry=tool_registry,
            max_steps=max_steps
        )

    @staticmethod
    def create_reflection_agent(
            llm_client: HelloAgentsLLM,
            tool_registry: ToolRegistry,
            system_prompt: str = None
    ) -> SimpleAgent:
        """创建反思 Agent"""
        prompt = system_prompt or code_checkout_prompt
        agent = SimpleAgent(
            name="python代码审查专家",
            llm=llm_client,
            system_prompt=prompt
        )
        agent.tool_registry = tool_registry
        return agent