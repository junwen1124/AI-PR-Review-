"""LLM API client supporting OpenAI-compatible endpoints (DeepSeek, GPT, etc.)."""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Default configuration
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.3


class AIClient:
    """Thin wrapper around OpenAI-compatible chat API for code review."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ):
        self.api_key = api_key or os.getenv("AI_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Set AI_API_KEY, DEEPSEEK_API_KEY, or OPENAI_API_KEY env var."
            )
        self.model = model or os.getenv("AI_MODEL", DEFAULT_MODEL)
        self.base_url = base_url or os.getenv("AI_BASE_URL", DEFAULT_BASE_URL)
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(self, system_prompt: str, user_prompt: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
        """Send a chat completion request."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=DEFAULT_TEMPERATURE,
        )
        content = response.choices[0].message.content
        return content or ""

    def review(self, prompt: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
        """Send a code review request. Uses the structured system prompt from reviewer."""
        try:
            from .reviewer import SYSTEM_PROMPT
        except ImportError:
            from reviewer import SYSTEM_PROMPT
        return self.chat(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=max_tokens,
        )

    def review_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> str:
        """Send a review with separate system and user prompts."""
        return self.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
        )
