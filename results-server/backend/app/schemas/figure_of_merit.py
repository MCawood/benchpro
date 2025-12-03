"""FigureOfMerit Pydantic schemas."""

from typing import Optional, Union

from pydantic import field_validator, model_validator

from app.db.models import FomValueType
from app.schemas.common import BaseSchema


class FigureOfMeritBase(BaseSchema):
    """Base FoM schema."""

    name: str
    unit: Optional[str] = None
    is_primary: bool = False


class FigureOfMeritCreate(FigureOfMeritBase):
    """Schema for creating a FoM.

    Either value_numeric or value_text should be provided.
    The value_type is inferred from which value is set.
    """

    value_numeric: Optional[float] = None
    value_text: Optional[str] = None

    @model_validator(mode="after")
    def validate_value(self) -> "FigureOfMeritCreate":
        """Ensure exactly one of value_numeric or value_text is set."""
        has_numeric = self.value_numeric is not None
        has_text = self.value_text is not None

        if not has_numeric and not has_text:
            raise ValueError("Either value_numeric or value_text must be provided")

        return self

    @property
    def value_type(self) -> FomValueType:
        """Infer value type from which value is set."""
        if self.value_numeric is not None:
            return FomValueType.NUMERIC
        return FomValueType.STRING


class FigureOfMeritRead(FigureOfMeritBase):
    """Schema for reading FoM data."""

    id: int
    task_run_id: int
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None
    value_type: FomValueType

    @property
    def value(self) -> Union[float, str, None]:
        """Get the actual value based on type."""
        if self.value_type == FomValueType.NUMERIC:
            return self.value_numeric
        return self.value_text


class FigureOfMeritSummary(BaseSchema):
    """Simplified FoM for embedding in task responses."""

    name: str
    value: Union[float, str, None]
    unit: Optional[str] = None
    value_type: FomValueType
    is_primary: bool = False

    @classmethod
    def from_read(cls, fom: FigureOfMeritRead) -> "FigureOfMeritSummary":
        """Create summary from full read schema."""
        value = fom.value_numeric if fom.value_type == FomValueType.NUMERIC else fom.value_text
        return cls(
            name=fom.name,
            value=value,
            unit=fom.unit,
            value_type=fom.value_type,
            is_primary=fom.is_primary,
        )

