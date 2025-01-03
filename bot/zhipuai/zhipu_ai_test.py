import unittest

from bot.zhipuai.zhipu_tools import zhipu_tools
import pytest

from config import load_config


@pytest.fixture
def before():
    load_config()

def test_web_search(before):
    # 1. Test the web_search method of the ZhipuTools class
    print(zhipu_tools.web_search("中国队奥运会拿了多少奖牌"))

def test_file_extract(before):
    # 2. Test the file_extract method of the ZhipuTools class
    file = '/Users/mac/Downloads/test.jpg'
    print(zhipu_tools.file_extract(file))

