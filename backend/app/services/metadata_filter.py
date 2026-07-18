"""Metadata filter service.

Builds ChromaDB-compatible metadata filters from query parameters.
Supports various filter operators for flexible document filtering.

This service is designed to work with ChromaDB but can be extended
for other vector databases by implementing filter adapters.
"""

from enum import Enum
from typing import Any, Optional, Union

from app.utils.logging import get_logger

logger = get_logger(__name__)


class FilterOperator(str, Enum):
    """Supported filter operators."""

    EQ = "$eq"  # Equal
    NE = "$ne"  # Not equal (ChromaDB doesn't support, implemented as NOT $eq)
    IN = "$in"  # In list
    NIN = "$nin"  # Not in list (ChromaDB doesn't support, implemented as NOT $in)
    GT = "$gt"  # Greater than
    GTE = "$gte"  # Greater than or equal
    LT = "$lt"  # Less than
    LTE = "$lte"  # Less than or equal
    AND = "$and"  # Logical AND
    OR = "$or"  # Logical OR


class MetadataFilter:
    """Builds metadata filters for vector database queries.

    Supports ChromaDB filter syntax and can be extended for other
    vector databases through filter adapters.

    Example filter structures:
        Simple equality: {"field": "value"}
        Operator: {"field": {"$eq": "value"}}
        IN: {"field": {"$in": ["value1", "value2"]}}
        AND: {"$and": [{"field1": "value1"}, {"field2": "value2"}]}
    """

    # Fields that support range queries
    RANGE_FIELDS = {"page_number", "created_at", "updated_at", "chunk_index"}

    # Fields that support string matching
    STRING_FIELDS = {"document_id", "section", "content_type", "source_file"}

    # All supported filter fields
    SUPPORTED_FIELDS = RANGE_FIELDS | STRING_FIELDS

    @classmethod
    def build_chroma_filter(
        cls,
        filters: Optional[dict[str, Any]] = None,
        document_ids: Optional[list[str]] = None,
    ) -> Optional[dict[str, Any]]:
        """Build ChromaDB-compatible where filter.

        Args:
            filters: Filter specifications from query.
            document_ids: Optional list of document IDs to filter by.

        Returns:
            ChromaDB-compatible where filter, or None if no filters.
        """
        conditions = []

        # Add document_ids filter
        if document_ids:
            if len(document_ids) == 1:
                conditions.append({"document_id": document_ids[0]})
            else:
                conditions.append({"document_id": {"$in": document_ids}})

        # Add custom filters
        if filters:
            filter_condition = cls._build_filter_condition(filters)
            if filter_condition:
                conditions.append(filter_condition)

        # Combine conditions
        if not conditions:
            return None

        if len(conditions) == 1:
            return conditions[0]

        return {"$and": conditions}

    @classmethod
    def _build_filter_condition(cls, filters: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Build a single filter condition.

        Args:
            filters: Filter dictionary.

        Returns:
            ChromaDB-compatible filter condition.
        """
        if not filters:
            return None

        conditions = []

        for field, value in filters.items():
            if field.startswith("$"):
                # Logical operator
                if field in ("$and", "$or") and isinstance(value, list):
                    sub_conditions = []
                    for sub_filter in value:
                        sub_condition = cls._build_filter_condition(sub_filter)
                        if sub_condition:
                            sub_conditions.append(sub_condition)
                    if sub_conditions:
                        if len(sub_conditions) == 1:
                            conditions.append(sub_conditions[0])
                        else:
                            conditions.append({field: sub_conditions})
            elif isinstance(value, dict):
                # Operator-based filter
                condition = cls._build_operator_filter(field, value)
                if condition:
                    conditions.append(condition)
            else:
                # Simple equality
                conditions.append({field: value})

        if not conditions:
            return None

        if len(conditions) == 1:
            return conditions[0]

        return {"$and": conditions}

    @classmethod
    def _build_operator_filter(
        cls, field: str, operators: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Build filter with operators.

        Args:
            field: Field name.
            operators: Dictionary of operators and values.

        Returns:
            ChromaDB-compatible filter condition.
        """
        if not cls._validate_field(field):
            logger.warning(f"Unsupported filter field: {field}")
            return None

        conditions = []
        for op, value in operators.items():
            try:
                filter_op = FilterOperator(op)
            except ValueError:
                logger.warning(f"Unsupported filter operator: {op}")
                continue

            # Handle special cases for unsupported ChromaDB operators
            if filter_op == FilterOperator.NE:
                # NOT $eq - ChromaDB doesn't support $ne directly
                conditions.append({"$not": {field: {"$eq": value}}})
            elif filter_op == FilterOperator.NIN:
                # NOT $in - ChromaDB doesn't support $nin directly
                conditions.append({"$not": {field: {"$in": value}}})
            else:
                conditions.append({field: {op: value}})

        if not conditions:
            return None

        if len(conditions) == 1:
            return conditions[0]

        return {"$and": conditions}

    @classmethod
    def _validate_field(cls, field: str) -> bool:
        """Validate if a field is supported for filtering.

        Args:
            field: Field name to validate.

        Returns:
            True if field is supported.
        """
        # Allow dynamic fields for flexibility
        return True

    @classmethod
    def validate_filters(cls, filters: Optional[dict[str, Any]]) -> tuple[bool, str]:
        """Validate filter structure.

        Args:
            filters: Filters to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if not filters:
            return True, ""

        try:
            # Try to build the filter to validate structure
            cls.build_chroma_filter(filters)
            return True, ""
        except Exception as e:
            return False, str(e)

    @classmethod
    def get_supported_fields(cls) -> list[str]:
        """Get list of supported filter fields.

        Returns:
            List of supported field names.
        """
        return sorted(cls.SUPPORTED_FIELDS)


# Module-level instance
metadata_filter = MetadataFilter()
