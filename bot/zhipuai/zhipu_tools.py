""""
智谱AI工具类
"""
import uuid

import requests

import config
from common.singleton import singleton


class SearchResultItem(dict):
    """查询结构项"""

    def __init__(self, content: str, icon: str, index: int, link: str, media: str, refer: str, title: str):
        super().__init__()
        self["content"] = content
        self["icon"] = icon
        self["index"] = index
        self["link"] = link
        self["media"] = media
        self["refer"] = refer
        self["title"] = title

    def __repr__(self):
        return self.__dict__


class SearchResult(dict):
    """查询结果"""

    def __init__(self, id: str, search_result: list):
        super().__init__()
        self['id'] = id
        self['search_result'] = [SearchResultItem(**item) for item in search_result]

    def __repr__(self):
        return self.__dict__


@singleton
class ZhipuTools:
    @staticmethod
    def web_search(content) -> SearchResultItem:
        """
        从智谱AI的响应中获取答案
        Args:
            content: 智谱AI响应

        Returns: 查询结果
        """
        msg = [
            {
                "role": "user",
                "content": content
            }
        ]
        conf = config.conf()
        api_key = conf.get("zhipu_ai_api_key")
        url = conf.get("zhipu_ai_api_tools", config.zhipu_config.get("zhipu_ai_api_tools"))
        tool = conf.get("zhipu_ai_tools_web_search", config.zhipu_config.get("zhipu_ai_tools_web_search"))
        request_id = str(uuid.uuid4())
        data = {
            "request_id": request_id,
            "tool": tool,
            "stream": False,
            "messages": msg
        }
        resp = requests.post(
            url,
            json=data,
            headers={'Authorization': api_key},
            timeout=300
        )
        print(resp.content.decode())

if __name__ == '__main__':
    ZhipuTools().web_search("中国队奥运会拿了多少奖牌")