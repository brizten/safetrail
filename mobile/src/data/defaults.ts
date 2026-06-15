import { EmergencyContact, HikePlan, SafetyProfile } from '../types';

const now = new Date();
const plusHours = (hours: number) => new Date(now.getTime() + hours * 60 * 60 * 1000).toISOString();

export const DEFAULT_PROFILE: SafetyProfile = {
  userName: 'Алексей Морозов',
  phone: '+7 000 000-00-00',
  bloodGroup: 'O+',
  allergies: 'пенициллин',
  chronicDiseases: 'нет',
  hikingExperience: 'начальный',
  rescueNumber: '112',
};

export const DEFAULT_CONTACTS: EmergencyContact[] = [
  {
    id: 'contact-1',
    name: 'Марина',
    phone: '+7 000 000-00-01',
    relation: 'сестра',
  },
  {
    id: 'contact-2',
    name: 'Игорь',
    phone: '+7 000 000-00-02',
    relation: 'напарник',
  },
];

export const DEFAULT_HIKE: HikePlan = {
  title: 'Соло-ночёвка на перевале',
  startPoint: 'Лесная тропа Север',
  endPoint: 'Перевал Каменный',
  plannedStart: plusHours(2),
  plannedReturn: plusHours(12),
  distanceKm: 18,
  difficulty: 'сложный',
  participantsCount: 1,
  weatherCondition: 'переменная облачность',
  hasOvernight: true,
  waterLiters: 2,
  hasFirstAid: true,
  noSignalZones: true,
  routeDeviationKm: 0,
  checkpoints: [
    {
      id: 'cp-1',
      name: 'Развилка у старой сосны',
      plannedTime: plusHours(5),
      lat: 43.15,
      lon: 77.07,
      checkedIn: false,
    },
    {
      id: 'cp-2',
      name: 'Ручей перед перевалом',
      plannedTime: plusHours(8),
      lat: 43.18,
      lon: 77.12,
      checkedIn: false,
    },
  ],
  notes: 'После развилки связь может пропадать. У ручья возможна ночёвка.',
  status: 'planned',
  currentLat: 43.166,
  currentLon: 77.101,
  alarmSettings: {
    checkpointGraceMinutes: 45,
    returnGraceMinutes: 60,
    maxSilenceHours: 6,
    routeDeviationKmThreshold: 1,
  },
};
