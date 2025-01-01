import json
import time
import requests
from bot.bot import Bot
from bot.zhipuagent.zhipu_agent_session import ZhipuAgentSession
from bot.session_manager import SessionManager
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from config import conf


class ReplyItem:
    def __init__(self, reply, usage=None, is_end=False):
        self.is_end = is_end
        self.reply = reply
        self.usage = usage


class ZhipuAgentBot(Bot):
    def __init__(self):
        super().__init__()
        self.sessions = SessionManager(ZhipuAgentSession)
        self.api_key = conf().get("zhipu_ai_api_key")
        self.app_id = conf().get("zhipu_agent_app_id")
        self.base_url = "https://open.bigmodel.cn/api/llm-application/open"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def reply(self, query, context=None):
        if context.type == ContextType.TEXT:
            logger.info("[ZHIPU_AGENT] query={}".format(query))
            session_id = context["session_id"]

            # 处理清除记忆等指令
            reply = self._handle_commands(query, session_id)
            if reply:
                return reply

            session = self.sessions.session_query(query, session_id)
            reply_content = self.reply_text(session)

            content = reply_content.get("content", "")

            # 检查是否是智谱AI的视频响应
            try:
                if content.startswith('[') and 'cogvideo' in content:
                    data = json.loads(content)
                    if data[0] == "SUCCESS" and len(data[1]) > 0:
                        video_info = data[1][0]
                        video_url = video_info.get("url")
                        if video_url and video_url.endswith('.mp4'):
                            logger.info(f"[ZHIPU_AGENT] Found video url: {video_url}")
                            return Reply(ReplyType.VIDEO_URL, video_url)
            except (json.JSONDecodeError, IndexError, KeyError) as e:
                logger.warning(f"[ZHIPU_AGENT] Failed to parse video response: {e}")

            # 检查是否是智谱AI的图片链接
            if content.startswith('https://aigc-files.bigmodel.cn') and content.endswith('.png'):
                logger.info(f"[ZHIPU_AGENT] Found image url: {content}")
                return Reply(ReplyType.IMAGE_URL, content)

            # 处理普通文本回复
            if reply_content.get("completion_tokens", 0) == 0 and len(content) > 0:
                reply = Reply(ReplyType.ERROR, content)
            elif reply_content.get("completion_tokens", 0) > 0:
                self.sessions.session_reply(content, session_id, reply_content.get("total_tokens", 0))
                reply = Reply(ReplyType.TEXT, content)
            else:
                reply = Reply(ReplyType.ERROR, content or "未知错误")
                logger.debug("[ZHIPU_AGENT] reply {} used 0 tokens.".format(reply_content))
            return reply
        else:
            return Reply(ReplyType.ERROR, "Bot不支持处理{}类型的消息".format(context.type))

    def reply_text(self, session, retry_count=0):
        try:
            logger.info("[ZHIPU_AGENT] Starting reply_text")

            # 检查session是否已有conversation_id，没有则创建新的
            if not session.conversation_id:
                conversation_id = self._create_conversation()
                logger.info(f"[ZHIPU_AGENT] Created new conversation: {conversation_id}")
                if not conversation_id:
                    return {"completion_tokens": 0, "content": "创建会话失败"}
                session.conversation_id = conversation_id

            # 使用已存在的conversation_id
            request_id = self._create_request(session.conversation_id, session.messages[-1]["content"])
            logger.info(f"[ZHIPU_AGENT] Created request: {request_id}")
            if not request_id:
                return {"completion_tokens": 0, "content": "创建请求失败"}

            logger.info("[ZHIPU_AGENT] Getting SSE response")
            reply_item = self._get_sse_response(request_id)
            logger.info(f"[ZHIPU_AGENT] Got response: {reply_item.reply[:100]}...")

            usage = reply_item.usage or {}
            return {
                "completion_tokens": usage.get("completion_tokens", 1),
                "total_tokens": usage.get("total_tokens", 0),
                "content": reply_item.reply
            }

        except Exception as e:
            logger.exception(f"[ZHIPU_AGENT] Exception in reply_text: {e}")
            need_retry = retry_count < 2

            if need_retry:
                logger.info(f"[ZHIPU_AGENT] Retrying {retry_count + 1}/2")
                time.sleep(5)
                return self.reply_text(session, retry_count + 1)
            else:
                return {"completion_tokens": 0, "content": "我现在有点累了，等会再来吧"}

    def _create_conversation(self):
        url = f"{self.base_url}/v2/application/{self.app_id}/conversation"
        try:
            logger.info(f"[ZHIPU_AGENT] Creating conversation with URL: {url}")
            response = requests.post(url, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            logger.info(f"[ZHIPU_AGENT] Conversation response: {result}")
            return result.get("data", {}).get("conversation_id")
        except Exception as e:
            logger.error(f"[ZHIPU_AGENT] Create conversation failed: {e}")
            return None

    def _create_request(self, conversation_id, prompt):
        url = f"{self.base_url}/v2/application/generate_request_id"
        data = {
            "app_id": self.app_id,
            "conversation_id": conversation_id,
            "key_value_pairs": [{
                "id": "user",
                "type": "input",
                "name": "用户提问",
                "value": prompt
            }]
        }
        try:
            logger.info(f"[ZHIPU_AGENT] Creating request with URL: {url}")
            logger.info(f"[ZHIPU_AGENT] Request data: {data}")
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            result = response.json()
            logger.info(f"[ZHIPU_AGENT] Request response: {result}")
            return result.get("data", {}).get("id")
        except Exception as e:
            logger.error(f"[ZHIPU_AGENT] Create request failed: {e}")
            return None

    def _get_sse_response(self, request_id):
        url = f"{self.base_url}/v2/model-api/{request_id}/sse-invoke"
        headers = {**self.headers, "Accept": "text/event-stream"}
        content = []
        usage = None
        has_response = False

        try:
            logger.info(f"[ZHIPU_AGENT] Getting SSE response from URL: {url}")
            response = requests.post(url, headers=headers, stream=True, timeout=180)
            response.raise_for_status()

            current_data = {}
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue

                if line.startswith(("event:", "id:", "data:")):
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()

                    if key == "data":
                        try:
                            data = json.loads(value)
                            if "extra_input" in data:
                                block_data = data["extra_input"].get("block_data", {})
                                if block_data.get("block_type") == "output" and \
                                        block_data.get("block_status") == "finished":
                                    out_content = block_data.get("out_put", {}).get("out_content")
                                    if out_content:
                                        has_response = True
                                        if not out_content.rstrip().endswith(('\n', '\r')):
                                            out_content = out_content.rstrip()
                                        logger.info(f"[ZHIPU_AGENT] Got output content: {out_content}")
                                        return ReplyItem(out_content, usage=usage, is_end=True)
                            elif "msg" in data and data["msg"]:
                                has_response = True
                                content.append(data["msg"])
                            elif "usage" in data and not data.get("msg"):
                                usage = data["usage"]
                        except json.JSONDecodeError as e:
                            logger.warn(f"[ZHIPU_AGENT] Failed to decode JSON: {e}")
                            continue

            final_content = "".join(content)
            if not has_response or not final_content:
                logger.error("[ZHIPU_AGENT] No valid response received")
                return ReplyItem("对不起，我没有收到有效的回复", is_end=True)

            logger.info(f"[ZHIPU_AGENT] Final response content: {final_content[:100]}...")
            return ReplyItem(final_content, usage=usage, is_end=True)

        except Exception as e:
            logger.error(f"[ZHIPU_AGENT] Get SSE response failed: {e}")
            return ReplyItem("对不起，发生了未知错误", is_end=True)

    def _handle_commands(self, query, session_id):
        clear_memory_commands = conf().get("clear_memory_commands", ["#清除记忆"])
        if query in clear_memory_commands:
            self.sessions.clear_session(session_id)
            return Reply(ReplyType.INFO, "记忆已清除")
        elif query == "#清除所有":
            self.sessions.clear_all_session()
            return Reply(ReplyType.INFO, "所有人记忆已清除")
        return None