from enum import Enum,unique

@unique
class HooksEvents(Enum):
	"""
	事件 -- 用户输入提交后、进入 LLM 前
	用途：输入验证、注入上下文等
	"""
	USER_PROMPT_SUBMIT = 1
	"""
	事件 --工具执行前
	用途：权限检查、日志记录
	"""
	PRE_TOOL_USE = 2

	"""
	事件 -- 工具执行后
	用途：副作用（自动 git add 等）、输出检查
	"""
	POST_TOOL_USE = 3

	"""
	事件-- 循环即将退出时
	用途：收尾清理、决定是否继续循环
	"""
	STOP = 4


class HooksHelper:
	def __init__(self):
		self.hooks = {
			HooksEvents.USER_PROMPT_SUBMIT: [],
			HooksEvents.PRE_TOOL_USE: [],
			HooksEvents.POST_TOOL_USE: [],
			HooksEvents.STOP: [],
		}

	def register_hook(self, event: HooksEvents, callback):
		self.hooks[event].append(callback)

	def trigger_hooks(self, event: HooksEvents, *args):
		for callback in self.hooks[event]:
			result = callback(*args)
			if result is not None:  # 返回值 ≠ None → hook 说"停"
				return result
		return None
