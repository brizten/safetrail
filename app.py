from __future__ import annotations

from datetime import date, datetime, time, timedelta

import pandas as pd
import requests
import streamlit as st

from checklist import CHECKLISTS, SOS_INSTRUCTIONS
from config import (
    APP_DESCRIPTION,
    APP_NAME,
    DISCLAIMER,
    DIFFICULTY_OPTIONS,
    EXPERIENCE_OPTIONS,
    OPEN_METEO_URL,
    PRIVACY_NOTICE,
    WEATHER_OPTIONS,
)
from database import (
    add_contact,
    create_hike,
    create_incident,
    delete_contact,
    get_profile,
    init_db,
    list_contacts,
    list_hikes,
    mark_checkpoint,
    save_profile,
    update_hike,
)
from emergency import build_sms_link, build_tel_link, generate_sos_message
from models import AlarmSettings, Checkpoint, EmergencyContact, HikePlan, SafetyProfile, now_iso, parse_datetime
from safety import assess_risk, evaluate_alerts, risk_color

try:
    import folium
    from streamlit_folium import st_folium
except ImportError:
    folium = None
    st_folium = None


NAV_ITEMS = [
    "Главная",
    "Создание похода",
    "Карта маршрута",
    "Чек-листы",
    "Оценка риска",
    "SOS-режим",
    "История походов",
    "Настройки контактов",
]

RISK_STYLE = {
    "низкий": ("#1f7a4d", "#e8f6ee"),
    "средний": ("#a15c00", "#fff4df"),
    "высокий": ("#b42318", "#fde8e7"),
    "критический": ("#7c2d12", "#ffe7d6"),
}


