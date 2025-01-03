""""
智谱AI工具类
"""
import logging
import uuid
from typing import Tuple
from pathlib import Path
import json
import requests
from zhipuai import ZhipuAI

import config
from common.singleton import singleton


class SearchResultItem(dict):
    """查询结构项"""

    def __init__(self, content: str = None, icon: str = None, index: int = None, link: str = None, media: str = None,
                 refer: str = None, title: str = None, **kwargs):
        super().__init__()
        self["content"] = content
        self["icon"] = icon
        self["index"] = index
        self["link"] = link
        self["media"] = media
        self["refer"] = refer
        self["title"] = title
        if kwargs:
            self.update(kwargs)


@singleton
class ZhipuTools:
    @classmethod
    def web_search(cls, content) -> Tuple[SearchResultItem, ...]:
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
        api_key = conf.get("zhipu_ai_api_key", config.zhipu_config.get("zhipu_ai_api_key"))
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
        # 检查是否response成功
        status_code = resp.status_code
        if status_code != 200:
            logging.error(f"zhipuai response error: status:{status_code},  response: {resp.text}")
            raise Exception(f"zhipuai response error: status:{status_code},  response: {resp.text}")
        search_result_list = tuple(tool_call["search_result"] for tool_call in
                                   resp.json()["choices"][0]["message"]["tool_calls"] if tool_call.get("search_result"))
        if search_result_list:
            return tuple(SearchResultItem(**result) for result in search_result_list[0])


    @classmethod
    def file_extract(cls, file_path) -> str:
        """
        从智谱AI的响应中获取答案
        Args:
            file_path: 文件路径
        Returns: 查询结果
        """
        conf = config.conf()
        api_key = conf.get("zhipu_ai_api_key", config.zhipu_config.get("zhipu_ai_api_key"))
        client = ZhipuAI(api_key=api_key)
        # 格式限制：.PDF .DOCX .DOC .XLS .XLSX .PPT .PPTX .PNG .JPG .JPEG .CSV .PY .TXT .MD .BMP .GIF
        # 大小：单个文件50M、总数限制为100个文件
        file_object = client.files.create(file=Path(file_path), purpose="file-extract")
        # 获取文本内容
        file_content = json.loads(client.files.content(file_id=file_object.id).content)["content"]
        return file_content


zhipu_tools = ZhipuTools()