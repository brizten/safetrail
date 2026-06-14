from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from models import HikePlan, SafetyProfile, parse_datetime


BAD_WEATHER_WORDS = {
    "гроза",
    "ливень",
    "снег",
    "метель",
    "туман",
    "шторм",
    "ветер",
    "мороз",
    "жара",
}


def assess_risk(hike: HikePlan, profile: SafetyProfile | None = None) -> dict[str, Any]:
    score = 0
    factors: list[str] = []
    recommendations: list[str] = []

    def add(points: int, factor: str, recommendation: str) -> None:
        nonlocal score
        score += points
        factors.append(factor)
        recommendations.append(recommendation)

    if hike.participants_count <= 1:
        add(2, "Одиночный поход", "Оставьте маршрут и контрольные времена доверенному контакту.")

    if hike.difficulty == "средний":
        add(1, "Средняя сложность маршрута", "Проверьте запас времени и навигационные точки.")
    elif hike.difficulty == "сложный":
        add(2, "Сложный маршрут", "Добавьте запасной план схода с маршрута.")
    elif hike.difficulty == "экстремальный":
        add(4, "Экстремальный маршрут", "Не выходите без опытной группы, связи и аварийного маяка.")

    if hike.has_overnight:
        add(2, "Планируется ночёвка", "Проверьте укрытие, теплоизоляцию, фонарь и ночной план безопасности.")

    if hike.no_signal_zones:
        add(2, "Есть зоны без связи", "Назначьте контрольные окна связи и продумайте спутниковый канал.")

    weather = hike.weather_condition.lower()
    if any(word in weather for word in BAD_WEATHER_WORDS):
        add(2, "Неблагоприятная погода", "Сверьте прогноз перед выходом и подготовьте вариант отмены.")

    expected_water = _expected_water_liters(hike)
    if hike.water_liters < expected_water:
        add(
            2,
            "Запас воды ниже базовой нормы",
            f"Запланируйте минимум {expected_water:.1f} л воды или надёжные источники пополнения.",
        )

    if not hike.has_first_aid:
        add(2, "Не отмечена аптечка", "Добавьте аптечку и индивидуальные лекарства.")

    experience = (profile.hiking_experience if profile else "").lower()
    if not profile or experience in {"", "нет опыта", "начальный"}:
        add(2, "Недостаточный опыт", "Выберите простой маршрут или идите с опытным напарником.")

    if not hike.checkpoints:
        add(2, "Нет контрольных точек", "Добавьте контрольные точки с ожидаемым временем прибытия.")

    planned_return = parse_datetime(hike.planned_return)
    if planned_return and (planned_return.hour >= 22 or planned_return.hour < 6):
        add(1, "Позднее время возвращения", "Заложите финиш до темноты или подготовьте ночной выход.")

    level = _score_to_level(score)
    return {
        "score": score,
        "level": level,
        "factors": factors,
        "recommendations": _dedupe(recommendations),
    }


def evaluate_alerts(hike: HikePlan, now: datetime | None = None) -> list[dict[str, str]]:
    now = now or datetime.now()
    alerts: list[dict[str, str]] = []
    settings = hike.alarm_settings

    if hike.status == "completed":
        return alerts

    if settings.checkpoint_late_enabled:
        for checkpoint in hike.checkpoints:
            planned = parse_datetime(checkpoint.planned_time)
            if checkpoint.checked_in or not planned:
                continue
            deadline = planned + timedelta(minutes=settings.checkpoint_grace_minutes)
            if now > deadline:
                alerts.append(
                    {
                        "severity": "high",
                        "title": "Контрольная точка просрочена",
                        "message": f"Не отмечена точка «{checkpoint.name}» после {deadline:%d.%m.%Y %H:%M}.",
                    }
                )
                break

    if settings.hike_return_late_enabled:
        planned_return = parse_datetime(hike.planned_return)
        if planned_return and now > planned_return + timedelta(minutes=settings.return_grace_minutes):
            alerts.append(
                {
                    "severity": "critical",
                    "title": "Поход не завершён вовремя",
                    "message": "Плановое время возвращения истекло с учётом допустимой задержки.",
                }
            )

    if settings.no_contact_enabled:
        last_contact = parse_datetime(hike.last_contact_at or hike.planned_start)
        if last_contact and now > last_contact + timedelta(hours=settings.max_silence_hours):
            alerts.append(
                {
                    "severity": "high",
                    "title": "Долго нет связи",
                    "message": f"Последний контакт был {last_contact:%d.%m.%Y %H:%M}.",
                }
            )

    if (
        settings.route_deviation_enabled
        and hike.route_deviation_km > settings.route_deviation_km_threshold
    ):
        alerts.append(
            {
                "severity": "high",
                "title": "Отклонение от маршрута",
                "message": (
                    f"Отклонение {hike.route_deviation_km:.1f} км превышает порог "
                    f"{settings.route_deviation_km_threshold:.1f} км."
                ),
            }
        )

    return alerts


def risk_color(level: str) -> str:
    return {
        "низкий": "green",
        "средний": "orange",
        "высокий": "red",
        "критический": "violet",
    }.get(level, "gray")


def _score_to_level(score: int) -> str:
    if score <= 3:
        return "низкий"
    if score <= 7:
        return "средний"
    if score <= 12:
        return "высокий"
    return "критический"


def _expected_water_liters(hike: HikePlan) -> float:
    start = parse_datetime(hike.planned_start)
    end = parse_datetime(hike.planned_return)
    participants = max(hike.participants_count, 1)
    if not start or not end or end <= start:
        days = 1.0
    else:
        days = max((end - start).total_seconds() / 86400, 0.5)
    weather_bonus = 1.3 if any(word in hike.weather_condition.lower() for word in {"жара", "ветер"}) else 1.0
    return participants * days * 2.0 * weather_bonus


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
