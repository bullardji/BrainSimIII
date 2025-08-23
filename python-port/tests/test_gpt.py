import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from gpt import GPTClient
import tiktoken


def test_local_generation():
    def local_model(prompt: str, max_tokens: int) -> str:
        # simple echo model used for testing the delegation hook
        return ("local:" + prompt)[:max_tokens]

    client = GPTClient(local_model=local_model)
    out = client.generate("Hello", max_tokens=20)
    assert out.startswith("local:Hello")


def test_token_accounting_and_pluralisation():
    def local_model(prompt: str, max_tokens: int) -> str:
        return "cats"

    client = GPTClient(local_model=local_model)
    client.generate("dog", max_tokens=5)
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
    assert client.prompt_tokens == len(enc.encode("dog"))
    assert client.completion_tokens == len(enc.encode("cats"))
    assert client.total_tokens == client.prompt_tokens + client.completion_tokens

    assert client.pluralize("bus") == "buses"
    assert client.pluralize("bus", count=1) == "bus"
    assert client.singularize("geese") == "goose"
