import { StatusBar } from 'expo-status-bar';
import * as Location from 'expo-location';
import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';

import { CHECKLISTS, SOS_INSTRUCTIONS } from './src/data/checklists';
import { buildSmsUrl, formatCoordinates, generateSosMessage } from './src/logic/emergency';
import { assessRisk, evaluateAlerts, formatDateTime } from './src/logic/safety';
import { AppState, DEFAULT_STATE, loadState, resetState, saveState } from './src/storage';
import { Difficulty, Experience, HikePlan } from './src/types';

type TabKey = 'home' | 'route' | 'checklists' | 'sos';

const TABS: { key: TabKey; label: string }[] = [
  { key: 'home', label: 'Обзор' },
  { key: 'route', label: 'Маршрут' },
  { key: 'checklists', label: 'Чек-листы' },
  { key: 'sos', label: 'SOS' },
];

const DIFFICULTIES: Difficulty[] = ['лёгкий', 'средний', 'сложный', 'экстремальный'];
const EXPERIENCES: Experience[] = ['нет опыта', 'начальный', 'средний', 'опытный', 'инструктор'];

export default function App() {
  const [tab, setTab] = useState<TabKey>('home');
  const [state, setState] = useState<AppState>(DEFAULT_STATE);
  const [loaded, setLoaded] = useState(false);
  const [incident, setIncident] = useState('SOS');
  const [incidentDescription, setIncidentDescription] = useState('');
  const [sosMessage, setSosMessage] = useState('');

  useEffect(() => {
    loadState()
      .then(setState)
      .finally(() => setLoaded(true));
  }, []);

  useEffect(() => {
    if (loaded) {
      saveState(state);
    }
  }, [loaded, state]);

  const assessment = useMemo(() => assessRisk(state.hike, state.profile), [state.hike, state.profile]);
  const alerts = useMemo(() => evaluateAlerts(state.hike), [state.hike]);

  const updateHike = (patch: Partial<HikePlan>) => {
    setState((current) => ({ ...current, hike: { ...current.hike, ...patch } }));
  };

  const markContact = () => {
    updateHike({
      status: state.hike.status === 'planned' ? 'active' : state.hike.status,
      lastContactAt: new Date().toISOString(),
    });
  };

  const markCheckpoint = (checkpointId: string) => {
    setState((current) => ({
      ...current,
      hike: {
        ...current.hike,
        status: current.hike.status === 'planned' ? 'active' : current.hike.status,
        lastContactAt: new Date().toISOString(),
        checkpoints: current.hike.checkpoints.map((checkpoint) =>
          checkpoint.id === checkpointId
            ? { ...checkpoint, checkedIn: true, checkedInAt: new Date().toISOString() }
            : checkpoint,
        ),
      },
    }));
  };

  const requestLocation = async () => {
    const permission = await Location.requestForegroundPermissionsAsync();
    if (permission.status !== 'granted') {
      Alert.alert('Геолокация недоступна', 'Можно ввести координаты вручную в карточке SOS.');
      return;
    }
    const position = await Location.getCurrentPositionAsync({});
    updateHike({
      currentLat: position.coords.latitude,
      currentLon: position.coords.longitude,
      lastContactAt: new Date().toISOString(),
      status: state.hike.status === 'planned' ? 'active' : state.hike.status,
    });
  };

  const prepareSos = () => {
    Alert.alert(
      'Подготовить SOS?',
      'Приложение только сформирует сообщение. Звонок и SMS запускаются отдельным действием.',
      [
        { text: 'Отмена', style: 'cancel' },
        {
          text: 'Сформировать',
          style: 'destructive',
          onPress: () => {
            setSosMessage(
              generateSosMessage(
                state.profile,
                state.hike,
                state.hike.currentLat,
                state.hike.currentLon,
                incident,
                incidentDescription,
              ),
            );
            setTab('sos');
          },
        },
      ],
    );
  };

  const callRescue = () => {
    Alert.alert('Позвонить спасательной службе?', `Будет открыт набор номера ${state.profile.rescueNumber}.`, [
      { text: 'Отмена', style: 'cancel' },
      { text: 'Позвонить', onPress: () => Linking.openURL(`tel:${state.profile.rescueNumber}`) },
    ]);
  };

  const sendSms = (contactId: string) => {
    const contact = state.contacts.find((item) => item.id === contactId);
    if (!contact || !sosMessage) {
      return;
    }
    Alert.alert('Отправить SMS?', `Будет открыт SMS-черновик для ${contact.name}.`, [
      { text: 'Отмена', style: 'cancel' },
      {
        text: 'Открыть SMS',
        onPress: () => Linking.openURL(buildSmsUrl(contact, sosMessage, Platform.OS === 'ios' ? 'ios' : 'android')),
      },
    ]);
  };

  const content = () => {
    if (tab === 'route') {
      return <RouteScreen state={state} setState={setState} updateHike={updateHike} />;
    }
    if (tab === 'checklists') {
      return <ChecklistScreen state={state} setState={setState} />;
    }
    if (tab === 'sos') {
      return (
        <SosScreen
          state={state}
          incident={incident}
          setIncident={setIncident}
          description={incidentDescription}
          setDescription={setIncidentDescription}
          sosMessage={sosMessage}
          requestLocation={requestLocation}
          prepareSos={prepareSos}
          callRescue={callRescue}
          sendSms={sendSms}
        />
      );
    }
    return (
      <HomeScreen
        state={state}
        assessment={assessment}
        alerts={alerts}
        markContact={markContact}
        markCheckpoint={markCheckpoint}
        finishHike={() => updateHike({ status: 'completed', lastContactAt: new Date().toISOString() })}
        prepareSos={prepareSos}
      />
    );
  };

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.safe}>
        <StatusBar style="dark" />
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.shell}>
          <View style={styles.header}>
            <View>
              <Text style={styles.eyebrow}>TrailSafe Mobile</Text>
              <Text style={styles.title}>Безопасный поход</Text>
            </View>
            <RiskBadge level={assessment.level} score={assessment.score} compact />
          </View>
          <View style={styles.warningBar}>
            <Text style={styles.warningText}>
              Не заменяет спасателей, спутниковый маяк и профессиональную навигацию.
            </Text>
          </View>
          <ScrollView style={styles.content} contentContainerStyle={styles.contentInner}>
            {content()}
          </ScrollView>
          <View style={styles.tabBar}>
            {TABS.map((item) => (
              <Pressable
                key={item.key}
                accessibilityRole="button"
                style={[styles.tabButton, tab === item.key && styles.tabButtonActive]}
                onPress={() => setTab(item.key)}
              >
                <Text style={[styles.tabLabel, tab === item.key && styles.tabLabelActive]}>{item.label}</Text>
              </Pressable>
            ))}
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

