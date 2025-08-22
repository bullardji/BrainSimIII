from __future__ import annotations

"""Port of the C# ModuleGPTInfo module.

The original module uses OpenAI's GPT models to verify relationships and to
fetch commonsense information.  The Python port provides similar helpers using
the OpenAI HTTP API.  Calls require the ``OPENAI_API_KEY`` environment variable
and will raise :class:`RuntimeError` if it is missing.
"""

import os
import json
from typing import Optional

from .module_base import ModuleBase


class ModuleGPTInfo(ModuleBase):
    Output: str = ""

    def initialize(self) -> None:
        # Validate that an API key is available up-front so calls fail fast
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        # No heavy initialisation is required beyond environment validation,
        # but the flag indicates the module is ready for use

    def fire(self) -> None:
        self._ensure_initialized()
        # this module is request driven; nothing to do each step

    # ------------------------------------------------------------------
    @staticmethod
    def _call_openai(prompt: str, system: Optional[str] = None) -> str:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        import requests  # local import to avoid dependency when unused

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": []
        }
        if system:
            payload["messages"].append({"role": "system", "content": system})
        payload["messages"].append({"role": "user", "content": prompt})
        resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, data=json.dumps(payload), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    @staticmethod
    def get_chatgpt_verify_parent_child(child: str, parent: str) -> str:
        system = "Provide commonsense facts about the following:"  # brief system prompt
        prompt = f"Is the following true: a(n) {child} is a(n) {parent}? (yes or no, no explanation)"
        return ModuleGPTInfo._call_openai(prompt, system)

    @staticmethod
    def get_chatgpt_parents(text: str) -> str:
        text = text.lstrip('.')
        user = f"Provide commonsense classification answer the request which is appropriate for a 5 year old: What is-a {text}"
        system = (
            "This is a classification request. Examples: horse is-a | animal, mammal\n"
            "chimpanzee is-a | primate, mammal. Answer is formatted: is-a | VALUE, VALUE, VALUE"
        )
        return ModuleGPTInfo._call_openai(user, system)

    @staticmethod
    def get_chatgpt_data(text: str) -> str:
        text = text.replace('.', '')
        user = f"Provide commonsense facts to answer the request: what is a {text}"
        system = (
            "Provide answers that are common sense to a 10 year old. Each Answer in the format VALUE-NAME | VALUE, VALUE"
        )
        return ModuleGPTInfo._call_openai(user, system)
