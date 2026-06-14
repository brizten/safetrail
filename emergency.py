from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

from checklist import SOS_INSTRUCTIONS
from config import DEFAULT_RESCUE_NUMBER
from models import HikePlan, SafetyProfile


def format_coordinates(lat: float | None, lon: float | None) -> str:
    if lat is None or lon is None:
        return "координаты не указаны"
    return f"{lat:.6f}, {lon:.6f}"


def generate_sos_message(
    profile: SafetyProfile | None,
    hike: HikePlan | None,
    lat: float | None,
    lon: float | None,
    incident_type: str = "",
    extra_description: str = "",
) -> str:
    generated_at = datetime.now().strftime("%d.%m.%Y %H:%M")
    coords = format_coordinates(lat, lon)
    maps_link = f"https://maps.google.com/?q={lat},{lon}" if lat is not None and lon is not None else ""

    name = profile.user_name if profile and profile.user_name else "не указано"
    phone = profile.phone if profile and profile.phone else "не указано"
    blood = profile.blood_group if profile and profile.blood_group else "не указано"
    allergies = profile.allergies if profile and profile.allergies else "не указано"
    chronic = profile.chronic_diseases if profile and profile.chronic_diseases else "не указано"

    route = "маршрут не выбран"
    last_checkpoint = "не указана"
    planned_return = "не указано"
    last_contact = "не указано"
    if hike:
        route = f"{hike.title}: {hike.start_point} -> {hike.end_point}"
        last_checkpoint = hike.last_checkpoint_name()
        planned_return = hike.planned_return or "не указано"
        last_contact = hike.last_contact_at or "не указано"

    lines = [
        "Я в походе, возможно, мне нужна помощь.",
        f"Координаты: {coords}",
        f"Ссылка на карту: {maps_link or 'нет'}",
        f"Маршрут: {route}",
        f"Последняя контрольная точка: {last_checkpoint}",
        f"Последний контакт: {last_contact}",
        f"Плановое возвращение: {planned_return}",
        f"Тип проблемы: {incident_type or 'SOS'}",
        f"Описание: {extra_description or 'нет дополнительного описания'}",
        f"Сообщение сформировано: {generated_at}",
        "",
        f"Данные пользователя: {name}, телефон {phone}",
        f"Группа крови: {blood}",
        f"Аллергии: {allergies}",
        f"Хронические болезни: {chronic}",
    ]
    return "\n".join(lines)


def build_sms_link(phone: str, message: str) -> str:
    clean_phone = phone.strip().replace(" ", "")
    return f"sms:{clean_phone}?body={quote(message)}"


def build_tel_link(number: str | None) -> str:
    return f"tel:{number or DEFAULT_RESCUE_NUMBER}"


def compact_sos_instructions() -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(SOS_INSTRUCTIONS, start=1))
