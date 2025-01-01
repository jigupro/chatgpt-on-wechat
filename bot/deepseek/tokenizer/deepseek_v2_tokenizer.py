# pip3 install transformers
# python3 deepseek_v2_tokenizer.py
import os

import transformers

chat_tokenizer_dir = os.path.dirname(__file__)

tokenizer = transformers.AutoTokenizer.from_pretrained(
    chat_tokenizer_dir, trust_remote_code=True
)


def deepseek_num_tokens(message):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tokenizer.encode(message)
        return len(encoding)
    except Exception as e:
        return len(message)