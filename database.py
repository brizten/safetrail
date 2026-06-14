from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from config import DATA_DIR, DB_PATH
from models import AlarmSettings, Checkpoint, EmergencyContact, HikePlan, SafetyProfile, now_iso


def _connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS safety_profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                user_name TEXT,
                phone TEXT,
                blood_group TEXT,
                allergies TEXT,
                chronic_diseases TEXT,
                hiking_experience TEXT,
                rescue_number TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS emergency_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                relation TEXT,
                note TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS hikes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                start_point TEXT NOT NULL,
                end_point TEXT NOT NULL,
                start_lat REAL,
                start_lon REAL,
                end_lat REAL,
                end_lon REAL,
                planned_start TEXT NOT NULL,
                planned_return TEXT NOT NULL,
                distance_km REAL,
                difficulty TEXT,
                participants_count INTEGER,
                weather_condition TEXT,
                has_overnight INTEGER,
                water_liters REAL,
                has_first_aid INTEGER,
                no_signal_zones INTEGER,
                route_deviation_km REAL,
                checkpoints_json TEXT,
                notes_json TEXT,
                alarm_settings_json TEXT,
                status TEXT,
                current_lat REAL,
                current_lon REAL,
                last_contact_at TEXT,
                actual_return_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hike_id INTEGER,
                incident_type TEXT NOT NULL,
                description TEXT,
                lat REAL,
                lon REAL,
                needs_help INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (hike_id) REFERENCES hikes(id)
            );
            """
        )


def save_profile(profile: SafetyProfile) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO safety_profile (
                id, user_name, phone, blood_group, allergies, chronic_diseases,
                hiking_experience, rescue_number, updated_at
            )
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                user_name = excluded.user_name,
                phone = excluded.phone,
                blood_group = excluded.blood_group,
                allergies = excluded.allergies,
                chronic_diseases = excluded.chronic_diseases,
                hiking_experience = excluded.hiking_experience,
                rescue_number = excluded.rescue_number,
                updated_at = excluded.updated_at
            """,
            (
                profile.user_name,
                profile.phone,
                profile.blood_group,
                profile.allergies,
                profile.chronic_diseases,
                profile.hiking_experience,
                profile.rescue_number,
                now_iso(),
            ),
        )


def get_profile() -> SafetyProfile | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM safety_profile WHERE id = 1").fetchone()
    if not row:
        return None
    return SafetyProfile(
        user_name=row["user_name"] or "",
        phone=row["phone"] or "",
        blood_group=row["blood_group"] or "",
        allergies=row["allergies"] or "",
        chronic_diseases=row["chronic_diseases"] or "",
        hiking_experience=row["hiking_experience"] or "начальный",
        rescue_number=row["rescue_number"] or "112",
    )


def add_contact(contact: EmergencyContact) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO emergency_contacts (name, phone, relation, note, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (contact.name, contact.phone, contact.relation, contact.note, now_iso()),
        )
        return int(cursor.lastrowid)


