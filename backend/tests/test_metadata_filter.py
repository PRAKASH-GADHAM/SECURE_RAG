"""Tests for the metadata filter service.

Tests ChromaDB filter building with various filter structures
and edge cases.
"""

import pytest

from app.services.metadata_filter import MetadataFilter, FilterOperator


class TestMetadataFilter:
    """Test MetadataFilter service."""

    def test_build_empty_filter(self):
        """Test building filter with no conditions."""
        result = MetadataFilter.build_chroma_filter()
        assert result is None

    def test_build_document_ids_single(self):
        """Test building filter with single document ID."""
        result = MetadataFilter.build_chroma_filter(
            document_ids=["doc123"]
        )
        assert result == {"document_id": "doc123"}

    def test_build_document_ids_multiple(self):
        """Test building filter with multiple document IDs."""
        result = MetadataFilter.build_chroma_filter(
            document_ids=["doc1", "doc2", "doc3"]
        )
        assert result == {"document_id": {"$in": ["doc1", "doc2", "doc3"]}}

    def test_build_simple_equality_filter(self):
        """Test building simple equality filter."""
        filters = {"section": "introduction"}
        result = MetadataFilter.build_chroma_filter(filters=filters)
        assert result == {"section": "introduction"}

    def test_build_operator_filter_eq(self):
        """Test building filter with $eq operator."""
        filters = {"content_type": {"$eq": "pdf"}}
        result = MetadataFilter.build_chroma_filter(filters=filters)
        assert result == {"content_type": {"$eq": "pdf"}}

    def test_build_operator_filter_in(self):
        """Test building filter with $in operator."""
        filters = {"content_type": {"$in": ["pdf", "docx"]}}
        result = MetadataFilter.build_chroma_filter(filters=filters)
        assert result == {"content_type": {"$in": ["pdf", "docx"]}}

    def test_build_operator_filter_gt(self):
        """Test building filter with $gt operator."""
        filters = {"page_number": {"$gt": 5}}
        result = MetadataFilter.build_chroma_filter(filters=filters)
        assert result == {"page_number": {"$gt": 5}}

    def test_build_operator_filter_range(self):
        """Test building filter with range operators."""
        filters = {"page_number": {"$gte": 1, "$lte": 10}}
        result = MetadataFilter.build_chroma_filter(filters=filters)
        assert "$and" in result
        assert len(result["$and"]) == 2

    def test_build_combined_filters(self):
        """Test building filter with document IDs and metadata."""
        result = MetadataFilter.build_chroma_filter(
            filters={"section": "conclusion"},
            document_ids=["doc1", "doc2"],
        )
        assert "$and" in result
        assert len(result["$and"]) == 2

    def test_build_and_filter(self):
        """Test building $and filter."""
        filters = {
            "$and": [
                {"section": "introduction"},
                {"page_number": {"$gte": 1}},
            ]
        }
        result = MetadataFilter.build_chroma_filter(filters=filters)
        assert "$and" in result

    def test_build_or_filter(self):
        """Test building $or filter."""
        filters = {
            "$or": [
                {"section": "introduction"},
                {"section": "conclusion"},
            ]
        }
        result = MetadataFilter.build_chroma_filter(filters=filters)
        assert "$or" in result

    def test_validate_filters_valid(self):
        """Test validating valid filters."""
        filters = {"section": "test", "page_number": {"$gt": 5}}
        is_valid, error = MetadataFilter.validate_filters(filters)
        assert is_valid is True
        assert error == ""

    def test_validate_filters_none(self):
        """Test validating None filters."""
        is_valid, error = MetadataFilter.validate_filters(None)
        assert is_valid is True

    def test_validate_filters_empty(self):
        """Test validating empty filters."""
        is_valid, error = MetadataFilter.validate_filters({})
        assert is_valid is True

    def test_get_supported_fields(self):
        """Test getting supported filter fields."""
        fields = MetadataFilter.get_supported_fields()
        assert "document_id" in fields
        assert "page_number" in fields
        assert "section" in fields
        assert "content_type" in fields

    def test_build_filter_with_unsupported_operator(self):
        """Test that unsupported operators are skipped gracefully."""
        filters = {"field": {"$unsupported": "value"}}
        result = MetadataFilter.build_chroma_filter(filters=filters)
        # Should not include the unsupported operator
        assert result is None or "$unsupported" not in str(result)

    def test_build_nested_and_or_filters(self):
        """Test building nested AND/OR filters."""
        filters = {
            "$and": [
                {"$or": [
                    {"section": "intro"},
                    {"section": "conclusion"},
                ]},
                {"page_number": {"$gte": 1}},
            ]
        }
        result = MetadataFilter.build_chroma_filter(filters=filters)
        assert result is not None
        assert "$and" in result


class TestFilterOperators:
    """Test FilterOperator enum."""

    def test_filter_operator_values(self):
        """Test all filter operator values."""
        assert FilterOperator.EQ.value == "$eq"
        assert FilterOperator.NE.value == "$ne"
        assert FilterOperator.IN.value == "$in"
        assert FilterOperator.NIN.value == "$nin"
        assert FilterOperator.GT.value == "$gt"
        assert FilterOperator.GTE.value == "$gte"
        assert FilterOperator.LT.value == "$lt"
        assert FilterOperator.LTE.value == "$lte"
        assert FilterOperator.AND.value == "$and"
        assert FilterOperator.OR.value == "$or"

    def test_filter_operator_from_string(self):
        """Test creating FilterOperator from string."""
        assert FilterOperator("$eq") == FilterOperator.EQ
        assert FilterOperator("$in") == FilterOperator.IN
