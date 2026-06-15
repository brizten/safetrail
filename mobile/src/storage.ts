import AsyncStorage from '@react-native-async-storage/async-storage';
import { DEFAULT_CONTACTS, DEFAULT_HIKE, DEFAULT_PROFILE } from './data/defaults';
import { EmergencyContact, HikePlan, SafetyProfile } from './types';

const STORAGE_KEY = 'trailsafe-mobile-state-v1';

export type AppState = {
  profile: SafetyProfile;
  contacts: EmergencyContact[];
  hike: HikePlan;
  checkedItems: Record<string, boolean>;
};

export const DEFAULT_STATE: AppState = {
  profile: DEFAULT_PROFILE,
  contacts: DEFAULT_CONTACTS,
  hike: DEFAULT_HIKE,
  checkedItems: {},
};

export async function loadState(): Promise<AppState> {
  const raw = await AsyncStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return DEFAULT_STATE;
  }
  try {
    return {
      ...DEFAULT_STATE,
      ...JSON.parse(raw),
    };
  } catch {
    return DEFAULT_STATE;
  }
}

export async function saveState(state: AppState) {
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export async function resetState() {
  await AsyncStorage.removeItem(STORAGE_KEY);
}
