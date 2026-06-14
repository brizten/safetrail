from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from config import DEFAULT_RESCUE_NUMBER


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


@dataclass
class EmergencyContact:
    id: int | None = None
    name: str = ""
    phone: str = ""
    relation: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EmergencyContact":
        return cls(**{key: data.get(key) for key in cls.__dataclass_fields__})


@dataclass
class SafetyProfile:
    user_name: str = ""
    phone: str = ""
    blood_group: str = ""
    allergies: str = ""
    chronic_diseases: str = ""
    hiking_experience: str = "начальный"
    rescue_number: str = DEFAULT_RESCUE_NUMBER

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Checkpoint:
    name: str = ""
    planned_time: str = ""
    lat: float | None = None
    lon: float | None = None
    checked_in: bool = False
    checked_in_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Checkpoint":
        return cls(
            name=data.get("name", ""),
            planned_time=data.get("planned_time", ""),
            lat=data.get("lat"),
            lon=data.get("lon"),
            checked_in=bool(data.get("checked_in", False)),
            checked_in_at=data.get("checked_in_at"),
        )


@dataclass
class AlarmSettings:
    checkpoint_late_enabled: bool = True
    hike_return_late_enabled: bool = True
    no_contact_enabled: bool = True
    route_deviation_enabled: bool = True
    manual_incident_enabled: bool = True
    checkpoint_grace_minutes: int = 45
    return_grace_minutes: int = 60
    max_silence_hours: int = 6
    route_deviation_km_threshold: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AlarmSettings":
        if not data:
            return cls()
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{key: data.get(key) for key in allowed if key in data})


@dataclass
class HikePlan:
    id: int | None = None
    title: str = ""
    start_point: str = ""
    end_point: str = ""
    start_lat: float | None = None
    start_lon: float | None = None
    end_lat: float | None = None
    end_lon: float | None = None
    planned_start: str = ""
    planned_return: str = ""
    distance_km: float = 0.0
    difficulty: str = "средний"
    participants_count: int = 1
    weather_condition: str = "неизвестно"
    has_overnight: bool = False
    water_liters: float = 0.0
    has_first_aid: bool = True
    no_signal_zones: bool = False
    route_deviation_km: float = 0.0
    checkpoints: list[Checkpoint] = field(default_factory=list)
    notes: list[dict[str, str]] = field(default_factory=list)
    alarm_settings: AlarmSettings = field(default_factory=AlarmSettings)
    status: str = "planned"
    current_lat: float | None = None
    current_lon: float | None = None
    last_contact_at: str | None = None
    actual_return_at: str | None = None
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["checkpoints"] = [checkpoint.to_dict() for checkpoint in self.checkpoints]
        data["alarm_settings"] = self.alarm_settings.to_dict()
        return data

    def last_checkpoint_name(self) -> str:
        checked = [checkpoint for checkpoint in self.checkpoints if checkpoint.checked_in]
        if checked:
            return checked[-1].name
        return "нет отмеченных контрольных точек"
