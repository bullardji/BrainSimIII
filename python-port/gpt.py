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

import inflect

try:  # optional dependency used for token counting
    import tiktoken
except Exception:  # pragma: no cover
    tiktoken = None  # type: ignore

try:  # OpenAI library is optional for offline/local usage
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
        self._inflect = inflect.engine()
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        if tiktoken is not None:
            try:
                self._encoding = tiktoken.encoding_for_model(self.model)
            except Exception:  # pragma: no cover - fall back to default encoding
                self._encoding = tiktoken.get_encoding("cl100k_base")
        else:
            self._encoding = None
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
                output = self.local_model(prompt, max_tokens)
                self._update_token_usage(prompt, output)
                return output

            if openai is None:
                raise RuntimeError("openai package is not installed and no local model provided")
            if not self.api_key:
                raise RuntimeError("OPENAI_API_KEY not set and no local model provided")
            completion = openai.ChatCompletion.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            output = completion.choices[0].message["content"].strip()
            usage = completion.get("usage")
            if usage:
                self.prompt_tokens += usage.get("prompt_tokens", 0)
                self.completion_tokens += usage.get("completion_tokens", 0)
                self.total_tokens += usage.get("total_tokens", 0)
            else:
                self._update_token_usage(prompt, output)
            return output

    # ------------------------------------------------------------------
    # Token accounting helpers
    def _update_token_usage(self, prompt: str, completion: str) -> None:
        """Estimate token usage for ``prompt``/``completion`` pairs."""

        if self._encoding is not None:  # use tiktoken when available
            prompt_toks = len(self._encoding.encode(prompt))
            completion_toks = len(self._encoding.encode(completion))
        else:  # simple whitespace fallback
            prompt_toks = len(prompt.split())
            completion_toks = len(completion.split())
        self.prompt_tokens += prompt_toks
        self.completion_tokens += completion_toks
        self.total_tokens += prompt_toks + completion_toks

    # ------------------------------------------------------------------
    # Pluralisation helpers
    def pluralize(self, word: str, count: int | None = None) -> str:
        """Return the plural form of ``word``.

        If ``count`` is provided the pluralisation rules from ``inflect`` are
        applied taking singular/plural choice into account.
        """

        if count is None:
            return self._inflect.plural(word)
        return self._inflect.plural(word, count)

    def singularize(self, word: str) -> str:
        """Return the singular form of ``word``."""

        result = self._inflect.singular_noun(word)
        return result if result else word
