"""Validated contracts shared by collectors, the API, and Spark sinks."""
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pycountry
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

Degree = Literal["bachelor", "master", "phd", "postdoc", "research", "other"]
Funding = Literal["full", "partial", "tuition", "stipend", "unknown"]
STORAGE_FIELDS = {"added_at", "updated_at", "first_streamed_at", "last_event_id", "last_observed_at", "ingestion_mode"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def country_code(value: str) -> str:
    code = value.upper().strip()
    if not pycountry.countries.get(alpha_2=code):
        raise ValueError("رمز الدولة غير صالح")
    return code


def web_url(value: str | None) -> str | None:
    if value is not None:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username:
            raise ValueError("يلزم رابط ويب عام صالح")
    return value


class Placement(BaseModel):
    id: str
    name: str
    country: str
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lon: float = Field(ge=-180, le=180, allow_inf_nan=False)
    precision: Literal["campus", "city", "country"]
    source_url: str
    _country = field_validator("country")(country_code)
    _source = field_validator("source_url")(web_url)


class Scholarship(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=150)
    source_id: str = Field(min_length=1, max_length=60)
    source_record_id: str = Field(min_length=1, max_length=150)
    title: str = Field(min_length=1, max_length=700)
    title_ar: str | None = None
    provider: str = ""
    source_url: str
    official_url: str | None = None
    cycle: str | None = None
    countries: list[str] = Field(default_factory=list)
    degrees: list[Degree] = Field(default_factory=list)
    fields: list[str] = Field(default_factory=list)
    funding: Funding = "unknown"
    description: str = ""
    eligibility_text: str = ""
    nationalities: list[str] = Field(default_factory=list)
    excluded_nationalities: list[str] = Field(default_factory=list)
    minimum_gpa: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    gpa_scale: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    extra_requirements: list[str] = Field(default_factory=list)
    deadline: str | None = None
    deadline_text: str = ""
    deadline_timezone: str | None = None
    deadline_confidence: Literal["confirmed", "estimated", "recurring", "unknown"] = "unknown"
    opens_at: str | None = None
    reported_status: Literal["open", "upcoming", "closed", "unknown"] = "unknown"
    open_evidence: Literal["accepting_applications", "date_window", "rolling"] | None = None
    official_verified_at: AwareDatetime | None = None
    verification_note: str = ""
    fetched_at: AwareDatetime = Field(default_factory=utcnow)
    source_checked_at: AwareDatetime | None = None
    placements: list[Placement] = Field(default_factory=list)
    identity_resolved: bool = False
    added_at: AwareDatetime | None = None
    updated_at: AwareDatetime | None = None
    first_streamed_at: AwareDatetime | None = None
    last_event_id: str | None = None
    last_observed_at: AwareDatetime | None = None
    ingestion_mode: Literal["live", "import", "replay", "test"] | None = None

    _urls = field_validator("source_url", "official_url")(web_url)

    @field_validator("deadline_timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ZoneInfo(value)
            except (ZoneInfoNotFoundError, ValueError) as error:
                raise ValueError("المنطقة الزمنية غير صالحة") from error
        return value

    @field_validator("countries", "excluded_nationalities")
    @classmethod
    def validate_countries(cls, values: list[str]) -> list[str]:
        return sorted(set(country_code(value) for value in values))

    @field_validator("nationalities")
    @classmethod
    def validate_nationalities(cls, values: list[str]) -> list[str]:
        return sorted(set("*" if value == "*" else country_code(value) for value in values))

    @field_validator("deadline", "opens_at")
    @classmethod
    def validate_date(cls, value: str | None) -> str | None:
        if value:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    @model_validator(mode="after")
    def validate_grade(self):
        if self.minimum_gpa is not None and (not self.gpa_scale or self.minimum_gpa > self.gpa_scale):
            raise ValueError("حد المعدل يحتاج مقياسًا صالحًا")
        return self


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nationality: str
    gpa: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    gpa_scale: float = Field(default=100, gt=0, le=1000, allow_inf_nan=False)
    field: str = Field(min_length=1, max_length=100)
    degree: Degree
    preferred_countries: list[str] = Field(default_factory=list, max_length=30)
    _country = field_validator("nationality")(country_code)

    @field_validator("preferred_countries")
    @classmethod
    def validate_preferences(cls, values: list[str]) -> list[str]:
        return sorted(set(country_code(value) for value in values))

    @model_validator(mode="after")
    def validate_gpa(self):
        if self.gpa is not None and self.gpa > self.gpa_scale:
            raise ValueError("المعدل لا يمكن أن يتجاوز مقياسه")
        return self


class MatchResult(BaseModel):
    compatible: bool
    status: Literal["matched", "potential", "excluded"]
    score: float
    reasons: list[str]
    uncertainties: list[str]
    excluded_reasons: list[str]


class ObservationEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    event_id: str = Field(min_length=16, max_length=128)
    source_id: str
    source_record_id: str
    event_type: Literal["discovered", "updated", "closed"]
    observed_at: AwareDatetime
    content_hash: str
    mode: Literal["live", "import", "replay", "test"] = "live"
    run_id: str | None = None
    scholarship: Scholarship

    @model_validator(mode="after")
    def consistent_source(self):
        if (self.source_id, self.source_record_id) != (
            self.scholarship.source_id, self.scholarship.source_record_id
        ):
            raise ValueError("Event source does not match scholarship source")
        return self