function HomeScreen({
  state,
  assessment,
  alerts,
  markContact,
  markCheckpoint,
  finishHike,
  prepareSos,
}: {
  state: AppState;
  assessment: ReturnType<typeof assessRisk>;
  alerts: ReturnType<typeof evaluateAlerts>;
  markContact: () => void;
  markCheckpoint: (id: string) => void;
  finishHike: () => void;
  prepareSos: () => void;
}) {
  return (
    <View>
      <Card>
        <Text style={styles.cardLabel}>Текущий маршрут</Text>
        <Text style={styles.cardTitle}>{state.hike.title}</Text>
        <Text style={styles.muted}>{state.hike.startPoint} → {state.hike.endPoint}</Text>
        <View style={styles.metricsRow}>
          <Metric label="Статус" value={statusLabel(state.hike.status)} />
          <Metric label="Финиш" value={formatDateTime(state.hike.plannedReturn)} />
          <Metric label="Связь" value={formatDateTime(state.hike.lastContactAt)} />
        </View>
        <RiskBadge level={assessment.level} score={assessment.score} />
      </Card>

      <View style={styles.actionsRow}>
        <ActionButton label="Отметить связь" onPress={markContact} />
        <ActionButton label="SOS" danger onPress={prepareSos} />
      </View>

      <SectionTitle title="Тревоги" subtitle="Срабатывают только как подсказка. Отправка всегда вручную." />
      {alerts.length === 0 ? (
        <Card>
          <Text style={styles.successText}>Активных тревожных условий нет.</Text>
        </Card>
      ) : (
        alerts.map((alert) => (
          <Card key={alert.title} danger={alert.severity === 'critical'}>
            <Text style={styles.alertTitle}>{alert.title}</Text>
            <Text style={styles.muted}>{alert.message}</Text>
          </Card>
        ))
      )}

      <SectionTitle title="Контрольные точки" />
      {state.hike.checkpoints.map((checkpoint) => (
        <Card key={checkpoint.id}>
          <View style={styles.rowBetween}>
            <View style={styles.flex}>
              <Text style={styles.itemTitle}>{checkpoint.name}</Text>
              <Text style={styles.muted}>План: {formatDateTime(checkpoint.plannedTime)}</Text>
              <Text style={styles.muted}>
                {checkpoint.checkedIn ? `Отмечена: ${formatDateTime(checkpoint.checkedInAt)}` : 'Ожидает отметки'}
              </Text>
            </View>
            <Pressable
              style={[styles.smallButton, checkpoint.checkedIn && styles.smallButtonDisabled]}
              onPress={() => markCheckpoint(checkpoint.id)}
              disabled={checkpoint.checkedIn}
            >
              <Text style={styles.smallButtonText}>{checkpoint.checkedIn ? 'OK' : 'Чек-ин'}</Text>
            </Pressable>
          </View>
        </Card>
      ))}

      <Pressable style={styles.secondaryButton} onPress={finishHike}>
        <Text style={styles.secondaryButtonText}>Завершить поход</Text>
      </Pressable>
    </View>
  );
}

