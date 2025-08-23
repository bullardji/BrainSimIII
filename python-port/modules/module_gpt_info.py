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
from gpt import GPTClient



class ModuleGPTInfo(ModuleBase):
    Output: str = ""

    def initialize(self, local_model: Optional[str] = None) -> None:
        """Initialise GPT client using either OpenAI API or a local model.

        If ``OPENAI_API_KEY`` is available the remote API is used; otherwise
        a local model specified via ``local_model`` is loaded using the
        :class:`~python-port.gpt.GPTClient`.  This mirrors the flexibility of
        the C# version which can operate offline with local models.
        """

        api_key = os.getenv("OPENAI_API_KEY")
        self._client = GPTClient(api_key=api_key, local_model=local_model)

    def fire(self) -> None:
        self._ensure_initialized()
        # this module is request driven; nothing to do each step

    # ------------------------------------------------------------------
    @staticmethod
    def _call_openai(prompt: str, system: Optional[str] = None) -> str:
        # For compatibility with legacy callers, route through GPTClient
        # which will select remote or local inference as configured.
        client = getattr(ModuleGPTInfo, "_client", None)
        if client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            client = GPTClient(api_key=api_key)
            ModuleGPTInfo._client = client  # cache for reuse

        if system:
            prompt = f"{system}\n{prompt}"
        return client.generate(prompt)

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
