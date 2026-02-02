"""
Filter Builder Utility
Dynamic query filter construction for complex database queries.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional, TypeVar, Generic
from enum import Enum

from sqlalchemy import select, func, or_, and_, text
from sqlalchemy.sql import Select


class FilterOperator(str, Enum):
    """Supported filter operators."""
    EQ = "eq"           # Equal
    NE = "ne"           # Not equal
    GT = "gt"           # Greater than
    GTE = "gte"         # Greater than or equal
    LT = "lt"           # Less than
    LTE = "lte"         # Less than or equal
    IN = "in"           # In list
    NOT_IN = "not_in"   # Not in list
    LIKE = "like"       # LIKE pattern
    ILIKE = "ilike"     # Case-insensitive LIKE
    IS_NULL = "is_null" # IS NULL
    FTS = "fts"         # Full-text search


@dataclass
class FilterCondition:
    """A single filter condition."""
    field: str
    operator: FilterOperator
    value: Any


@dataclass
class SortOrder:
    """Sort order specification."""
    field: str
    desc: bool = True


@dataclass
class FilterSpec:
    """Complete filter specification."""
    conditions: List[FilterCondition] = field(default_factory=list)
    or_conditions: List[FilterCondition] = field(default_factory=list)
    sort: Optional[SortOrder] = None
    page: int = 1
    limit: int = 20
    
    def add_filter(
        self,
        field: str,
        operator: FilterOperator,
        value: Any,
        is_or: bool = False,
    ) -> "FilterSpec":
        """Add a filter condition."""
        condition = FilterCondition(field=field, operator=operator, value=value)
        if is_or:
            self.or_conditions.append(condition)
        else:
            self.conditions.append(condition)
        return self
    
    def eq(self, field: str, value: Any) -> "FilterSpec":
        """Add equality filter."""
        return self.add_filter(field, FilterOperator.EQ, value)
    
    def in_list(self, field: str, values: List[Any]) -> "FilterSpec":
        """Add IN filter."""
        return self.add_filter(field, FilterOperator.IN, values)
    
    def ilike(self, field: str, pattern: str) -> "FilterSpec":
        """Add case-insensitive LIKE filter."""
        return self.add_filter(field, FilterOperator.ILIKE, f"%{pattern}%")
    
    def between_dates(self, field: str, start: date, end: date) -> "FilterSpec":
        """Add date range filter."""
        self.add_filter(field, FilterOperator.GTE, start)
        self.add_filter(field, FilterOperator.LTE, end)
        return self
    
    def full_text_search(self, query: str) -> "FilterSpec":
        """Add full-text search filter."""
        return self.add_filter("search_vector", FilterOperator.FTS, query)
    
    def order_by(self, field: str, desc: bool = True) -> "FilterSpec":
        """Set sort order."""
        self.sort = SortOrder(field=field, desc=desc)
        return self
    
    def paginate(self, page: int, limit: int = 20) -> "FilterSpec":
        """Set pagination."""
        self.page = page
        self.limit = limit
        return self


class FilterBuilder:
    """
    Builds SQLAlchemy queries from FilterSpec.
    
    Usage:
        spec = FilterSpec()
        spec.eq("status", "applied").in_list("source", ["linkedin", "direct"])
        spec.full_text_search("google engineer")
        spec.order_by("applied_date", desc=True).paginate(page=1, limit=20)
        
        builder = FilterBuilder(Application)
        query, total = await builder.build_and_count(spec, db, user_id=user.id)
    """
    
    def __init__(self, model):
        self.model = model
    
    def _apply_condition(self, query: Select, condition: FilterCondition) -> Select:
        """Apply a single condition to the query."""
        column = getattr(self.model, condition.field, None)
        
        if column is None:
            # Handle special fields like search_vector
            if condition.field == "search_vector" and condition.operator == FilterOperator.FTS:
                # PostgreSQL full-text search
                search_query = func.plainto_tsquery('english', condition.value)
                return query.where(text(f"search_vector @@ plainto_tsquery('english', :q)").bindparams(q=condition.value))
            return query
        
        match condition.operator:
            case FilterOperator.EQ:
                return query.where(column == condition.value)
            case FilterOperator.NE:
                return query.where(column != condition.value)
            case FilterOperator.GT:
                return query.where(column > condition.value)
            case FilterOperator.GTE:
                return query.where(column >= condition.value)
            case FilterOperator.LT:
                return query.where(column < condition.value)
            case FilterOperator.LTE:
                return query.where(column <= condition.value)
            case FilterOperator.IN:
                return query.where(column.in_(condition.value))
            case FilterOperator.NOT_IN:
                return query.where(~column.in_(condition.value))
            case FilterOperator.LIKE:
                return query.where(column.like(condition.value))
            case FilterOperator.ILIKE:
                return query.where(column.ilike(condition.value))
            case FilterOperator.IS_NULL:
                if condition.value:
                    return query.where(column.is_(None))
                else:
                    return query.where(column.isnot(None))
            case _:
                return query
    
    def build(self, spec: FilterSpec, base_query: Optional[Select] = None) -> Select:
        """Build a query from the filter specification."""
        query = base_query if base_query is not None else select(self.model)
        
        # Apply soft delete filter if applicable
        if hasattr(self.model, 'deleted_at'):
            query = query.where(self.model.deleted_at.is_(None))
        
        # Apply AND conditions
        for condition in spec.conditions:
            query = self._apply_condition(query, condition)
        
        # Apply OR conditions
        if spec.or_conditions:
            or_filters = []
            for condition in spec.or_conditions:
                column = getattr(self.model, condition.field, None)
                if column is not None:
                    if condition.operator == FilterOperator.ILIKE:
                        or_filters.append(column.ilike(condition.value))
                    elif condition.operator == FilterOperator.EQ:
                        or_filters.append(column == condition.value)
            if or_filters:
                query = query.where(or_(*or_filters))
        
        # Apply sorting
        if spec.sort:
            sort_column = getattr(self.model, spec.sort.field, None)
            if sort_column is not None:
                query = query.order_by(
                    sort_column.desc() if spec.sort.desc else sort_column.asc()
                )
        
        # Apply pagination
        offset = (spec.page - 1) * spec.limit
        query = query.offset(offset).limit(spec.limit)
        
        return query
    
    def build_count(self, spec: FilterSpec) -> Select:
        """Build a count query from the filter specification."""
        query = select(func.count()).select_from(self.model)
        
        # Apply soft delete filter
        if hasattr(self.model, 'deleted_at'):
            query = query.where(self.model.deleted_at.is_(None))
        
        # Apply conditions (excluding pagination/sorting)
        for condition in spec.conditions:
            query = self._apply_condition(query, condition)
        
        return query


def parse_filter_params(
    status: Optional[str] = None,
    search: Optional[str] = None,
    source: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort: str = "-applied_date",
    page: int = 1,
    limit: int = 20,
) -> FilterSpec:
    """
    Parse common API query parameters into a FilterSpec.
    
    Usage:
        spec = parse_filter_params(
            status="applied,screening",
            search="google",
            sort="-applied_date",
            page=1
        )
    """
    spec = FilterSpec()
    
    # Status filter (comma-separated)
    if status:
        statuses = [s.strip() for s in status.split(",")]
        spec.in_list("status", statuses)
    
    # Full-text search
    if search:
        spec.full_text_search(search)
    
    # Source filter
    if source:
        spec.eq("source", source)
    
    # Date range
    if date_from:
        spec.add_filter("applied_date", FilterOperator.GTE, date_from)
    if date_to:
        spec.add_filter("applied_date", FilterOperator.LTE, date_to)
    
    # Sorting
    if sort.startswith("-"):
        spec.order_by(sort[1:], desc=True)
    else:
        spec.order_by(sort, desc=False)
    
    # Pagination
    spec.paginate(page, limit)
    
    return spec