function RouteScreen({
  state,
  setState,
  updateHike,
}: {
  state: AppState;
  setState: React.Dispatch<React.SetStateAction<AppState>>;
  updateHike: (patch: Partial<HikePlan>) => void;
}) {
  const profile = state.profile;
  const hike = state.hike;

  return (
    <View>
      <SectionTitle title="Маршрут" subtitle="Поля сохраняются локально на телефоне." />
      <Card>
        <Field label="Название похода" value={hike.title} onChangeText={(title) => updateHike({ title })} />
        <Field label="Старт" value={hike.startPoint} onChangeText={(startPoint) => updateHike({ startPoint })} />
        <Field label="Финиш" value={hike.endPoint} onChangeText={(endPoint) => updateHike({ endPoint })} />
        <Field
          label="Дистанция, км"
          value={String(hike.distanceKm)}
          keyboardType="numeric"
          onChangeText={(value) => updateHike({ distanceKm: toNumber(value, hike.distanceKm) })}
        />
        <Field
          label="Погода"
          value={hike.weatherCondition}
          onChangeText={(weatherCondition) => updateHike({ weatherCondition })}
        />
        <Field
          label="Вода, л"
          value={String(hike.waterLiters)}
          keyboardType="numeric"
          onChangeText={(value) => updateHike({ waterLiters: toNumber(value, hike.waterLiters) })}
        />
        <Field
          label="Отклонение от маршрута, км"
          value={String(hike.routeDeviationKm)}
          keyboardType="numeric"
          onChangeText={(value) => updateHike({ routeDeviationKm: toNumber(value, hike.routeDeviationKm) })}
        />
        <ChipGroup
          label="Сложность"
          values={DIFFICULTIES}
          selected={hike.difficulty}
          onSelect={(difficulty) => updateHike({ difficulty })}
        />
        <Field
          label="Участников"
          value={String(hike.participantsCount)}
          keyboardType="numeric"
          onChangeText={(value) => updateHike({ participantsCount: Math.max(1, Math.round(toNumber(value, 1))) })}
        />
        <SwitchRow label="Ночёвка" value={hike.hasOvernight} onValueChange={(hasOvernight) => updateHike({ hasOvernight })} />
        <SwitchRow label="Аптечка есть" value={hike.hasFirstAid} onValueChange={(hasFirstAid) => updateHike({ hasFirstAid })} />
        <SwitchRow
          label="Есть зоны без связи"
          value={hike.noSignalZones}
          onValueChange={(noSignalZones) => updateHike({ noSignalZones })}
        />
        <Field label="Заметки" value={hike.notes} multiline onChangeText={(notes) => updateHike({ notes })} />
      </Card>

      <SectionTitle title="Профиль безопасности" />
      <Card>
        <Field
          label="Имя"
          value={profile.userName}
          onChangeText={(userName) => setState((current) => ({ ...current, profile: { ...current.profile, userName } }))}
        />
        <Field
          label="Телефон"
          value={profile.phone}
          keyboardType="phone-pad"
          onChangeText={(phone) => setState((current) => ({ ...current, profile: { ...current.profile, phone } }))}
        />
        <Field
          label="Группа крови"
          value={profile.bloodGroup}
          onChangeText={(bloodGroup) => setState((current) => ({ ...current, profile: { ...current.profile, bloodGroup } }))}
        />
        <ChipGroup
          label="Опыт"
          values={EXPERIENCES}
          selected={profile.hikingExperience}
          onSelect={(hikingExperience) =>
            setState((current) => ({ ...current, profile: { ...current.profile, hikingExperience } }))
          }
        />
        <Field
          label="Аллергии"
          value={profile.allergies}
          onChangeText={(allergies) => setState((current) => ({ ...current, profile: { ...current.profile, allergies } }))}
        />
        <Field
          label="Хронические болезни"
          value={profile.chronicDiseases}
          onChangeText={(chronicDiseases) =>
            setState((current) => ({ ...current, profile: { ...current.profile, chronicDiseases } }))
          }
        />
        <Field
          label="Номер спасательной службы"
          value={profile.rescueNumber}
          keyboardType="phone-pad"
          onChangeText={(rescueNumber) =>
            setState((current) => ({ ...current, profile: { ...current.profile, rescueNumber } }))
          }
        />
      </Card>

      <Pressable
        style={styles.secondaryButton}
        onPress={() =>
          Alert.alert('Сбросить тестовые данные?', 'Локальный план вернётся к стартовому примеру.', [
            { text: 'Отмена', style: 'cancel' },
            {
              text: 'Сбросить',
              style: 'destructive',
              onPress: async () => {
                await resetState();
                setState(DEFAULT_STATE);
              },
            },
          ])
        }
      >
        <Text style={styles.secondaryButtonText}>Сбросить локальные данные</Text>
      </Pressable>
    </View>
  );
}

