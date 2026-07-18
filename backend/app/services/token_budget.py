"""Token budget manager service.

Manages token budgets for LLM context windows, ensuring
context doesn't overflow and output tokens are reserved.
"""

from dataclasses import dataclass
from typing import Optional

from app.config import get_settings
from app.services.token_counter import token_counter
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class TokenBudget:
    """Token budget for a single request."""

    total_window: int
    reserved_output: int
    available_for_input: int
    system_prompt_tokens: int
    conversation_tokens: int
    context_tokens: int
    query_tokens: int
    remaining_tokens: int


@dataclass
class CompressedContext:
    """Result of context compression."""

    content: str
    original_tokens: int
    compressed_tokens: int
    chunks_kept: int
    chunks_dropped: int
    citations_preserved: list[str]


class TokenBudgetManager:
    """Manages token budgets for LLM requests.

    Responsibilities:
    - Calculate available context window
    - Reserve output tokens
    - Truncate retrieved context to fit budget
    - Prevent context overflow
    """

    def __init__(
        self,
        context_window: Optional[int] = None,
        output_reserved: Optional[int] = None,
    ):
        """Initialize the token budget manager.

        Args:
            context_window: Total context window size (default from config).
            output_reserved: Tokens to reserve for output (default from config).
        """
        self._context_window = context_window or getattr(
            settings, "LLM_CONTEXT_WINDOW", 8192
        )
        self._output_reserved = output_reserved or getattr(
            settings, "LLM_OUTPUT_RESERVED_TOKENS", 1024
        )
        logger.info(
            f"Token budget manager initialized: "
            f"window={self._context_window}, reserved={self._output_reserved}"
        )

    def calculate_budget(
        self,
        system_prompt: str = "",
        conversation: Optional[list[dict[str, str]]] = "",
        query: str = "",
    ) -> TokenBudget:
        """Calculate token budget for a request.

        Args:
            system_prompt: System prompt text.
            conversation: Conversation history.
            query: User query.

        Returns:
            TokenBudget with token allocations.
        """
        system_tokens = token_counter.count_tokens(system_prompt) if system_prompt else 0

        conversation_tokens = 0
        if conversation:
            conversation_tokens = token_counter.count_message_tokens(conversation)

        query_tokens = token_counter.count_tokens(query) if query else 0

        # Calculate available tokens for context
        used_tokens = system_tokens + conversation_tokens + query_tokens
        available_for_context = (
            self._context_window
            - self._output_reserved
            - used_tokens
        )

        # Ensure non-negative
        available_for_context = max(0, available_for_context)

        remaining = self._context_window - used_tokens - self._output_reserved

        return TokenBudget(
            total_window=self._context_window,
            reserved_output=self._output_reserved,
            available_for_input=available_for_context,
            system_prompt_tokens=system_tokens,
            conversation_tokens=conversation_tokens,
            context_tokens=available_for_context,
            query_tokens=query_tokens,
            remaining_tokens=max(0, remaining),
        )

    def compress_context(
        self,
        context: str,
        budget_tokens: int,
        ranked_chunks: Optional[list] = None,
    ) -> CompressedContext:
        """Compress context to fit within token budget.

        Strategy:
        1. If context fits, return as-is
        2. If exceeds budget, keep highest-ranked chunks
        3. Preserve citations (metadata at end of chunks)
        4. Never truncate in middle of metadata

        Args:
            context: Full context string.
            budget_tokens: Maximum tokens allowed.
            ranked_chunks: Optional list of ranked chunks with metadata.

        Returns:
            CompressedContext with compression results.
        """
        original_tokens = token_counter.count_tokens(context)

        if original_tokens <= budget_tokens:
            return CompressedContext(
                content=context,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                chunks_kept=len(ranked_chunks) if ranked_chunks else 0,
                chunks_dropped=0,
                citations_preserved=[],
            )

        logger.info(
            f"Context compression needed: {original_tokens} tokens "
            f"exceeds budget of {budget_tokens} tokens"
        )

        # Split context into chunks by "---" separator
        chunks = context.split("\n---\n")
        if len(chunks) <= 1:
            # No clear chunk boundaries, truncate intelligently
            compressed = token_counter.truncate_to_tokens(context, budget_tokens)
            return CompressedContext(
                content=compressed,
                original_tokens=original_tokens,
                compressed_tokens=token_counter.count_tokens(compressed),
                chunks_kept=1,
                chunks_dropped=0,
                citations_preserved=[],
            )

        # Keep chunks that fit within budget
        kept_chunks = []
        kept_tokens = 0
        citations = []
        chunks_dropped = 0

        for i, chunk in enumerate(chunks):
            chunk_tokens = token_counter.count_tokens(chunk)

            if kept_tokens + chunk_tokens <= budget_tokens:
                kept_chunks.append(chunk)
                kept_tokens += chunk_tokens

                # Extract citation if present
                if "[Source:" in chunk:
                    start = chunk.find("[Source:")
                    end = chunk.find("]", start)
                    if end > start:
                        citations.append(chunk[start:end + 1])
            else:
                chunks_dropped += 1

        # Add truncation notice if chunks were dropped
        if chunks_dropped > 0:
            kept_chunks.append(
                f"\n\n[Context truncated: {chunks_dropped} chunks omitted due to token limit]"
            )

        compressed_content = "\n---\n".join(kept_chunks)
        compressed_tokens = token_counter.count_tokens(compressed_content)

        logger.info(
            f"Context compressed: {original_tokens} → {compressed_tokens} tokens, "
            f"kept={len(kept_chunks)}, dropped={chunks_dropped}"
        )

        return CompressedContext(
            content=compressed_content,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            chunks_kept=len(kept_chunks),
            chunks_dropped=chunks_dropped,
            citations_preserved=citations,
        )

    def validate_request(
        self,
        system_prompt: str = "",
        conversation: Optional[list[dict[str, str]]] = None,
        query: str = "",
        context: str = "",
    ) -> tuple[bool, str, Optional[TokenBudget]]:
        """Validate that a request fits within token budget.

        Args:
            system_prompt: System prompt.
            conversation: Conversation history.
            query: User query.
            context: Retrieved context.

        Returns:
            Tuple of (is_valid, error_message, budget).
        """
        budget = self.calculate_budget(
            system_prompt=system_prompt,
            conversation=conversation,
            query=query,
        )

        context_tokens = token_counter.count_tokens(context)

        if context_tokens > budget.available_for_input:
            return (
                False,
                f"Context too large: {context_tokens} tokens exceeds "
                f"available budget of {budget.available_for_input} tokens",
                budget,
            )

        return True, "", budget


# Module-level instance
token_budget_manager = TokenBudgetManager()
