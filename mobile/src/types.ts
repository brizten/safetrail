export type Difficulty = 'лёгкий' | 'средний' | 'сложный' | 'экстремальный';
export type Experience = 'нет опыта' | 'начальный' | 'средний' | 'опытный' | 'инструктор';
export type HikeStatus = 'planned' | 'active' | 'completed';

export type Checkpoint = {
  id: string;
  name: string;
  plannedTime: string;
  lat?: number;
  lon?: number;
  checkedIn: boolean;
  checkedInAt?: string;
};

export type AlarmSettings = {
  checkpointGraceMinutes: number;
  returnGraceMinutes: number;
  maxSilenceHours: number;
  routeDeviationKmThreshold: number;
};

export type HikePlan = {
  title: string;
  startPoint: string;
  endPoint: string;
  plannedStart: string;
  plannedReturn: string;
  distanceKm: number;
  difficulty: Difficulty;
  participantsCount: number;
  weatherCondition: string;
  hasOvernight: boolean;
  waterLiters: number;
  hasFirstAid: boolean;
  noSignalZones: boolean;
  routeDeviationKm: number;
  checkpoints: Checkpoint[];
  notes: string;
  status: HikeStatus;
  currentLat?: number;
  currentLon?: number;
  lastContactAt?: string;
  alarmSettings: AlarmSettings;
};

export type SafetyProfile = {
  userName: string;
  phone: string;
  bloodGroup: string;
  allergies: string;
  chronicDiseases: string;
  hikingExperience: Experience;
  rescueNumber: string;
};

export type EmergencyContact = {
  id: string;
  name: string;
  phone: string;
  relation: string;
};

export type RiskAssessment = {
  level: 'низкий' | 'средний' | 'высокий' | 'критический';
  score: number;
  factors: string[];
  recommendations: string[];
};

export type AlertItem = {
  severity: 'high' | 'critical';
  title: string;
  message: string;
};
