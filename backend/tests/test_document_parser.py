"""Tests for document parser service.

Tests PDF, DOCX, TXT, and Markdown parsing with real and mock files.
"""

import os
import tempfile

import pytest

from app.core.exceptions import FileUploadException
from app.services.document_parser import DocumentParser, ParsedDocument


class TestDocumentParser:
    """Tests for the DocumentParser service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = DocumentParser()

    def test_parse_txt_file(self):
        """Test parsing a plain text file."""
        content = "Hello world. This is a test document.\nWith multiple lines."
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = self.parser.parse(temp_path, "txt")

            assert isinstance(result, ParsedDocument)
            assert result.content == content
            assert result.word_count == 10
            assert result.char_count == len(content)
            assert result.page_count == 1
            assert result.metadata["parser"] == "plaintext"
            assert result.metadata["line_count"] == 2
        finally:
            os.unlink(temp_path)

    def test_parse_empty_txt_file(self):
        """Test parsing an empty text file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("")
            temp_path = f.name

        try:
            result = self.parser.parse(temp_path, "txt")

            assert result.content == ""
            assert result.word_count == 0
            assert result.char_count == 0
        finally:
            os.unlink(temp_path)

    def test_parse_markdown_file(self):
        """Test parsing a Markdown file."""
        md_content = """# Title

This is a paragraph with **bold** and *italic* text.

## Section 1

Some content under section 1.

## Section 2

More content here.
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(md_content)
            temp_path = f.name

        try:
            result = self.parser.parse(temp_path, "md")

            assert isinstance(result, ParsedDocument)
            assert result.metadata["parser"] == "markdown"
            assert result.metadata["heading_count"] == 3
            assert "Title" in result.metadata["headings"]
            assert len(result.content) > 0
            # HTML tags should be stripped
            assert "<h1>" not in result.content
            assert "<strong>" not in result.content
        finally:
            os.unlink(temp_path)

    def test_parse_unsupported_type(self):
        """Test parsing an unsupported file type."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xyz", delete=False
        ) as f:
            f.write("content")
            temp_path = f.name

        try:
            with pytest.raises(FileUploadException) as exc_info:
                self.parser.parse(temp_path, "xyz")
            assert "Unsupported file type" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_parser_registrations(self):
        """Test that all expected parsers are registered."""
        expected_types = {"pdf", "docx", "txt", "md", "markdown"}
        registered = set(self.parser._parsers.keys())
        assert expected_types == registered

    def test_parse_txt_with_special_characters(self):
        """Test parsing a text file with special characters."""
        content = "Héllo Wörld! 你好世界 🌍\n\tTabbed\t\tcontent"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = self.parser.parse(temp_path, "txt")
            assert result.content == content
        finally:
            os.unlink(temp_path)

    def test_parse_markdown_extension_detection(self):
        """Test that both .md and .markdown extensions work."""
        content = "# Test\n\nContent"
        for ext in [".md", ".markdown"]:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=ext, delete=False, encoding="utf-8"
            ) as f:
                f.write(content)
                temp_path = f.name

            try:
                result = self.parser.parse(temp_path, ext.lstrip("."))
                assert result.metadata["parser"] == "markdown"
            finally:
                os.unlink(temp_path)


class TestParsedDocument:
    """Tests for the ParsedDocument dataclass."""

    def test_post_init_calculations(self):
        """Test that post_init calculates counts correctly."""
        doc = ParsedDocument(content="Hello world test content")
        assert doc.char_count == 24
        assert doc.word_count == 4
        assert doc.page_count == 1

    def test_empty_content(self):
        """Test ParsedDocument with empty content."""
        doc = ParsedDocument(content="")
        assert doc.char_count == 0
        assert doc.word_count == 0

    def test_custom_page_count(self):
        """Test ParsedDocument with explicit page count."""
        doc = ParsedDocument(content="content", page_count=10)
        assert doc.page_count == 10

    def test_metadata_preservation(self):
        """Test that custom metadata is preserved."""
        meta = {"parser": "test", "custom_key": "value"}
        doc = ParsedDocument(content="content", metadata=meta)
        assert doc.metadata == meta
