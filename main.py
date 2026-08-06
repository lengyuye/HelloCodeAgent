# This is a sample Python script.
from hello_agents import HelloAgentsLLM

from src.agents.agent_factory import AgentFactory
from src.agents.multi_agent_manager import MultiAgentManager
import src.utils.test_case as tc
from src.tools.code_slice_tool import create_code_slice_registry
from src.utils.knowledge_util import KnowledgeUtil
from src.utils.memory_util import MemoryUtil


def run_with_dependency_injection(user_id:str):
    """使用依赖注入的方式运行"""
    # 创建依赖组件
    llm = HelloAgentsLLM()
    tool_registry = create_code_slice_registry()
    memory_util = MemoryUtil(user_id=user_id)
    knowledge_util = KnowledgeUtil()

    # 使用工厂创建 Agent
    code_review_agent = AgentFactory.create_code_review_agent(llm, tool_registry)
    reflection_agent = AgentFactory.create_reflection_agent(llm, tool_registry)

    # 注入依赖
    manager = MultiAgentManager(
        user_id=user_id,
        llm_client=llm,
        code_review_agent=code_review_agent,
        reflection_agent=reflection_agent,
        memory_util=memory_util,
        knowledge_util=knowledge_util,
        tool_registry=tool_registry
    )

    manager.run(tc.question_normal)


def run_simple(user_id:str):
    """简单方式运行（自动创建依赖）"""
    manager = MultiAgentManager(user_id=user_id)
    manager.run(tc.question_normal)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # 选择运行方式
    run_simple("user123")  # 或 run_with_dependency_injection("user123")

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
