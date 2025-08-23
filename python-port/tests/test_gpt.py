import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from gpt import GPTClient


def test_local_generation():
    def local_model(prompt: str, max_tokens: int) -> str:
        # simple echo model used for testing the delegation hook
        return ("local:" + prompt)[:max_tokens]

    client = GPTClient(local_model=local_model)
    out = client.generate("Hello", max_tokens=20)
    assert out.startswith("local:Hello")
