"""Tests for prompt builder service.

Covers RAG prompt construction, simple prompts, context injection, and truncation.
"""

import pytest

from app.services.prompt_builder import PromptBuilder, DEFAULT_SYSTEM_PROMPT, prompt_builder


class TestBuildRAGPrompt:
    """Tests for build_rag_prompt."""

    def test_returns_list_of_messages(self):
        builder = PromptBuilder()
        messages = builder.build_rag_prompt(query="What is RAG?", context="RAG info")
        assert isinstance(messages, list)
        assert len(messages) > 0

    def test_includes_system_message(self):
        builder = PromptBuilder()
        messages = builder.build_rag_prompt(query="test", context="context")
        assert messages[0]["role"] == "system"

    def test_includes_user_message(self):
        builder = PromptBuilder()
        messages = builder.build_rag_prompt(query="What is X?", context="X is Y")
        user_msgs = [m for m in messages if m["role"] == "user"]
        assert len(user_msgs) >= 1

    def test_includes_query_in_user_message(self):
        builder = PromptBuilder()
        messages = builder.build_rag_prompt(query="What is RAG?", context="some context")
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "What is RAG?" in user_msg["content"]

    def test_includes_context_in_user_message(self):
        builder = PromptBuilder()
        messages = builder.build_rag_prompt(
            query="test", context="RAG is Retrieval Augmented Generation"
        )
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "Retrieval Augmented Generation" in user_msg["content"]

    def test_empty_context(self):
        builder = PromptBuilder()
        messages = builder.build_rag_prompt(query="test", context="")
        assert len(messages) >= 2  # system + user

    def test_conversation_history_included(self):
        builder = PromptBuilder()
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        messages = builder.build_rag_prompt(query="follow up", context="ctx", conversation_history=history)
        contents = [m["content"] for m in messages]
        assert any("Hello" in c for c in contents)

    def test_conversation_history_limited_to_10(self):
        builder = PromptBuilder()
        history = [{"role": "user", "content": f"msg{i}"} for i in range(20)]
        messages = builder.build_rag_prompt(query="q", context="ctx", conversation_history=history)
        non_system = [m for m in messages if m["role"] != "system"]
        assert len(non_system) <= 11  # 10 history + 1 current user msg

    def test_custom_system_prompt(self):
        custom = "You are a pirate assistant."
        builder = PromptBuilder(system_prompt=custom)
        messages = builder.build_rag_prompt(query="test", context="ctx")
        assert messages[0]["content"] == custom

    def test_source_citation_instruction(self):
        builder = PromptBuilder()
        messages = builder.build_rag_prompt(
            query="test", context="some context", include_sources=True
        )
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "Cite" in user_msg["content"] or "cite" in user_msg["content"]

    def test_no_source_instruction_when_disabled(self):
        builder = PromptBuilder()
        messages = builder.build_rag_prompt(
            query="test", context="some context", include_sources=False
        )
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "Cite" not in user_msg["content"]


class TestBuildSimplePrompt:
    """Tests for build_simple_prompt."""

    def test_returns_list_of_messages(self):
        builder = PromptBuilder()
        messages = builder.build_simple_prompt(query="Hello")
        assert isinstance(messages, list)
        assert len(messages) == 2

    def test_system_and_user_messages(self):
        builder = PromptBuilder()
        messages = builder.build_simple_prompt(query="Hello")
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_query_in_user_message(self):
        builder = PromptBuilder()
        messages = builder.build_simple_prompt(query="What is AI?")
        assert "What is AI?" in messages[1]["content"]

    def test_custom_system_prompt(self):
        builder = PromptBuilder()
        messages = builder.build_simple_prompt(query="q", system_prompt="Custom prompt")
        assert messages[0]["content"] == "Custom prompt"

    def test_uses_default_system_prompt(self):
        builder = PromptBuilder()
        messages = builder.build_simple_prompt(query="q")
        assert messages[0]["content"] == builder._system_prompt


class TestTruncateContext:
    """Tests for truncate_context."""

    def test_short_context_not_truncated(self):
        builder = PromptBuilder()
        result = builder.truncate_context("short context", max_tokens=1000)
        assert result == "short context"

    def test_empty_context_returns_empty(self):
        builder = PromptBuilder()
        result = builder.truncate_context("", max_tokens=1000)
        assert result == ""

    def test_none_context_returns_empty(self):
        builder = PromptBuilder()
        result = builder.truncate_context(None, max_tokens=1000)
        assert result == ""

    def test_long_context_truncated(self):
        builder = PromptBuilder()
        long_ctx = "word " * 5000
        result = builder.truncate_context(long_ctx, max_tokens=10)
        assert len(result) < len(long_ctx)

    def test_truncation_message_appended(self):
        builder = PromptBuilder()
        long_ctx = "word " * 5000
        result = builder.truncate_context(long_ctx, max_tokens=10)
        assert "[Context truncated due to token limit]" in result

    def test_with_token_counter_function(self):
        builder = PromptBuilder()
        # Token counter that always reports high usage
        def high_counter(text):
            return 100000
        result = builder.truncate_context("context", max_tokens=10, token_counter=high_counter)
        assert "[Context truncated due to token limit]" in result

    def test_with_token_counter_within_limit(self):
        builder = PromptBuilder()
        def low_counter(text):
            return 5
        result = builder.truncate_context("short", max_tokens=100, token_counter=low_counter)
        assert result == "short"


class TestGetSetSystemPrompt:
    """Tests for system prompt getter and setter."""

    def test_get_system_prompt(self):
        builder = PromptBuilder()
        prompt = builder.get_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_set_system_prompt(self):
        builder = PromptBuilder()
        builder.set_system_prompt("New prompt")
        assert builder.get_system_prompt() == "New prompt"

    def test_default_prompt_contains_assistant(self):
        builder = PromptBuilder()
        assert "assistant" in builder.get_system_prompt().lower()


class TestContextMessage:
    """Tests for _build_context_message."""

    def test_context_markers(self):
        builder = PromptBuilder()
        msg = builder._build_context_message(query="q", context="some context")
        assert "--- Context Start ---" in msg
        assert "--- Context End ---" in msg

    def test_query_in_message(self):
        builder = PromptBuilder()
        msg = builder._build_context_message(query="What is X?", context="X info")
        assert "What is X?" in msg

    def test_context_in_message(self):
        builder = PromptBuilder()
        msg = builder._build_context_message(query="q", context="important info here")
        assert "important info here" in msg

    def test_empty_context_no_markers(self):
        builder = PromptBuilder()
        msg = builder._build_context_message(query="q", context="")
        assert "Context Start" not in msg

    def test_empty_context_none(self):
        builder = PromptBuilder()
        msg = builder._build_context_message(query="q", context=None)
        assert "Context Start" not in msg


class TestModuleLevelInstance:
    """Tests for module-level prompt_builder instance."""

    def test_exists(self):
        assert prompt_builder is not None

    def test_is_prompt_builder(self):
        assert isinstance(prompt_builder, PromptBuilder)
