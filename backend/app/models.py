from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WardrobeItem(Base):
    __tablename__ = "wardrobe_items"

    id: Mapped[str] = mapped_column(String(4), primary_key=True)
    catalog_fields: Mapped[dict] = mapped_column(JSON, default=dict)
    user_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    visual_description: Mapped["VisualDescription | None"] = relationship(
        back_populates="item", cascade="all, delete-orphan", uselist=False
    )


class VisualDescription(Base):
    __tablename__ = "visual_descriptions"

    item_id: Mapped[str] = mapped_column(ForeignKey("wardrobe_items.id", ondelete="CASCADE"), primary_key=True)
    source_fields: Mapped[dict] = mapped_column(JSON, default=dict)
    item: Mapped[WardrobeItem] = relationship(back_populates="visual_description")


class Outfit(Base):
    __tablename__ = "outfits"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    season: Mapped[str] = mapped_column(String(120), default="")
    occasion: Mapped[str] = mapped_column(String(200), default="")
    item_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
