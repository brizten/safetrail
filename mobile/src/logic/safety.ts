import { AlertItem, HikePlan, RiskAssessment, SafetyProfile } from '../types';

const BAD_WEATHER_WORDS = ['гроза', 'ливень', 'снег', 'метель', 'туман', 'шторм', 'ветер', 'мороз', 'жара'];

export function assessRisk(hike: HikePlan, profile: SafetyProfile): RiskAssessment {
  let score = 0;
  const factors: string[] = [];
  const recommendations: string[] = [];

  const add = (points: number, factor: string, recommendation: string) => {
    score += points;
    factors.push(factor);
    recommendations.push(recommendation);
  };

  if (hike.participantsCount <= 1) {
    add(2, 'Одиночный поход', 'Оставьте маршрут и контрольные времена доверенному контакту.');
  }
  if (hike.difficulty === 'средний') {
    add(1, 'Средняя сложность маршрута', 'Проверьте запас времени и навигационные точки.');
  }
  if (hike.difficulty === 'сложный') {
    add(2, 'Сложный маршрут', 'Добавьте запасной план схода с маршрута.');
  }
  if (hike.difficulty === 'экстремальный') {
    add(4, 'Экстремальный маршрут', 'Не выходите без группы, связи и аварийного маяка.');
  }
  if (hike.hasOvernight) {
    add(2, 'Планируется ночёвка', 'Проверьте укрытие, теплоизоляцию, фонарь и ночной план.');
  }
  if (hike.noSignalZones) {
    add(2, 'Есть зоны без связи', 'Назначьте контрольные окна связи и продумайте спутниковый канал.');
  }
  if (BAD_WEATHER_WORDS.some((word) => hike.weatherCondition.toLowerCase().includes(word))) {
    add(2, 'Неблагоприятная погода', 'Сверьте прогноз перед выходом и подготовьте вариант отмены.');
  }

  const expectedWater = expectedWaterLiters(hike);
  if (hike.waterLiters < expectedWater) {
    add(2, 'Мало воды', `Запланируйте минимум ${expectedWater.toFixed(1)} л воды или источники пополнения.`);
  }
  if (!hike.hasFirstAid) {
    add(2, 'Нет аптечки', 'Добавьте аптечку и индивидуальные лекарства.');
  }
  if (profile.hikingExperience === 'нет опыта' || profile.hikingExperience === 'начальный') {
    add(2, 'Недостаточный опыт', 'Выберите простой маршрут или идите с опытным напарником.');
  }
  if (hike.checkpoints.length === 0) {
    add(2, 'Нет контрольных точек', 'Добавьте контрольные точки с ожидаемым временем прибытия.');
  }

  const returnDate = new Date(hike.plannedReturn);
  if (!Number.isNaN(returnDate.getTime()) && (returnDate.getHours() >= 22 || returnDate.getHours() < 6)) {
    add(1, 'Позднее возвращение', 'Заложите финиш до темноты или подготовьте ночной выход.');
  }

  return {
    score,
    level: score <= 3 ? 'низкий' : score <= 7 ? 'средний' : score <= 12 ? 'высокий' : 'критический',
    factors,
    recommendations: Array.from(new Set(recommendations)),
  };
}

export function evaluateAlerts(hike: HikePlan, now = new Date()): AlertItem[] {
  if (hike.status === 'completed') {
    return [];
  }

  const alerts: AlertItem[] = [];
  const settings = hike.alarmSettings;

  const lateCheckpoint = hike.checkpoints.find((checkpoint) => {
    if (checkpoint.checkedIn) {
      return false;
    }
    const planned = new Date(checkpoint.plannedTime);
    return now.getTime() > planned.getTime() + settings.checkpointGraceMinutes * 60 * 1000;
  });

  if (lateCheckpoint) {
    alerts.push({
      severity: 'high',
      title: 'Контрольная точка просрочена',
      message: `Не отмечена точка «${lateCheckpoint.name}».`,
    });
  }

  const plannedReturn = new Date(hike.plannedReturn);
  if (now.getTime() > plannedReturn.getTime() + settings.returnGraceMinutes * 60 * 1000) {
    alerts.push({
      severity: 'critical',
      title: 'Поход не завершён вовремя',
      message: 'Плановое время возвращения истекло с учётом допустимой задержки.',
    });
  }

  const lastContact = new Date(hike.lastContactAt || hike.plannedStart);
  if (now.getTime() > lastContact.getTime() + settings.maxSilenceHours * 60 * 60 * 1000) {
    alerts.push({
      severity: 'high',
      title: 'Долго нет связи',
      message: `Последний контакт: ${formatDateTime(lastContact.toISOString())}.`,
    });
  }

  if (hike.routeDeviationKm > settings.routeDeviationKmThreshold) {
    alerts.push({
      severity: 'high',
      title: 'Отклонение от маршрута',
      message: `${hike.routeDeviationKm.toFixed(1)} км при пороге ${settings.routeDeviationKmThreshold.toFixed(1)} км.`,
    });
  }

  return alerts;
}

export function formatDateTime(value?: string) {
  if (!value) {
    return 'не указано';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function expectedWaterLiters(hike: HikePlan) {
  const start = new Date(hike.plannedStart);
  const end = new Date(hike.plannedReturn);
  const durationDays = Math.max((end.getTime() - start.getTime()) / 86_400_000, 0.5);
  const weatherBonus = ['жара', 'ветер'].some((word) => hike.weatherCondition.toLowerCase().includes(word)) ? 1.3 : 1;
  return Math.max(hike.participantsCount, 1) * durationDays * 2 * weatherBonus;
}
