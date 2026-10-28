import hashlib
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PHONE_CLEAN_REGEX = re.compile(r"[^\d+]")


class ContactInfo(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v_clean = v.strip().lower()
        if not EMAIL_REGEX.match(v_clean):
            raise ValueError(f"Invalid email format: {v}")
        return v_clean

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        cleaned = PHONE_CLEAN_REGEX.sub("", v.strip())
        digits_only = re.sub(r"\D", "", cleaned)
        if len(digits_only) < 7 or len(digits_only) > 15:
            raise ValueError(f"Invalid phone number length ({len(digits_only)} digits): {v}")
        return cleaned

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v_clean = v.strip()
        if not (v_clean.startswith("http://") or v_clean.startswith("https://")):
            v_clean = "https://" + v_clean
        return v_clean


class Address(BaseModel):
    street: Optional[str] = None
    city: str = Field(..., min_length=1)
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "US"

    @field_validator("city")
    @classmethod
    def clean_city(cls, v: str) -> str:
        return v.strip().title()


class CompanyRecord(BaseModel):
    company_id: Optional[str] = None
    name: str = Field(..., min_length=2)
    category: str = Field(default="Uncategorized")
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    review_count: int = Field(default=0, ge=0)
    contact: ContactInfo = Field(default_factory=ContactInfo)
    address: Address
    source_url: Optional[str] = None
    extracted_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    hash_fingerprint: Optional[str] = None

    @model_validator(mode="after")
    def compute_fingerprint_and_id(self) -> "CompanyRecord":
        normalized_name = re.sub(r"\W+", "", self.name.lower())
        normalized_city = re.sub(r"\W+", "", self.address.city.lower())
        domain = ""
        if self.contact.website:
            domain_match = re.search(r"https?://(?:www\.)?([^/]+)", self.contact.website)
            if domain_match:
                domain = domain_match.group(1).lower()

        # Composite deduplication key
        key_raw = f"{normalized_name}:{normalized_city}:{domain}"
        fingerprint = hashlib.sha256(key_raw.encode("utf-8")).hexdigest()[:16]
        
        if not self.hash_fingerprint:
            self.hash_fingerprint = fingerprint
        if not self.company_id:
            self.company_id = f"cmp_{fingerprint}"
        return self


class QuarantineRecord(BaseModel):
    raw_data: Dict[str, Any]
    error_reasons: List[str]
    source: str
    quarantined_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class HarvestReport(BaseModel):
    total_scraped: int = 0
    valid_records: int = 0
    quarantined_records: int = 0
    duplicates_skipped: int = 0
    duration_seconds: float = 0.0
