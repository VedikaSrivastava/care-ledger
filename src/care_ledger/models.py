from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import date, time
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, PlainSerializer, WithJsonSchema, model_validator

_CLOCK = re.compile(r"^\d{2}:\d{2}$")


def _local_clock(value: object) -> time:
    """Require one local minute-precision clock; never discard offsets or seconds."""
    if isinstance(value, time):
        if value.tzinfo is not None or value.second or value.microsecond:
            raise ValueError("expected a naive minute-precision local clock")
        return value
    if isinstance(value, str) and _CLOCK.fullmatch(value):
        return time.fromisoformat(value)
    raise ValueError(f"expected HH:MM local clock time, got {value!r}")


Clock = Annotated[time, BeforeValidator(_local_clock),
                  PlainSerializer(lambda v: v.isoformat(timespec="minutes"), return_type=str),
                  WithJsonSchema({"type": "string", "pattern": r"^([01][0-9]|2[0-3]):[0-5][0-9]$"})]


class ServiceType(StrEnum):
    INDIVIDUAL_THERAPY = "individual_therapy"
    GROUP_THERAPY = "group_therapy"
    FAMILY_THERAPY = "family_therapy"
    MEDICATION_MANAGEMENT = "medication_management"
    COLLATERAL_CONTACT = "collateral_contact"
    CARE_COORDINATION = "care_coordination"
    OTHER = "other"


THERAPY_SERVICES = frozenset(
    {ServiceType.INDIVIDUAL_THERAPY, ServiceType.GROUP_THERAPY, ServiceType.FAMILY_THERAPY}
)


class Attendance(StrEnum):
    ATTENDED = "attended"
    NO_SHOW = "no_show"
    CANCELLED_BY_PATIENT = "cancelled_by_patient"
    CANCELLED_BY_CLINIC = "cancelled_by_clinic"
    PATIENT_ABSENT = "patient_absent"


class SourceStatus(StrEnum):
    FINAL = "final"
    DRAFT = "draft"


class CorrectedField(StrEnum):
    PRESENCE_START = "presence_start"
    PRESENCE_END = "presence_end"


class ObservationCategory(StrEnum):
    SYMPTOM = "symptom"
    FUNCTIONING = "functioning"
    SAFETY = "safety"
    VISIT_REASON = "visit_reason"
    CLINICAL_ASSESSMENT = "clinical_assessment"


class Reporter(StrEnum):
    PATIENT = "patient"
    CLINICIAN = "clinician"
    COLLATERAL = "collateral"


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_quotes: list[str]

    @model_validator(mode="after")
    def _has_evidence(self):
        if not self.evidence_quotes or any(not q.strip() for q in self.evidence_quotes):
            raise ValueError(f"{type(self).__name__} requires non-empty evidence quotes")
        return self


class Patient(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mrn: str
    name: str
    birth_date: date | None


class AttendanceClaim(Claim):
    status: Attendance


class Interval(Claim):
    start: Clock
    end: Clock

    @model_validator(mode="after")
    def _ordered(self):
        if self.end <= self.start:
            raise ValueError(f"interval end {self.end} must follow start {self.start}")
        return self


class Charge(Claim):
    charge_id: str


class EncounterSection(Claim):
    """Claims about one encounter from one section of a document; evidence_quotes support the identity, date and type."""

    encounter_id: str
    service_date: date
    service_type: ServiceType
    source_status: SourceStatus
    authored_on: date
    attendance: AttendanceClaim | None
    patient_presence: list[Interval]
    breaks: list[Interval]
    charges: list[Charge]


class Correction(Claim):
    encounter_id: str
    service_date: date
    field: CorrectedField
    replaced_time: Clock
    replacement_time: Clock
    source_status: SourceStatus
    authored_on: date

    @model_validator(mode="after")
    def _changes_value(self):
        if self.replaced_time == self.replacement_time:
            raise ValueError("a correction must change the recorded time")
        return self


class AssessmentResult(Claim):
    instrument: str
    completed_on: date
    form_id: str | None
    score: int
    source_status: SourceStatus
    authored_on: date


class Observation(Claim):
    encounter_id: str | None
    category: ObservationCategory
    reporter: Reporter
    statement: str
    source_status: SourceStatus
    authored_on: date


class PlanRequirement(Claim):
    effective_start: date
    effective_end: date
    min_therapy_days_per_week: int
    min_therapy_minutes_per_week: int
    eligible_service_types: list[ServiceType]


class ExtractionEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient: Patient
    encounters: list[EncounterSection]
    corrections: list[Correction]
    assessments: list[AssessmentResult]
    observations: list[Observation]
    plans: list[PlanRequirement]

    def claims(self) -> Iterator[Claim]:
        for section in self.encounters:
            yield section
            if section.attendance:
                yield section.attendance
            yield from section.patient_presence
            yield from section.breaks
            yield from section.charges
        yield from self.corrections
        yield from self.assessments
        yield from self.observations
        yield from self.plans
