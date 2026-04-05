from enum import StrEnum


class RepeatFrequency(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    OCCASIONAL = "occasional"
    ONE_OFF = "one_off"


class FitLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CandidateStatus(StrEnum):
    GENERATED = "generated"
    CLUSTERED = "clustered"
    SCORED = "scored"
    REPORTED = "reported"
