"""Tests for the prompt builder and token counter services.

Tests prompt construction, context injection, and token counting.
"""

import pytest

from app.services.prompt_builder import PromptBuilder, prompt_builder
from app.services.token_counter import TokenCounter, token_counter


class TestPromptBuilder:
    """Test PromptBuilder service."""

    def test_initialization_default(self):
        """Test prompt builder with default system prompt."""
        builder = PromptBuilder()
        assert builder.get_system_prompt() is not None
        assert len(builder.get_system_prompt()) > 0

    def test_initialization_custom(self):
        """Test prompt builder with custom system prompt."""
        custom_prompt = "Custom system prompt"
        builder = PromptBuilder(system_prompt=custom_prompt)
        assert builder.get_system_prompt() == custom_prompt

    def test_build_rag_prompt_basic(self):
        """Test building basic RAG prompt."""
        builder = PromptBuilder()
        messages = builder.build_rag_prompt(
            query="What is the policy?",
            context="The policy states that...",
        )

        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert "What is the policy?" in messages[-1]["content"]

    def test_build_rag_prompt_with_context(self):
        """Test RAG prompt includes context."""
        builder = PromptBuilder()
        context = "Document 1: Important information here."
        messages = builder.build_rag_prompt(
            query="Tell me about the document",
            context=context,
        )

        # Context should be in the user message
        user_message = messages[-1]["content"]
        assert "Important information here" in user_message

    def test_build_rag_prompt_with_history(self):
        """Test RAG prompt with conversation history."""
        builder = PromptBuilder()
        history = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"},
        ]
        messages = builder.build_rag_prompt(
            query="Follow-up question",
            context="Some context",
            conversation_history=history,
        )

        # Should have system + history + current user message
        assert len(messages) >= 4
        assert messages[1]["content"] == "Previous question"
        assert messages[2]["content"] == "Previous answer"

    def test_build_simple_prompt(self):
        """Test building simple prompt without context."""
        builder = PromptBuilder()
        messages = builder.build_simple_prompt(query="Hello")

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello"

    def test_set_system_prompt(self):
        """Test setting custom system prompt."""
        builder = PromptBuilder()
        new_prompt = "New system prompt"
        builder.set_system_prompt(new_prompt)
        assert builder.get_system_prompt() == new_prompt

    def test_truncate_context_short(self):
        """Test context truncation with short context."""
        builder = PromptBuilder()
        context = "Short context"
        truncated = builder.truncate_context(context, max_tokens=1000)
        assert truncated == context

    def test_truncate_context_long(self):
        """Test context truncation with long context."""
        builder = PromptBuilder()
        # Create context that exceeds token limit
        long_context = "word " * 10000  # ~5000 tokens
        truncated = builder.truncate_context(long_context, max_tokens=100)
        assert len(truncated) < len(long_context)
        assert "truncated" in truncated.lower()


class TestTokenCounter:
    """Test TokenCounter service."""

    def test_initialization(self):
        """Test token counter initialization."""
        counter = TokenCounter()
        assert counter.get_encoding_info()["encoding_name"] == "cl100k_base"

    def test_count_tokens_basic(self):
        """Test basic token counting."""
        counter = TokenCounter()
        tokens = counter.count_tokens("Hello, world!")
        assert tokens > 0
        assert isinstance(tokens, int)

    def test_count_tokens_empty(self):
        """Test token counting with empty text."""
        counter = TokenCounter()
        assert counter.count_tokens("") == 0
        assert counter.count_tokens(None) == 0

    def test_count_tokens_long_text(self):
        """Test token counting with longer text."""
        counter = TokenCounter()
        text = "This is a test sentence with some words. " * 10
        tokens = counter.count_tokens(text)
        assert tokens > 10  # Should have multiple tokens

    def test_count_message_tokens(self):
        """Test token counting for messages."""
        counter = TokenCounter()
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]
        tokens = counter.count_message_tokens(messages)
        assert tokens > 0

    def test_truncate_to_tokens_short(self):
        """Test truncation with short text."""
        counter = TokenCounter()
        text = "Short text"
        truncated = counter.truncate_to_tokens(text, max_tokens=1000)
        assert truncated == text

    def test_truncate_to_tokens_long(self):
        """Test truncation with long text."""
        counter = TokenCounter()
        long_text = "This is a sentence. " * 1000
        truncated = counter.truncate_to_tokens(long_text, max_tokens=50)
        assert len(truncated) < len(long_text)

    def test_estimate_cost(self):
        """Test cost estimation."""
        counter = TokenCounter()
        cost = counter.estimate_cost(
            prompt_tokens=1000,
            completion_tokens=500,
            model="gpt-3.5-turbo",
        )
        assert cost > 0
        assert isinstance(cost, float)

    def test_estimate_cost_free_model(self):
        """Test cost estimation for free model."""
        counter = TokenCounter()
        cost = counter.estimate_cost(
            prompt_tokens=1000,
            completion_tokens=500,
            model="llama-3.1-8b-instruct",
        )
        assert cost == 0.0

    def test_module_level_instance(self):
        """Test module-level token counter instance."""
        assert token_counter is not None
        assert isinstance(token_counter, TokenCounter)
