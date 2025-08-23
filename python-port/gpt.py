"""GPT client abstraction used by BrainSimIII modules.

The original C# project delegates all large language model access through a
wrapper so that the rest of the codebase does not need to know whether the
backend is an online service or a locally hosted model.  This Python port
follows the same idea but deliberately avoids shipping any built-in fallback or
placeholder generator.  Callers may supply a callable ``local_model`` which
performs text generation when no API key is configured.  This keeps the core
library lightweight while allowing integration with transformers, llama.cpp or
any other inference stack supplied by the user.
"""

from typing import Callable, Optional
import os
import threading

try:
    import openai
except Exception:  # pragma: no cover
    openai = None  # type: ignore


class GPTClient:
    """Wrapper around OpenAI's API with optional local-model delegation.

    Parameters
    ----------
    api_key:
        OpenAI API key.  If omitted, :func:`os.getenv` is used to look for
        ``OPENAI_API_KEY``.  When the key is absent and ``local_model`` is not
        provided the client raises :class:`RuntimeError`.
    model:
        Name of the OpenAI chat model to use when talking to the remote API.
    local_model:
        Optional callable of the form ``fn(prompt: str, max_tokens: int) -> str``
        which performs local text generation.  Supplying a callable enables
        offline operation while keeping this module agnostic to the actual
        inference backend.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        local_model: Optional[Callable[[str, int], str]] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.local_model = local_model
        self._lock = threading.Lock()
        if self.api_key and openai is not None:
            openai.api_key = self.api_key

    def generate(self, prompt: str, max_tokens: int = 50) -> str:
        """Generate text from ``prompt``.

        If a ``local_model`` callable was supplied it is used.  Otherwise the
        OpenAI API is called.  The function raises :class:`RuntimeError` if no
        generation backend is available.
        """

        with self._lock:
            if self.local_model is not None:
                return self.local_model(prompt, max_tokens)

            if openai is None:
                raise RuntimeError("openai package is not installed and no local model provided")
            if not self.api_key:
                raise RuntimeError("OPENAI_API_KEY not set and no local model provided")
            completion = openai.ChatCompletion.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return completion.choices[0].message["content"].strip()
