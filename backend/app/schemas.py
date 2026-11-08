from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VisualDescriptionOut(BaseModel):
    visual_description: str = ""
    critical_details: str = ""
    uncertainties: str = ""
    source_fields: dict[str, Any] = Field(default_factory=dict)


class ItemOut(BaseModel):
    id: str
    catalog_fields: dict[str, Any]
    user_notes: str = ""
    visual_description: VisualDescriptionOut | None = None
    local_image_path: str | None = None
    image_status: str = "missing_url"


class ItemUpdate(BaseModel):
    catalog_fields: dict[str, Any] | None = None
    user_notes: str | None = None


class OutfitBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    season: str = ""
    occasion: str = ""
    item_ids: list[str] = Field(default_factory=list)

    @field_validator("item_ids")
    @classmethod
    def unique_ids(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("item_ids must not contain duplicates")
        return value


class OutfitCreate(OutfitBase):
    pass


class OutfitUpdate(OutfitBase):
    pass


class OutfitOut(OutfitBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class ImportReport(BaseModel):
    catalog_added: int
    catalog_updated: int
    catalog_skipped: int
    visual_added: int
    visual_updated: int
    visual_skipped: int
    errors: list[str] = Field(default_factory=list)
