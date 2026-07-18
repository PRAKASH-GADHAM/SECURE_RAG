"""Token counter service.

Provides token counting using tiktoken for context management
and cost estimation.
"""

from typing import Optional

import tiktoken

from app.utils.logging import get_logger

logger = get_logger(__name__)


class TokenCounter:
    """Token counter using tiktoken.

    Supports:
    - Token counting for various models
    - Context window management
    - Cost estimation (approximate)
    """

    def __init__(self, encoding_name: str = "cl100k_base"):
        """Initialize the token counter.

        Args:
            encoding_name: tiktoken encoding name.
                          Default: cl100k_base (GPT-4, GPT-3.5-turbo)
        """
        self._encoding_name = encoding_name
        self._encoding: Optional[tiktoken.Encoding] = None
        logger.info(f"Token counter initialized: encoding={encoding_name}")

    @property
    def encoding(self) -> tiktoken.Encoding:
        """Get the tiktoken encoding (lazy loaded)."""
        if self._encoding is None:
            try:
                self._encoding = tiktoken.get_encoding(self._encoding_name)
            except Exception as e:
                logger.warning(
                    f"Failed to load encoding {self._encoding_name}: {e}. "
                    f"Falling back to cl100k_base"
                )
                self._encoding = tiktoken.get_encoding("cl100k_base")
        return self._encoding

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens for.

        Returns:
            Number of tokens.
        """
        if not text:
            return 0

        try:
            tokens = self.encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.warning(f"Token counting failed: {e}")
            # Fallback: approximate by words
            return len(text.split())

    def count_message_tokens(self, messages: list[dict[str, str]]) -> int:
        """Count tokens in a list of messages.

        Args:
            messages: List of message dictionaries.

        Returns:
            Total number of tokens.
        """
        total = 0
        for msg in messages:
            # Each message has overhead for role and formatting
            total += 4  # <role> overhead
            total += self.count_tokens(msg.get("content", ""))
        total += 2  # reply priming
        return total

    def truncate_to_tokens(
        self,
        text: str,
        max_tokens: int,
    ) -> str:
        """Truncate text to fit within token limit.

        Args:
            text: Text to truncate.
            max_tokens: Maximum tokens allowed.

        Returns:
            Truncated text.
        """
        if not text:
            return ""

        try:
            tokens = self.encoding.encode(text)
            if len(tokens) <= max_tokens:
                return text

            # Truncate tokens
            truncated_tokens = tokens[:max_tokens]
            truncated_text = self.encoding.decode(truncated_tokens)

            # Try to end at a sentence or word boundary
            last_period = truncated_text.rfind(".")
            last_newline = truncated_text.rfind("\n")

            if last_period > len(truncated_text) * 0.8:
                truncated_text = truncated_text[: last_period + 1]
            elif last_newline > len(truncated_text) * 0.8:
                truncated_text = truncated_text[:last_newline]

            return truncated_text + "\n\n[Truncated due to token limit]"

        except Exception as e:
            logger.warning(f"Token truncation failed: {e}")
            # Fallback: character-based
            avg_chars_per_token = 4
            max_chars = max_tokens * avg_chars_per_token
            if len(text) > max_chars:
                return text[:max_chars] + "\n\n[Truncated due to token limit]"
            return text

    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str = "gpt-3.5-turbo",
    ) -> float:
        """Estimate cost for token usage (approximate).

        Args:
            prompt_tokens: Number of prompt tokens.
            completion_tokens: Number of completion tokens.
            model: Model name for pricing.

        Returns:
            Estimated cost in USD.
        """
        # Approximate pricing (as of 2024)
        pricing = {
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "llama-3.1-8b-instruct": {"input": 0.0, "output": 0.0},  # Free
        }

        prices = pricing.get(model, pricing["gpt-3.5-turbo"])

        input_cost = (prompt_tokens / 1000) * prices["input"]
        output_cost = (completion_tokens / 1000) * prices["output"]

        return input_cost + output_cost

    def get_encoding_info(self) -> dict:
        """Get information about the current encoding.

        Returns:
            Dictionary with encoding information.
        """
        return {
            "encoding_name": self._encoding_name,
            "is_loaded": self._encoding is not None,
        }


# Module-level instance
token_counter = TokenCounter()
