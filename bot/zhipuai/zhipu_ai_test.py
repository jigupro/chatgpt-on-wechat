import unittest

from bot.zhipuai.zhipu_tools import zhipu_tools
import pytest

from config import load_config


def test_web_search():
    load_config()
    # 1. Test the web_search method of the ZhipuTools class
    print(zhipu_tools.web_search("中国队奥运会拿了多少奖牌"))