function ChecklistScreen({ state, setState }: { state: AppState; setState: React.Dispatch<React.SetStateAction<AppState>> }) {
  const total = Object.values(CHECKLISTS).flat().length;
  const done = Object.values(state.checkedItems).filter(Boolean).length;

  const toggle = (key: string) => {
    setState((current) => ({
      ...current,
      checkedItems: { ...current.checkedItems, [key]: !current.checkedItems[key] },
    }));
  };

  return (
    <View>
      <Card>
        <Text style={styles.cardLabel}>Готовность</Text>
        <Text style={styles.cardTitle}>{done} из {total}</Text>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: `${Math.min(100, (done / total) * 100)}%` }]} />
        </View>
      </Card>

      {Object.entries(CHECKLISTS).map(([category, items]) => (
        <View key={category}>
          <SectionTitle title={category} />
          {items.map((item) => {
            const key = `${category}:${item}`;
            const checked = Boolean(state.checkedItems[key]);
            return (
              <Pressable key={key} style={styles.checkRow} onPress={() => toggle(key)}>
                <View style={[styles.checkbox, checked && styles.checkboxActive]}>
                  <Text style={styles.checkboxText}>{checked ? '✓' : ''}</Text>
                </View>
                <Text style={[styles.checkText, checked && styles.checkTextDone]}>{item}</Text>
              </Pressable>
            );
          })}
        </View>
      ))}
    </View>
  );
}