def delete_contact(contact_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM emergency_contacts WHERE id = ?", (contact_id,))


def list_contacts() -> list[EmergencyContact]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM emergency_contacts ORDER BY name").fetchall()
    return [
        EmergencyContact(
            id=row["id"],
            name=row["name"] or "",
            phone=row["phone"] or "",
            relation=row["relation"] or "",
            note=row["note"] or "",
        )
        for row in rows
    ]


def _hike_from_row(row: sqlite3.Row) -> HikePlan:
    checkpoints = [
        Checkpoint.from_dict(item)
        for item in _json_loads(row["checkpoints_json"], [])
        if isinstance(item, dict)
    ]
    return HikePlan(
        id=row["id"],
        title=row["title"] or "",
        start_point=row["start_point"] or "",
        end_point=row["end_point"] or "",
        start_lat=row["start_lat"],
        start_lon=row["start_lon"],
        end_lat=row["end_lat"],
        end_lon=row["end_lon"],
        planned_start=row["planned_start"] or "",
        planned_return=row["planned_return"] or "",
        distance_km=float(row["distance_km"] or 0),
        difficulty=row["difficulty"] or "средний",
        participants_count=int(row["participants_count"] or 1),
        weather_condition=row["weather_condition"] or "неизвестно",
        has_overnight=bool(row["has_overnight"]),
        water_liters=float(row["water_liters"] or 0),
        has_first_aid=bool(row["has_first_aid"]),
        no_signal_zones=bool(row["no_signal_zones"]),
        route_deviation_km=float(row["route_deviation_km"] or 0),
        checkpoints=checkpoints,
        notes=_json_loads(row["notes_json"], []),
        alarm_settings=AlarmSettings.from_dict(_json_loads(row["alarm_settings_json"], {})),
        status=row["status"] or "planned",
        current_lat=row["current_lat"],
        current_lon=row["current_lon"],
        last_contact_at=row["last_contact_at"],
        actual_return_at=row["actual_return_at"],
        created_at=row["created_at"] or now_iso(),
        updated_at=row["updated_at"] or now_iso(),
    )


def create_hike(hike: HikePlan) -> int:
    now = now_iso()
    hike.created_at = now
    hike.updated_at = now
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO hikes (
                title, start_point, end_point, start_lat, start_lon, end_lat, end_lon,
                planned_start, planned_return, distance_km, difficulty, participants_count,
                weather_condition, has_overnight, water_liters, has_first_aid,
                no_signal_zones, route_deviation_km, checkpoints_json, notes_json,
                alarm_settings_json, status, current_lat, current_lon, last_contact_at,
                actual_return_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _hike_values(hike),
        )
        return int(cursor.lastrowid)


def update_hike(hike: HikePlan) -> None:
    if hike.id is None:
        raise ValueError("Cannot update hike without id")
    hike.updated_at = now_iso()
    with _connect() as conn:
        conn.execute(
            """
            UPDATE hikes SET
                title = ?, start_point = ?, end_point = ?, start_lat = ?, start_lon = ?,
                end_lat = ?, end_lon = ?, planned_start = ?, planned_return = ?,
                distance_km = ?, difficulty = ?, participants_count = ?,
                weather_condition = ?, has_overnight = ?, water_liters = ?,
                has_first_aid = ?, no_signal_zones = ?, route_deviation_km = ?,
                checkpoints_json = ?, notes_json = ?, alarm_settings_json = ?,
                status = ?, current_lat = ?, current_lon = ?, last_contact_at = ?,
                actual_return_at = ?, created_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (*_hike_values(hike), hike.id),
        )


def _hike_values(hike: HikePlan) -> tuple[Any, ...]:
    return (
        hike.title,
        hike.start_point,
        hike.end_point,
        hike.start_lat,
        hike.start_lon,
        hike.end_lat,
        hike.end_lon,
        hike.planned_start,
        hike.planned_return,
        hike.distance_km,
        hike.difficulty,
        hike.participants_count,
        hike.weather_condition,
        int(hike.has_overnight),
        hike.water_liters,
        int(hike.has_first_aid),
        int(hike.no_signal_zones),
        hike.route_deviation_km,
        json.dumps([checkpoint.to_dict() for checkpoint in hike.checkpoints], ensure_ascii=False),
        json.dumps(hike.notes, ensure_ascii=False),
        json.dumps(hike.alarm_settings.to_dict(), ensure_ascii=False),
        hike.status,
        hike.current_lat,
        hike.current_lon,
        hike.last_contact_at,
        hike.actual_return_at,
        hike.created_at,
        hike.updated_at,
    )


def get_hike(hike_id: int) -> HikePlan | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM hikes WHERE id = ?", (hike_id,)).fetchone()
    return _hike_from_row(row) if row else None


def list_hikes() -> list[HikePlan]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM hikes ORDER BY planned_start DESC, id DESC").fetchall()
    return [_hike_from_row(row) for row in rows]


def mark_checkpoint(hike_id: int, checkpoint_index: int) -> None:
    hike = get_hike(hike_id)
    if not hike or checkpoint_index >= len(hike.checkpoints):
        return
    hike.checkpoints[checkpoint_index].checked_in = True
    hike.checkpoints[checkpoint_index].checked_in_at = now_iso()
    hike.last_contact_at = now_iso()
    if hike.status == "planned":
        hike.status = "active"
    update_hike(hike)


def create_incident(
    hike_id: int | None,
    incident_type: str,
    description: str,
    lat: float | None,
    lon: float | None,
    needs_help: bool = True,
) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO incidents (
                hike_id, incident_type, description, lat, lon, needs_help, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (hike_id, incident_type, description, lat, lon, int(needs_help), now_iso()),
        )
        return int(cursor.lastrowid)
