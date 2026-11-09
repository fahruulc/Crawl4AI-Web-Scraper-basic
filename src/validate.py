from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, Field, field_validator


class ProductRecord(BaseModel):
    target: str = Field(..., min_length=1)
    source_url: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    price: float = Field(..., ge=0.0)
    stock: str = Field(default="")
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, v: Any) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Product name cannot be empty")
        return v.strip()

    @field_validator("price", mode="before")
    @classmethod
    def clean_price(cls, v: Any) -> float:
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            # Extract number with optional decimals, e.g. £51.77 or $1,234.56
            cleaned = v.replace(",", "").strip()
            match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
            if match:
                return float(match.group(1))
        raise ValueError(f"Unable to parse price from: {v!r}")

    @field_validator("stock", mode="before")
    @classmethod
    def clean_stock(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v).strip()


def validate_product(
    raw_data: Dict[str, Any],
    target: str,
    source_url: str
) -> Tuple[Optional[ProductRecord], Optional[str]]:
    """
    Validate a single product dictionary.
    Returns (record, None) if valid, or (None, error_message) if invalid.
    """
    try:
        record = ProductRecord(
            target=target,
            source_url=source_url,
            name=raw_data.get("name", ""),
            price=raw_data.get("price"),
            stock=raw_data.get("stock", ""),
        )
        return record, None
    except Exception as exc:
        return None, str(exc)


def validate_generic(
    raw_data: Dict[str, Any],
    target: str,
    source_url: str
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Validate a generic/dynamic record from scraping.
    Cleans strings, removes None, and ensures at least one field has non-empty content.
    Returns (cleaned_dict, None) if valid, or (None, error_message) if invalid.
    """
    if not isinstance(raw_data, dict) or not raw_data:
        return None, "Empty or invalid record dictionary"

    cleaned: Dict[str, Any] = {}
    has_content = False

    for k, v in raw_data.items():
        if v is None:
            continue
        if isinstance(v, str):
            clean_v = v.strip()
            if clean_v:
                has_content = True
            cleaned[k] = clean_v
        else:
            has_content = True
            cleaned[k] = v

    if not has_content:
        return None, "All fields in scraped record are empty"

    return cleaned, None

