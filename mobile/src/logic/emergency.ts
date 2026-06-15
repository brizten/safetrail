import { EmergencyContact, HikePlan, SafetyProfile } from '../types';
import { formatDateTime } from './safety';

export function formatCoordinates(lat?: number, lon?: number) {
  if (lat === undefined || lon === undefined) {
    return 'координаты не указаны';
  }
  return `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
}

export function generateSosMessage(
  profile: SafetyProfile,
  hike: HikePlan,
  lat?: number,
  lon?: number,
  incidentType = 'SOS',
  description = 'нет дополнительного описания',
) {
  const checked = hike.checkpoints.filter((checkpoint) => checkpoint.checkedIn);
  const lastCheckpoint = checked.length > 0 ? checked[checked.length - 1].name : 'нет отмеченных контрольных точек';
  const mapLink = lat !== undefined && lon !== undefined ? `https://maps.google.com/?q=${lat},${lon}` : 'нет';

  return [
    'Я в походе, возможно, мне нужна помощь.',
    `Координаты: ${formatCoordinates(lat, lon)}`,
    `Ссылка на карту: ${mapLink}`,
    `Маршрут: ${hike.title}: ${hike.startPoint} -> ${hike.endPoint}`,
    `Последняя контрольная точка: ${lastCheckpoint}`,
    `Последний контакт: ${formatDateTime(hike.lastContactAt)}`,
    `Плановое возвращение: ${formatDateTime(hike.plannedReturn)}`,
    `Тип проблемы: ${incidentType}`,
    `Описание: ${description}`,
    `Данные пользователя: ${profile.userName}, телефон ${profile.phone}`,
    `Группа крови: ${profile.bloodGroup}`,
    `Аллергии: ${profile.allergies || 'не указано'}`,
    `Хронические болезни: ${profile.chronicDiseases || 'не указано'}`,
  ].join('\n');
}

export function buildSmsUrl(contact: EmergencyContact, message: string, platform: 'ios' | 'android' | 'web') {
  const separator = platform === 'ios' ? '&' : '?';
  return `sms:${contact.phone}${separator}body=${encodeURIComponent(message)}`;
}