def main() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon="⛰️", layout="wide")
    apply_theme()
    init_db()

    st.sidebar.title(APP_NAME)
    st.sidebar.caption(APP_DESCRIPTION)
    st.sidebar.markdown(
        "<div class='sidebar-card'>Планируйте маршрут, держите контрольные точки под рукой "
        "и заранее готовьте тревожный сценарий.</div>",
        unsafe_allow_html=True,
    )
    page = st.sidebar.radio("Раздел", NAV_ITEMS)

    if page == "Главная":
        page_home()
    elif page == "Создание похода":
        page_create_hike()
    elif page == "Карта маршрута":
        page_route_map()
    elif page == "Чек-листы":
        page_checklists()
    elif page == "Оценка риска":
        page_risk()
    elif page == "SOS-режим":
        page_sos()
    elif page == "История походов":
        page_history()
    elif page == "Настройки контактов":
        page_settings()


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ts-bg: #f7f8f3;
            --ts-panel: #ffffff;
            --ts-ink: #172026;
            --ts-muted: #5f6b63;
            --ts-line: #e3ded4;
            --ts-green: #1f7a4d;
            --ts-amber: #b66a00;
            --ts-red: #b42318;
        }
        .stApp {
            background: var(--ts-bg);
            color: var(--ts-ink);
        }
        .block-container {
            max-width: 1180px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        [data-testid="stSidebar"] {
            background: #fbfaf6;
            border-right: 1px solid var(--ts-line);
        }
        [data-testid="stSidebar"] h1 {
            font-size: 1.45rem;
            margin-bottom: .25rem;
        }
        .sidebar-card {
            border: 1px solid var(--ts-line);
            border-radius: 8px;
            padding: .8rem .9rem;
            margin: .75rem 0 1rem;
            background: #ffffff;
            color: var(--ts-muted);
            font-size: .92rem;
            line-height: 1.35;
        }
        .ts-hero {
            border: 1px solid var(--ts-line);
            border-radius: 8px;
            padding: 1.25rem 1.35rem;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, #ffffff 0%, #eef7f1 52%, #fff4df 100%);
        }
        .ts-hero-eyebrow {
            color: var(--ts-green);
            font-weight: 700;
            text-transform: uppercase;
            font-size: .74rem;
            letter-spacing: 0;
            margin-bottom: .3rem;
        }
        .ts-hero h1 {
            margin: 0 0 .35rem;
            font-size: clamp(1.65rem, 2.5vw, 2.25rem);
            line-height: 1.12;
        }
        .ts-hero p {
            max-width: 780px;
            margin: 0;
            color: var(--ts-muted);
            font-size: 1rem;
        }
        .ts-section {
            margin: 1.25rem 0 .6rem;
        }
        .ts-section h2 {
            font-size: 1.08rem;
            margin: 0;
        }
        .ts-section p {
            margin: .2rem 0 0;
            color: var(--ts-muted);
            font-size: .92rem;
        }
        .ts-notice {
            border: 1px solid var(--ts-line);
            border-left-width: 5px;
            border-radius: 8px;
            padding: .85rem 1rem;
            margin: .7rem 0;
            background: var(--ts-panel);
        }
        .ts-notice strong {
            display: block;
            margin-bottom: .2rem;
        }
        .ts-notice p {
            margin: 0;
            color: var(--ts-muted);
        }
        .ts-notice.info { border-left-color: var(--ts-green); }
        .ts-notice.warning { border-left-color: var(--ts-amber); }
        .ts-notice.danger { border-left-color: var(--ts-red); }
        .ts-risk-pill {
            display: inline-flex;
            align-items: center;
            gap: .45rem;
            border-radius: 999px;
            padding: .36rem .7rem;
            font-size: .88rem;
            font-weight: 700;
            margin: .25rem 0 .65rem;
        }
        [data-testid="stMetric"] {
            background: var(--ts-panel);
            border: 1px solid var(--ts-line);
            border-radius: 8px;
            padding: .85rem 1rem;
        }
        div[data-testid="stExpander"] {
            border: 1px solid var(--ts-line);
            border-radius: 8px;
            background: var(--ts-panel);
        }
        .stButton button, .stFormSubmitButton button {
            border-radius: 8px;
            border: 1px solid #cfd8cf;
            min-height: 2.45rem;
            font-weight: 650;
        }
        .stButton button:hover, .stFormSubmitButton button:hover {
            border-color: var(--ts-green);
            color: var(--ts-green);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str, eyebrow: str) -> None:
    st.markdown(
        f"""
        <section class="ts-hero">
            <div class="ts-hero-eyebrow">{eyebrow}</div>
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def section_title(title: str, subtitle: str | None = None) -> None:
    subtitle_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="ts-section">
            <h2>{title}</h2>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def notice(title: str, body: str, tone: str = "info") -> None:
    st.markdown(
        f"""
        <div class="ts-notice {tone}">
            <strong>{title}</strong>
            <p>{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def risk_badge(level: str, score: int) -> None:
    color, background = RISK_STYLE.get(level, ("#5f6b63", "#f0f2ef"))
    st.markdown(
        f"""
        <div class="ts-risk-pill" style="color:{color}; background:{background};">
            Риск: {level} · {score} баллов
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_home() -> None:
    page_header(
        "Панель походов",
        "Короткий обзор маршрутов, рисков, связи и готовности к экстренным ситуациям.",
        "локальный MVP",
    )
    notice("Важно", DISCLAIMER, tone="warning")
    notice("Приватность", PRIVACY_NOTICE, tone="info")

    profile = get_profile()
    contacts = list_contacts()
    hikes = list_hikes()
    active_hikes = [hike for hike in hikes if hike.status != "completed"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Походов в базе", len(hikes))
    col2.metric("Активных/планируемых", len(active_hikes))
    col3.metric("Экстренных контактов", len(contacts))

    if not profile:
        st.warning("Заполните профиль безопасности в разделе «Настройки контактов».")
    if not contacts:
        st.warning("Добавьте хотя бы один экстренный контакт.")

    section_title("Ближайшие походы", "Активные и запланированные маршруты с быстрыми действиями.")
    if not active_hikes:
        st.write("Пока нет активных или запланированных походов.")
        return

    for hike in active_hikes[:5]:
        assessment = assess_risk(hike, profile)
        alerts = evaluate_alerts(hike)
        with st.expander(f"#{hike.id} · {hike.title} · риск: {assessment['level']}"):
            col_a, col_b, col_c = st.columns(3)
            col_a.write(f"**Маршрут:** {hike.start_point} -> {hike.end_point}")
            col_b.write(f"**Статус:** {hike.status}")
            col_c.write(f"**Возвращение:** {_format_dt(hike.planned_return)}")
            risk_badge(assessment["level"], assessment["score"])
            if alerts:
                for alert in alerts:
                    st.error(f"{alert['title']}: {alert['message']}")
            else:
                st.success("Критических условий тревоги сейчас нет.")
            _hike_quick_actions(hike, prefix="home")


def page_create_hike() -> None:
    page_header(
        "Создание похода",
        "Соберите маршрут, контрольные окна связи и условия тревоги в одном понятном плане.",
        "планирование",
    )

    with st.expander("Опционально: получить краткую погоду по координатам старта"):
        weather_lat = st.text_input("Широта старта для прогноза", key="weather_lat")
        weather_lon = st.text_input("Долгота старта для прогноза", key="weather_lon")
        if st.button("Получить погоду Open-Meteo"):
            lat = _parse_float(weather_lat)
            lon = _parse_float(weather_lon)
            if lat is None or lon is None:
                st.warning("Введите широту и долготу числами.")
            else:
                st.session_state["weather_hint"] = fetch_weather_summary(lat, lon)
                st.success(st.session_state["weather_hint"])

    default_start = datetime.combine(date.today() + timedelta(days=1), time(8, 0))
    default_return = default_start + timedelta(hours=8)

    with st.form("create_hike_form"):
        section_title("Маршрут", "Базовые точки, время и сложность.")
        title = st.text_input("Название похода", placeholder="Например: Соло-ночёвка у озера")
        col1, col2 = st.columns(2)
        start_point = col1.text_input("Стартовая точка")
        end_point = col2.text_input("Конечная точка")
        start_lat = col1.text_input("Широта старта", placeholder="43.2389")
        start_lon = col1.text_input("Долгота старта", placeholder="76.8897")
        end_lat = col2.text_input("Широта финиша")
        end_lon = col2.text_input("Долгота финиша")

        col3, col4 = st.columns(2)
        start_date = col3.date_input("Дата выхода", value=default_start.date())
        start_time = col3.time_input("Время выхода", value=default_start.time())
        return_date = col4.date_input("Дата возвращения", value=default_return.date())
        return_time = col4.time_input("Время возвращения", value=default_return.time())

        col5, col6, col7 = st.columns(3)
        distance_km = col5.number_input("Дистанция, км", min_value=0.0, value=12.0, step=1.0)
        difficulty = col6.selectbox("Сложность", DIFFICULTY_OPTIONS, index=1)
        participants_count = col7.number_input("Количество участников", min_value=1, value=1, step=1)

        weather_default = st.session_state.get("weather_hint", "неизвестно")
        weather_condition = st.text_input("Погода / прогноз", value=weather_default)
        col8, col9, col10 = st.columns(3)
        has_overnight = col8.checkbox("Есть ночёвка")
        water_liters = col9.number_input("Общий запас воды, л", min_value=0.0, value=2.0, step=0.5)
        has_first_aid = col10.checkbox("Аптечка есть", value=True)
        no_signal_zones = st.checkbox("Есть зоны без связи")

        section_title("Контрольные точки", "Добавьте места, где нужно отметиться по времени.")
        checkpoint_count = st.number_input("Количество контрольных точек", min_value=0, max_value=12, value=2, step=1)
        checkpoints: list[Checkpoint] = []
        for index in range(int(checkpoint_count)):
            st.markdown(f"**Контрольная точка {index + 1}**")
            cp_col1, cp_col2, cp_col3 = st.columns([2, 1, 1])
            cp_name = cp_col1.text_input("Название", key=f"cp_name_{index}")
            cp_date = cp_col2.date_input("Дата", value=default_start.date(), key=f"cp_date_{index}")
            cp_time_default = (default_start + timedelta(hours=index + 2)).time()
            cp_time = cp_col3.time_input("Время", value=cp_time_default, key=f"cp_time_{index}")
            cp_lat = cp_col2.text_input("Широта", key=f"cp_lat_{index}")
            cp_lon = cp_col3.text_input("Долгота", key=f"cp_lon_{index}")
            if cp_name:
                checkpoints.append(
                    Checkpoint(
                        name=cp_name,
                        planned_time=_combine_dt(cp_date, cp_time),
                        lat=_parse_float(cp_lat),
                        lon=_parse_float(cp_lon),
                    )
                )

        section_title("Заметки", "Вода, ночёвки, опасные участки и зоны без связи.")
        water_notes = st.text_area("Источники воды")
        camp_notes = st.text_area("Места ночёвки")
        hazard_notes = st.text_area("Опасные участки")
        no_signal_notes = st.text_area("Зоны без связи")
        free_notes = st.text_area("Дополнительные заметки")

        section_title("Условия тревоги", "Все действия всё равно требуют вашего подтверждения.")
        alarm_col1, alarm_col2 = st.columns(2)
        checkpoint_late_enabled = alarm_col1.checkbox("Тревога при просрочке контрольной точки", value=True)
        hike_return_late_enabled = alarm_col1.checkbox("Тревога при просрочке возвращения", value=True)
        no_contact_enabled = alarm_col1.checkbox("Тревога при долгом отсутствии связи", value=True)
        route_deviation_enabled = alarm_col1.checkbox("Тревога при отклонении от маршрута", value=True)
        manual_incident_enabled = alarm_col1.checkbox("Ручные инциденты включены", value=True)
        checkpoint_grace_minutes = alarm_col2.number_input("Допуск для контрольной точки, мин", min_value=0, value=45)
        return_grace_minutes = alarm_col2.number_input("Допуск для возвращения, мин", min_value=0, value=60)
        max_silence_hours = alarm_col2.number_input("Максимум без связи, часов", min_value=1, value=6)
        route_deviation_km_threshold = alarm_col2.number_input("Порог отклонения, км", min_value=0.1, value=1.0)

        submitted = st.form_submit_button("Сохранить поход")

    if not submitted:
        return

    planned_start = _combine_dt(start_date, start_time)
    planned_return = _combine_dt(return_date, return_time)
    if not title or not start_point or not end_point:
        st.error("Заполните название, стартовую и конечную точку.")
        return
    if parse_datetime(planned_return) <= parse_datetime(planned_start):
        st.error("Время возвращения должно быть позже времени выхода.")
        return

    notes = _build_notes(
        {
            "Источники воды": water_notes,
            "Места ночёвки": camp_notes,
            "Опасные участки": hazard_notes,
            "Зоны без связи": no_signal_notes,
            "Дополнительно": free_notes,
        }
    )
    hike = HikePlan(
        title=title,
        start_point=start_point,
        end_point=end_point,
        start_lat=_parse_float(start_lat),
        start_lon=_parse_float(start_lon),
        end_lat=_parse_float(end_lat),
        end_lon=_parse_float(end_lon),
        planned_start=planned_start,
        planned_return=planned_return,
        distance_km=float(distance_km),
        difficulty=difficulty,
        participants_count=int(participants_count),
        weather_condition=weather_condition,
        has_overnight=has_overnight,
        water_liters=float(water_liters),
        has_first_aid=has_first_aid,
        no_signal_zones=no_signal_zones,
        checkpoints=checkpoints,
        notes=notes,
        alarm_settings=AlarmSettings(
            checkpoint_late_enabled=checkpoint_late_enabled,
            hike_return_late_enabled=hike_return_late_enabled,
            no_contact_enabled=no_contact_enabled,
            route_deviation_enabled=route_deviation_enabled,
            manual_incident_enabled=manual_incident_enabled,
            checkpoint_grace_minutes=int(checkpoint_grace_minutes),
            return_grace_minutes=int(return_grace_minutes),
            max_silence_hours=int(max_silence_hours),
            route_deviation_km_threshold=float(route_deviation_km_threshold),
        ),
    )
    hike_id = create_hike(hike)
    st.success(f"Поход сохранён: #{hike_id}")


def page_route_map() -> None:
    page_header(
        "Карта маршрута",
        "Проверьте координаты старта, финиша, контрольных точек и последней известной позиции.",
        "карта",
    )
    hike = _select_hike("Выберите поход для карты")
    if not hike:
        return

    points = _route_points(hike)
    if not points:
        st.info("Добавьте координаты старта, финиша или контрольных точек, чтобы увидеть карту.")
    elif folium is None:
        st.warning("Для карты установите зависимости из requirements.txt: folium и streamlit-folium.")
    else:
        center = [points[0]["lat"], points[0]["lon"]]
        route_map = folium.Map(location=center, zoom_start=11, tiles="OpenStreetMap")
        polyline = []
        for point in points:
            location = [point["lat"], point["lon"]]
            polyline.append(location)
            folium.Marker(location=location, tooltip=point["label"], popup=point["label"]).add_to(route_map)
        if len(polyline) > 1:
            folium.PolyLine(polyline, color="#2563eb", weight=4, opacity=0.8).add_to(route_map)
        if hike.current_lat is not None and hike.current_lon is not None:
            folium.Marker(
                [hike.current_lat, hike.current_lon],
                tooltip="Текущая позиция",
                popup="Последняя известная позиция",
                icon=folium.Icon(color="red", icon="info-sign"),
            ).add_to(route_map)
        st_folium(route_map, width=1100, height=520)

    section_title("Контрольные точки")
    _show_checkpoint_table(hike)


def page_checklists() -> None:
    page_header(
        "Чек-листы",
        "Минимальный набор подготовки для соло-кемпинга, леса и гор.",
        "подготовка",
    )
    category = st.selectbox("Категория", list(CHECKLISTS.keys()))
    items = CHECKLISTS[category]
    done = 0
    for index, item in enumerate(items):
        checked = st.checkbox(item, key=f"checklist_{category}_{index}")
        done += int(checked)
    st.progress(done / max(len(items), 1))
    st.caption(f"Готово: {done} из {len(items)}")


def page_risk() -> None:
    page_header(
        "Оценка риска",
        "Приложение подсвечивает слабые места плана до выхода на маршрут.",
        "risk review",
    )
    hike = _select_hike("Выберите поход")
    if not hike:
        return

    profile = get_profile()
    assessment = assess_risk(hike, profile)
    color = risk_color(assessment["level"])
    st.markdown(f"### Уровень риска: :{color}[{assessment['level'].upper()}]")
    risk_badge(assessment["level"], assessment["score"])
    st.metric("Баллы риска", assessment["score"])
    st.progress(min(assessment["score"] / 16, 1.0))

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Факторы")
        if assessment["factors"]:
            for factor in assessment["factors"]:
                st.write(f"- {factor}")
        else:
            st.success("Существенные факторы риска не обнаружены.")

    with col2:
        st.subheader("Рекомендации")
        for recommendation in assessment["recommendations"]:
            st.write(f"- {recommendation}")

    st.subheader("Проверка условий тревоги")
    alerts = evaluate_alerts(hike)
    if not alerts:
        st.success("Сейчас нет активных тревожных условий.")
    for alert in alerts:
        st.error(f"{alert['title']}: {alert['message']}")


def page_sos() -> None:
    page_header(
        "SOS-режим",
        "Сформируйте сообщение с координатами, маршрутом и медицинскими данными.",
        "ручное подтверждение",
    )
    notice(
        "Без автозвонков",
        "SOS ничего не отправляет автоматически. Сообщение, звонок и SMS запускаются только вашим действием.",
        tone="danger",
    )

    profile = get_profile()
    contacts = list_contacts()
    hike = _select_hike("Связанный поход", allow_none=True)

    default_lat = "" if not hike or hike.current_lat is None else str(hike.current_lat)
    default_lon = "" if not hike or hike.current_lon is None else str(hike.current_lon)
    col1, col2 = st.columns(2)
    lat_text = col1.text_input("Текущая широта", value=default_lat)
    lon_text = col2.text_input("Текущая долгота", value=default_lon)
    lat = _parse_float(lat_text)
    lon = _parse_float(lon_text)
    st.info(f"Текущие координаты: {lat_text or 'не указано'}, {lon_text or 'не указано'}")

    incident_type = st.selectbox(
        "Причина",
        [
            "SOS",
            "травма",
            "потеря ориентации",
            "нехватка воды",
            "встреча с опасным животным",
            "резкое ухудшение погоды",
            "другое",
        ],
    )
    extra_description = st.text_area("Краткое описание ситуации")
    confirmed = st.checkbox("Я подтверждаю, что хочу подготовить тревожное сообщение.")

    if st.button("Сформировать SOS-сообщение", type="primary"):
        if not confirmed:
            st.warning("Сначала подтвердите подготовку тревожного сообщения.")
        else:
            message = generate_sos_message(profile, hike, lat, lon, incident_type, extra_description)
            st.session_state["sos_message"] = message
            if hike and hike.alarm_settings.manual_incident_enabled:
                create_incident(hike.id, incident_type, extra_description, lat, lon, needs_help=True)

    message = st.session_state.get("sos_message")
    if message:
        st.subheader("Готовое сообщение")
        st.text_area("Скопируйте или отправьте", value=message, height=260)
        rescue_number = profile.rescue_number if profile else "112"
        st.markdown(f"[Позвонить {rescue_number}]({build_tel_link(rescue_number)})")
        if contacts:
            st.write("Отправить SMS экстренным контактам:")
            for contact in contacts:
                st.markdown(f"- [{contact.name}: {contact.phone}]({build_sms_link(contact.phone, message)})")
        else:
            st.warning("Нет сохранённых экстренных контактов.")

    st.subheader("Что делать до прибытия помощи")
    for index, instruction in enumerate(SOS_INSTRUCTIONS, start=1):
        st.write(f"{index}. {instruction}")


def page_history() -> None:
    page_header(
        "История походов",
        "Следите за статусами, отметками контрольных точек и последним контактом.",
        "оперативный журнал",
    )
    hikes = list_hikes()
    if not hikes:
        st.info("История пока пустая.")
        return

    rows = [
        {
            "ID": hike.id,
            "Название": hike.title,
            "Статус": hike.status,
            "Старт": _format_dt(hike.planned_start),
            "Возвращение": _format_dt(hike.planned_return),
            "Сложность": hike.difficulty,
            "Дистанция, км": hike.distance_km,
        }
        for hike in hikes
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    hike = _select_hike("Управление походом")
    if not hike:
        return

    st.subheader(hike.title)
    _show_checkpoint_table(hike)
    _hike_quick_actions(hike, prefix="history")

    with st.form(f"contact_update_{hike.id}"):
        st.write("Обновить последнюю связь и позицию")
        col1, col2, col3 = st.columns(3)
        lat = col1.text_input("Широта", value="" if hike.current_lat is None else str(hike.current_lat))
        lon = col2.text_input("Долгота", value="" if hike.current_lon is None else str(hike.current_lon))
        deviation = col3.number_input("Отклонение от маршрута, км", min_value=0.0, value=float(hike.route_deviation_km), step=0.1)
        submitted = st.form_submit_button("Сохранить контакт")
    if submitted:
        hike.current_lat = _parse_float(lat)
        hike.current_lon = _parse_float(lon)
        hike.route_deviation_km = float(deviation)
        hike.last_contact_at = now_iso()
        if hike.status == "planned":
            hike.status = "active"
        update_hike(hike)
        st.success("Последний контакт обновлён.")
        st.rerun()

    st.subheader("Отметить контрольную точку")
    for index, checkpoint in enumerate(hike.checkpoints):
        label = f"Отметить «{checkpoint.name}»"
        if checkpoint.checked_in:
            st.button(label, disabled=True, key=f"cp_done_{hike.id}_{index}")
        elif st.button(label, key=f"cp_mark_{hike.id}_{index}"):
            mark_checkpoint(hike.id, index)
            st.success("Контрольная точка отмечена.")
            st.rerun()

    st.subheader("Заметки маршрута")
    if hike.notes:
        for note in hike.notes:
            st.write(f"**{note['category']}:** {note['text']}")
    else:
        st.write("Заметок нет.")


def page_settings() -> None:
    page_header(
        "Настройки контактов",
        "Профиль безопасности и люди, которым можно быстро отправить SOS-сообщение.",
        "профиль",
    )
    profile = get_profile() or SafetyProfile()

    with st.form("profile_form"):
        st.subheader("Профиль безопасности")
        col1, col2 = st.columns(2)
        user_name = col1.text_input("Имя", value=profile.user_name)
        phone = col2.text_input("Телефон", value=profile.phone)
        blood_group = col1.text_input("Группа крови", value=profile.blood_group)
        hiking_experience = col2.selectbox(
            "Опыт походов",
            EXPERIENCE_OPTIONS,
            index=EXPERIENCE_OPTIONS.index(profile.hiking_experience)
            if profile.hiking_experience in EXPERIENCE_OPTIONS
            else 1,
        )
        allergies = st.text_area("Аллергии", value=profile.allergies)
        chronic_diseases = st.text_area("Хронические болезни", value=profile.chronic_diseases)
        rescue_number = st.text_input("Номер спасательной службы региона", value=profile.rescue_number or "112")
        if st.form_submit_button("Сохранить профиль"):
            save_profile(
                SafetyProfile(
                    user_name=user_name,
                    phone=phone,
                    blood_group=blood_group,
                    allergies=allergies,
                    chronic_diseases=chronic_diseases,
                    hiking_experience=hiking_experience,
                    rescue_number=rescue_number,
                )
            )
            st.success("Профиль сохранён.")
            st.rerun()

    st.subheader("Экстренные контакты")
    with st.form("contact_form"):
        col1, col2, col3 = st.columns(3)
        name = col1.text_input("Имя контакта")
        contact_phone = col2.text_input("Телефон контакта")
        relation = col3.text_input("Кем приходится")
        note = st.text_input("Заметка")
        if st.form_submit_button("Добавить контакт"):
            if not name or not contact_phone:
                st.warning("Имя и телефон обязательны.")
            else:
                add_contact(EmergencyContact(name=name, phone=contact_phone, relation=relation, note=note))
                st.success("Контакт добавлен.")
                st.rerun()

    contacts = list_contacts()
    if not contacts:
        st.info("Контактов пока нет.")
    for contact in contacts:
        cols = st.columns([3, 3, 2, 1])
        cols[0].write(f"**{contact.name}**")
        cols[1].write(contact.phone)
        cols[2].write(contact.relation)
        if cols[3].button("Удалить", key=f"delete_contact_{contact.id}"):
            delete_contact(contact.id)
            st.rerun()


def fetch_weather_summary(lat: float, lon: float) -> str:
    try:
        response = requests.get(
            OPEN_METEO_URL,
            params={"latitude": lat, "longitude": lon, "current": "temperature_2m,wind_speed_10m,weather_code"},
            timeout=8,
        )
        response.raise_for_status()
        current = response.json().get("current", {})
        temp = current.get("temperature_2m")
        wind = current.get("wind_speed_10m")
        code = current.get("weather_code")
        return f"Open-Meteo: {temp}°C, ветер {wind} км/ч, код погоды {code}"
    except requests.RequestException as exc:
        return f"неизвестно (погоду получить не удалось: {exc})"


def _select_hike(label: str, allow_none: bool = False) -> HikePlan | None:
    hikes = list_hikes()
    if not hikes:
        st.info("Сначала создайте поход.")
        return None
    labels = []
    lookup: dict[str, HikePlan | None] = {}
    if allow_none:
        labels.append("Без выбранного похода")
        lookup["Без выбранного похода"] = None
    for hike in hikes:
        item = f"#{hike.id} · {hike.title} · {hike.status}"
        labels.append(item)
        lookup[item] = hike
    selected = st.selectbox(label, labels)
    return lookup[selected]


def _hike_quick_actions(hike: HikePlan, prefix: str) -> None:
    col1, col2, col3 = st.columns(3)
    if col1.button("Начать", key=f"{prefix}_start_{hike.id}", disabled=hike.status != "planned"):
        hike.status = "active"
        hike.last_contact_at = now_iso()
        update_hike(hike)
        st.rerun()
    if col2.button("Отметить связь", key=f"{prefix}_contact_{hike.id}", disabled=hike.status == "completed"):
        hike.last_contact_at = now_iso()
        if hike.status == "planned":
            hike.status = "active"
        update_hike(hike)
        st.rerun()
    if col3.button("Завершить", key=f"{prefix}_finish_{hike.id}", disabled=hike.status == "completed"):
        hike.status = "completed"
        hike.actual_return_at = now_iso()
        hike.last_contact_at = now_iso()
        update_hike(hike)
        st.rerun()


def _show_checkpoint_table(hike: HikePlan) -> None:
    if not hike.checkpoints:
        st.write("Контрольные точки не заданы.")
        return
    rows = [
        {
            "Точка": checkpoint.name,
            "План": _format_dt(checkpoint.planned_time),
            "Координаты": _coords_text(checkpoint.lat, checkpoint.lon),
            "Отмечена": "да" if checkpoint.checked_in else "нет",
            "Время отметки": _format_dt(checkpoint.checked_in_at),
        }
        for checkpoint in hike.checkpoints
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def _route_points(hike: HikePlan) -> list[dict[str, float | str]]:
    points: list[dict[str, float | str]] = []
    if hike.start_lat is not None and hike.start_lon is not None:
        points.append({"label": f"Старт: {hike.start_point}", "lat": hike.start_lat, "lon": hike.start_lon})
    for checkpoint in hike.checkpoints:
        if checkpoint.lat is not None and checkpoint.lon is not None:
            points.append({"label": f"КТ: {checkpoint.name}", "lat": checkpoint.lat, "lon": checkpoint.lon})
    if hike.end_lat is not None and hike.end_lon is not None:
        points.append({"label": f"Финиш: {hike.end_point}", "lat": hike.end_lat, "lon": hike.end_lon})
    return points


def _build_notes(raw_notes: dict[str, str]) -> list[dict[str, str]]:
    return [
        {"category": category, "text": text.strip()}
        for category, text in raw_notes.items()
        if text and text.strip()
    ]


def _combine_dt(day: date, clock: time) -> str:
    return datetime.combine(day, clock).replace(second=0, microsecond=0).isoformat()


def _format_dt(value: str | None) -> str:
    parsed = parse_datetime(value)
    return parsed.strftime("%d.%m.%Y %H:%M") if parsed else "не указано"


def _parse_float(value: str | float | int | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def _coords_text(lat: float | None, lon: float | None) -> str:
    if lat is None or lon is None:
        return "не указаны"
    return f"{lat:.6f}, {lon:.6f}"


if __name__ == "__main__":
    main()
