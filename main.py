# This is a sample Python script.
from src.agents.multi_agent_manager import MultiAgentManager
from src.utils.test_case import question_no_need_slice, question_normal, question_normal_short


def run():
   multi_agent_manager = MultiAgentManager()
   multi_agent_manager.run(question_normal)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    run()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