function SosScreen({
  state,
  incident,
  setIncident,
  description,
  setDescription,
  sosMessage,
  requestLocation,
  prepareSos,
  callRescue,
  sendSms,
}: {
  state: AppState;
  incident: string;
  setIncident: (value: string) => void;
  description: string;
  setDescription: (value: string) => void;
  sosMessage: string;
  requestLocation: () => void;
  prepareSos: () => void;
  callRescue: () => void;
  sendSms: (contactId: string) => void;
}) {
  return (
    <View>
      <Card danger>
        <Text style={styles.cardLabel}>Ручной SOS</Text>
        <Text style={styles.cardTitle}>Ничего не отправляется автоматически</Text>
        <Text style={styles.muted}>Сначала подготовьте сообщение. Звонок и SMS открываются отдельными кнопками.</Text>
      </Card>

      <Card>
        <Text style={styles.cardLabel}>Координаты</Text>
        <Text style={styles.cardTitle}>{formatCoordinates(state.hike.currentLat, state.hike.currentLon)}</Text>
        <ActionButton label="Получить координаты" onPress={requestLocation} />
      </Card>

      <Card>
        <Field label="Тип проблемы" value={incident} onChangeText={setIncident} />
        <Field label="Описание" value={description} multiline onChangeText={setDescription} />
        <ActionButton label="Сформировать SOS" danger onPress={prepareSos} />
      </Card>

      {sosMessage ? (
        <Card>
          <Text style={styles.cardLabel}>Сообщение</Text>
          <Text style={styles.messageText}>{sosMessage}</Text>
          <View style={styles.actionsColumn}>
            <ActionButton label={`Позвонить ${state.profile.rescueNumber}`} danger onPress={callRescue} />
            {state.contacts.map((contact) => (
              <ActionButton key={contact.id} label={`SMS: ${contact.name}`} onPress={() => sendSms(contact.id)} />
            ))}
          </View>
        </Card>
      ) : null}

      <SectionTitle title="До прибытия помощи" />
      {SOS_INSTRUCTIONS.map((instruction, index) => (
        <Card key={instruction}>
          <Text style={styles.itemTitle}>{index + 1}. {instruction}</Text>
        </Card>
      ))}
    </View>
  );
}

function Card({ children, danger = false }: { children: React.ReactNode; danger?: boolean }) {
  return <View style={[styles.card, danger && styles.cardDanger]}>{children}</View>;
}

function SectionTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <View style={styles.sectionTitle}>
      <Text style={styles.sectionHeading}>{title}</Text>
      {subtitle ? <Text style={styles.sectionSubtitle}>{subtitle}</Text> : null}
    </View>
  );
}

function RiskBadge({ level, score, compact = false }: { level: string; score: number; compact?: boolean }) {
  const tone = level === 'низкий' ? styles.riskLow : level === 'средний' ? styles.riskMid : level === 'высокий' ? styles.riskHigh : styles.riskCritical;
  return (
    <View style={[styles.riskBadge, tone, compact && styles.riskBadgeCompact]}>
      <Text style={styles.riskText}>{level} · {score}</Text>
    </View>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
    </View>
  );
}

function ActionButton({ label, onPress, danger = false }: { label: string; onPress: () => void; danger?: boolean }) {
  return (
    <Pressable style={[styles.actionButton, danger && styles.actionButtonDanger]} onPress={onPress}>
      <Text style={styles.actionButtonText}>{label}</Text>
    </Pressable>
  );
}

function Field({
  label,
  value,
  onChangeText,
  keyboardType,
  multiline = false,
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: 'default' | 'numeric' | 'phone-pad';
  multiline?: boolean;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.inputLabel}>{label}</Text>
      <TextInput
        style={[styles.input, multiline && styles.inputMultiline]}
        value={value}
        onChangeText={onChangeText}
        keyboardType={keyboardType}
        multiline={multiline}
        placeholderTextColor="#8a9289"
      />
    </View>
  );
}

