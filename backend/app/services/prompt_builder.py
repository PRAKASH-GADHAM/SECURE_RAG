"""Prompt builder service.

Creates and manages prompts for LLM generation with context injection.
Supports conversation history and source citations.
"""

from dataclasses import dataclass
from typing import Optional

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Default system prompt for enterprise RAG
DEFAULT_SYSTEM_PROMPT = """You are a helpful enterprise knowledge assistant. Your role is to answer questions accurately based on the provided context documents.

Guidelines:
1. Always base your answers on the provided context. If the context doesn't contain enough information, say so clearly.
2. Cite your sources when possible by referencing document names or sections.
3. Be concise and professional in your responses.
4. If you're unsure about something, acknowledge the uncertainty rather than guessing.
5. Never make up information that isn't in the provided context.
6. Format your responses clearly with appropriate paragraphs and structure.
7. If the user asks about something not related to the documents, politely redirect them to ask about the available knowledge base."""


@dataclass
class PromptMessage:
    """A message in the prompt."""

    role: str  # system, user, assistant
    content: str


class PromptBuilder:
    """Builds prompts for LLM generation.

    Supports:
    - System prompt configuration
    - Context injection with source citations
    - Conversation history formatting
    - Token-aware truncation
    """

    def __init__(self, system_prompt: Optional[str] = None):
        """Initialize the prompt builder.

        Args:
            system_prompt: Optional custom system prompt.
        """
        self._system_prompt = system_prompt or getattr(
            settings, "LLM_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT
        )
        logger.info("Prompt Builder initialized")

    def build_rag_prompt(
        self,
        query: str,
        context: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
        include_sources: bool = True,
    ) -> list[dict[str, str]]:
        """Build a RAG prompt with context injection.

        Args:
            query: User query.
            context: Retrieved context string.
            conversation_history: Optional conversation history.
            include_sources: Whether to include source citations in prompt.

        Returns:
            List of message dictionaries for LLM.
        """
        messages = []

        # System prompt
        messages.append({
            "role": "system",
            "content": self._system_prompt,
        })

        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })

        # Build the context-enhanced user message
        user_message = self._build_context_message(
            query, context, include_sources
        )
        messages.append({
            "role": "user",
            "content": user_message,
        })

        return messages

    def _build_context_message(
        self,
        query: str,
        context: str,
        include_sources: bool = True,
    ) -> str:
        """Build a user message with context injection.

        Args:
            query: User query.
            context: Retrieved context string.
            include_sources: Whether to include source information.

        Returns:
            Formatted user message with context.
        """
        parts = []

        if context and context.strip():
            parts.append("Based on the following context documents:")
            parts.append("")
            parts.append("--- Context Start ---")
            parts.append(context)
            parts.append("--- Context End ---")
            parts.append("")

        parts.append(f"Question: {query}")

        if include_sources and context:
            parts.append("")
            parts.append(
                "Please provide a comprehensive answer based on the context above. "
                "Cite specific documents or sections when possible."
            )

        return "\n".join(parts)

    def build_simple_prompt(
        self,
        query: str,
        system_prompt: Optional[str] = None,
    ) -> list[dict[str, str]]:
        """Build a simple prompt without context.

        Args:
            query: User query.
            system_prompt: Optional override for system prompt.

        Returns:
            List of message dictionaries for LLM.
        """
        messages = []

        messages.append({
            "role": "system",
            "content": system_prompt or self._system_prompt,
        })

        messages.append({
            "role": "user",
            "content": query,
        })

        return messages

    def truncate_context(
        self,
        context: str,
        max_tokens: int,
        token_counter=None,
    ) -> str:
        """Truncate context to fit within token limits.

        Args:
            context: Context string to truncate.
            max_tokens: Maximum tokens allowed.
            token_counter: Optional token counter function.

        Returns:
            Truncated context string.
        """
        if not context:
            return ""

        if token_counter:
            token_count = token_counter(context)
            if token_count <= max_tokens:
                return context

            # Truncate by characters (approximate)
            avg_chars_per_token = 4
            max_chars = max_tokens * avg_chars_per_token
            truncated = context[:max_chars]

            # Find last complete sentence or paragraph
            last_newline = truncated.rfind("\n")
            if last_newline > max_chars * 0.8:
                truncated = truncated[:last_newline]

            return truncated + "\n\n[Context truncated due to token limit]"

        # Fallback: character-based truncation
        avg_chars_per_token = 4
        max_chars = max_tokens * avg_chars_per_token
        if len(context) > max_chars:
            truncated = context[:max_chars]
            last_newline = truncated.rfind("\n")
            if last_newline > max_chars * 0.8:
                truncated = truncated[:last_newline]
            return truncated + "\n\n[Context truncated due to token limit]"

        return context

    def get_system_prompt(self) -> str:
        """Get the current system prompt.

        Returns:
            System prompt string.
        """
        return self._system_prompt

    def set_system_prompt(self, prompt: str):
        """Set a custom system prompt.

        Args:
            prompt: New system prompt.
        """
        self._system_prompt = prompt
        logger.info("System prompt updated")


# Module-level instance
prompt_builder = PromptBuilder()
