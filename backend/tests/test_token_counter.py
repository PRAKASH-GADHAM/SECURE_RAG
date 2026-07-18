"""Tests for token counter service.

Covers token counting, truncation, message counting, and cost estimation.
"""

import pytest

from app.services.token_counter import TokenCounter, token_counter


class TestTokenCounter:
    """Tests for TokenCounter class."""

    def test_count_tokens_returns_positive(self):
        tc = TokenCounter()
        count = tc.count_tokens("Hello world")
        assert count > 0

    def test_count_tokens_empty(self):
        tc = TokenCounter()
        count = tc.count_tokens("")
        assert count == 0

    def test_count_tokens_longer_text(self):
        tc = TokenCounter()
        short = tc.count_tokens("Hello")
        long = tc.count_tokens("Hello world this is a longer sentence with more tokens")
        assert long > short

    def test_default_encoding(self):
        tc = TokenCounter()
        assert tc._encoding_name == "cl100k_base"

    def test_encoding_lazy_loaded(self):
        tc = TokenCounter()
        assert tc._encoding is None
        # Accessing encoding triggers lazy load
        enc = tc.encoding
        assert enc is not None
        assert tc._encoding is not None


class TestTruncateToTokens:
    """Tests for truncate_to_tokens."""

    def test_short_text_not_truncated(self):
        tc = TokenCounter()
        text = "Hello"
        result = tc.truncate_to_tokens(text, max_tokens=100)
        assert result == text

    def test_long_text_truncated(self):
        tc = TokenCounter()
        text = "word " * 1000
        result = tc.truncate_to_tokens(text, max_tokens=10)
        assert result != text
        assert "[Truncated due to token limit]" in result

    def test_empty_text_returns_empty(self):
        tc = TokenCounter()
        result = tc.truncate_to_tokens("", max_tokens=10)
        assert result == ""

    def test_exact_limit_not_truncated(self):
        tc = TokenCounter()
        text = "Hello world"
        token_count = tc.count_tokens(text)
        result = tc.truncate_to_tokens(text, max_tokens=token_count)
        assert result == text


class TestCountMessageTokens:
    """Tests for count_message_tokens."""

    def test_counts_single_message(self):
        tc = TokenCounter()
        messages = [{"role": "user", "content": "Hello"}]
        count = tc.count_message_tokens(messages)
        assert count > 0

    def test_counts_multiple_messages(self):
        tc = TokenCounter()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        single = tc.count_message_tokens([messages[0]])
        double = tc.count_message_tokens(messages)
        assert double > single

    def test_includes_overhead(self):
        tc = TokenCounter()
        messages = [{"role": "user", "content": ""}]
        count = tc.count_message_tokens(messages)
        # Each message has 4 overhead tokens + 2 reply priming
        assert count >= 6

    def test_empty_content(self):
        tc = TokenCounter()
        messages = [{"role": "user", "content": ""}]
        count = tc.count_message_tokens(messages)
        assert count > 0  # overhead still counted


class TestEstimateCost:
    """Tests for estimate_cost."""

    def test_returns_float(self):
        tc = TokenCounter()
        cost = tc.estimate_cost(100, 50)
        assert isinstance(cost, float)

    def test_zero_tokens_zero_cost(self):
        tc = TokenCounter()
        cost = tc.estimate_cost(0, 0)
        assert cost == 0.0

    def test_higher_tokens_higher_cost(self):
        tc = TokenCounter()
        low = tc.estimate_cost(100, 50)
        high = tc.estimate_cost(1000, 500)
        assert high > low

    def test_different_models(self):
        tc = TokenCounter()
        cost_35 = tc.estimate_cost(1000, 1000, model="gpt-3.5-turbo")
        cost_4 = tc.estimate_cost(1000, 1000, model="gpt-4")
        assert cost_4 > cost_35

    def test_free_model(self):
        tc = TokenCounter()
        cost = tc.estimate_cost(1000, 1000, model="llama-3.1-8b-instruct")
        assert cost == 0.0


class TestModuleLevelInstance:
    """Tests for module-level token_counter instance."""

    def test_exists(self):
        assert token_counter is not None

    def test_is_token_counter(self):
        assert isinstance(token_counter, TokenCounter)

    def test_works(self):
        count = token_counter.count_tokens("Hello world")
        assert count > 0


class TestGetEncodingInfo:
    """Tests for get_encoding_info."""

    def test_returns_dict(self):
        tc = TokenCounter()
        info = tc.get_encoding_info()
        assert isinstance(info, dict)

    def test_includes_encoding_name(self):
        tc = TokenCounter()
        info = tc.get_encoding_info()
        assert info["encoding_name"] == "cl100k_base"

    def test_not_loaded_before_use(self):
        tc = TokenCounter()
        info = tc.get_encoding_info()
        assert info["is_loaded"] is False

    def test_loaded_after_use(self):
        tc = TokenCounter()
        tc.count_tokens("test")
        info = tc.get_encoding_info()
        assert info["is_loaded"] is True
