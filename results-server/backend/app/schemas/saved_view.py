"""SavedView Pydantic schemas."""

from datetime import datetime
from typing import Any, Optional

from app.db.models import SavedViewVisibility
from app.schemas.common import BaseSchema, TimestampMixin
from app.schemas.user import UserSummary


class SavedViewConfig(BaseSchema):
    """Configuration stored in a saved view."""

    # Filters
    filters: Optional[dict[str, Any]] = None

    # Display settings
    primary_fom_name: Optional[str] = None
    visible_columns: Optional[list[str]] = None

    # Chart settings
    chart_type: Optional[str] = None  # "line", "scatter", "bar"
    chart_x_axis: Optional[str] = None
    chart_y_axis: Optional[str] = None


class SavedViewBase(BaseSchema):
    """Base saved view schema."""

    name: str
    description: Optional[str] = None
    visibility: SavedViewVisibility = SavedViewVisibility.PRIVATE


class SavedViewCreate(SavedViewBase):
    """Schema for creating a saved view."""

    config: SavedViewConfig


class SavedViewUpdate(BaseSchema):
    """Schema for updating a saved view."""

    name: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[SavedViewVisibility] = None
    config: Optional[SavedViewConfig] = None


class SavedViewRead(SavedViewBase, TimestampMixin):
    """Schema for reading saved view data."""

    id: int
    owner_user_id: int
    config: SavedViewConfig


class SavedViewSummary(BaseSchema):
    """Summarized saved view for list views."""

    id: int
    name: str
    description: Optional[str] = None
    visibility: SavedViewVisibility
    owner: Optional[UserSummary] = None
    created_at: datetime
    updated_at: datetime


class SavedViewDetail(SavedViewRead):
    """Detailed saved view with owner info."""

    owner: Optional[UserSummary] = None

