from bot.session_manager import Session
from common.log import logger


class ZhipuAgentSession(Session):
    def __init__(self, session_id, system_prompt=None, **kwargs):
        super().__init__(session_id, system_prompt)
        self.conversation_id = None  # 添加conversation_id属性
        logger.info(f"[ZHIPU_AGENT] Created session with id: {session_id}")

    def clear_session(self):
        super().clear_session()
        self.conversation_id = None  # 清除conversation_id

    def calc_tokens(self) -> int:
        """简单计算token数，每个汉字算2个token，每个英文单词算1个token"""
        total = 0
        for message in self.messages:
            content = message.get("content", "")
            # 简单计算，实际应该使用专门的分词器
            total += len(content) * 2  # 按最大值计算
        logger.info(f"[ZHIPU_AGENT] Calculated tokens: {total}")
        return total