function ChipGroup<T extends string>({
  label,
  values,
  selected,
  onSelect,
}: {
  label: string;
  values: readonly T[];
  selected: T;
  onSelect: (value: T) => void;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.inputLabel}>{label}</Text>
      <View style={styles.chipWrap}>
        {values.map((value) => (
          <Pressable key={value} style={[styles.chip, selected === value && styles.chipActive]} onPress={() => onSelect(value)}>
            <Text style={[styles.chipText, selected === value && styles.chipTextActive]}>{value}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

function SwitchRow({ label, value, onValueChange }: { label: string; value: boolean; onValueChange: (value: boolean) => void }) {
  return (
    <View style={styles.switchRow}>
      <Text style={styles.itemTitle}>{label}</Text>
      <Switch value={value} onValueChange={onValueChange} trackColor={{ false: '#d8ded5', true: '#a8d5b8' }} />
    </View>
  );
}

function toNumber(value: string, fallback: number) {
  const parsed = Number(value.replace(',', '.'));
  return Number.isFinite(parsed) ? parsed : fallback;
}

function statusLabel(status: string) {
  if (status === 'active') {
    return 'идёт';
  }
  if (status === 'completed') {
    return 'завершён';
  }
  return 'план';
}

const colors = {
  bg: '#f7f8f3',
  panel: '#ffffff',
  ink: '#172026',
  muted: '#5f6b63',
  line: '#e3ded4',
  green: '#1f7a4d',
  greenSoft: '#e8f6ee',
  amber: '#a15c00',
  amberSoft: '#fff4df',
  red: '#b42318',
  redSoft: '#fde8e7',
};

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  shell: {
    flex: 1,
  },
  header: {
    paddingHorizontal: 18,
    paddingTop: 10,
    paddingBottom: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  eyebrow: {
    color: colors.green,
    fontSize: 12,
    fontWeight: '800',
    textTransform: 'uppercase',
  },
  title: {
    color: colors.ink,
    fontSize: 28,
    fontWeight: '800',
  },
  warningBar: {
    marginHorizontal: 18,
    padding: 12,
    borderRadius: 8,
    backgroundColor: colors.amberSoft,
    borderWidth: 1,
    borderColor: '#f2d5a5',
  },
  warningText: {
    color: colors.amber,
    fontWeight: '700',
  },
  content: {
    flex: 1,
  },
  contentInner: {
    padding: 18,
    paddingBottom: 110,
  },
  card: {
    backgroundColor: colors.panel,
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 10,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#0d1b12',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.05,
    shadowRadius: 10,
    elevation: 1,
  },
  cardDanger: {
    borderColor: '#f3b3ae',
    backgroundColor: '#fffafa',
  },
  cardLabel: {
    color: colors.green,
    fontSize: 12,
    fontWeight: '800',
    textTransform: 'uppercase',
    marginBottom: 4,
  },
  cardTitle: {
    color: colors.ink,
    fontSize: 22,
    fontWeight: '800',
    marginBottom: 6,
  },
  muted: {
    color: colors.muted,
    lineHeight: 20,
  },
  metricsRow: {
    flexDirection: 'row',
    gap: 8,
    marginVertical: 12,
  },
  metric: {
    flex: 1,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 10,
    backgroundColor: '#fbfaf6',
  },
  metricLabel: {
    color: colors.muted,
    fontSize: 11,
    marginBottom: 4,
  },
  metricValue: {
    color: colors.ink,
    fontWeight: '800',
    fontSize: 13,
  },
  riskBadge: {
    alignSelf: 'flex-start',
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  riskBadgeCompact: {
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  riskText: {
    fontWeight: '800',
    color: colors.ink,
  },
  riskLow: {
    backgroundColor: colors.greenSoft,
  },
  riskMid: {
    backgroundColor: colors.amberSoft,
  },
  riskHigh: {
    backgroundColor: colors.redSoft,
  },
  riskCritical: {
    backgroundColor: '#ffe7d6',
  },
  actionsRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 12,
  },
  actionsColumn: {
    gap: 10,
    marginTop: 12,
  },
  actionButton: {
    flex: 1,
    minHeight: 48,
    borderRadius: 8,
    backgroundColor: colors.green,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 14,
  },
  actionButtonDanger: {
    backgroundColor: colors.red,
  },
  actionButtonText: {
    color: '#ffffff',
    fontWeight: '800',
    fontSize: 15,
  },
  secondaryButton: {
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 14,
    alignItems: 'center',
    backgroundColor: colors.panel,
  },
  secondaryButtonText: {
    color: colors.ink,
    fontWeight: '800',
  },
  sectionTitle: {
    marginTop: 12,
    marginBottom: 8,
  },
  sectionHeading: {
    color: colors.ink,
    fontSize: 19,
    fontWeight: '800',
  },
  sectionSubtitle: {
    color: colors.muted,
    marginTop: 3,
  },
  rowBetween: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  flex: {
    flex: 1,
  },
  itemTitle: {
    color: colors.ink,
    fontSize: 16,
    fontWeight: '700',
    lineHeight: 21,
  },
  alertTitle: {
    color: colors.red,
    fontSize: 17,
    fontWeight: '800',
    marginBottom: 4,
  },
  successText: {
    color: colors.green,
    fontWeight: '800',
  },
  smallButton: {
    borderRadius: 8,
    backgroundColor: colors.green,
    paddingVertical: 10,
    paddingHorizontal: 12,
  },
  smallButtonDisabled: {
    backgroundColor: '#b9c7bd',
  },
  smallButtonText: {
    color: '#ffffff',
    fontWeight: '800',
  },
  field: {
    marginBottom: 12,
  },
  inputLabel: {
    color: colors.muted,
    fontSize: 12,
    fontWeight: '800',
    marginBottom: 6,
    textTransform: 'uppercase',
  },
  input: {
    minHeight: 46,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: '#fbfaf6',
    color: colors.ink,
    paddingHorizontal: 12,
    fontSize: 16,
  },
  inputMultiline: {
    minHeight: 86,
    paddingTop: 12,
    textAlignVertical: 'top',
  },
  chipWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  chip: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: '#fbfaf6',
    paddingHorizontal: 12,
    paddingVertical: 9,
  },
  chipActive: {
    backgroundColor: colors.green,
    borderColor: colors.green,
  },
  chipText: {
    color: colors.ink,
    fontWeight: '700',
  },
  chipTextActive: {
    color: '#ffffff',
  },
  switchRow: {
    minHeight: 48,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderBottomWidth: 1,
    borderBottomColor: '#f0ece4',
  },
  progressTrack: {
    height: 10,
    borderRadius: 999,
    backgroundColor: '#e5eadf',
    overflow: 'hidden',
    marginTop: 10,
  },
  progressFill: {
    height: '100%',
    backgroundColor: colors.green,
  },
  checkRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: colors.panel,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 8,
    padding: 13,
    marginBottom: 8,
  },
  checkbox: {
    width: 26,
    height: 26,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#b9c7bd',
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkboxActive: {
    backgroundColor: colors.green,
    borderColor: colors.green,
  },
  checkboxText: {
    color: '#ffffff',
    fontWeight: '900',
  },
  checkText: {
    flex: 1,
    color: colors.ink,
    fontSize: 15,
    lineHeight: 20,
  },
  checkTextDone: {
    color: colors.muted,
    textDecorationLine: 'line-through',
  },
  messageText: {
    color: colors.ink,
    lineHeight: 20,
    padding: 12,
    borderRadius: 8,
    backgroundColor: '#fbfaf6',
    borderWidth: 1,
    borderColor: colors.line,
  },
  tabBar: {
    position: 'absolute',
    left: 14,
    right: 14,
    bottom: Platform.OS === 'ios' ? 10 : 12,
    flexDirection: 'row',
    gap: 6,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: '#ffffff',
    padding: 6,
    shadowColor: '#0d1b12',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.12,
    shadowRadius: 18,
    elevation: 4,
  },
  tabButton: {
    flex: 1,
    minHeight: 44,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tabButtonActive: {
    backgroundColor: colors.greenSoft,
  },
  tabLabel: {
    color: colors.muted,
    fontSize: 12,
    fontWeight: '800',
  },
  tabLabelActive: {
    color: colors.green,
  },
});
