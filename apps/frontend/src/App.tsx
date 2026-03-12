import { useCallback, useEffect, useMemo, useState, useRef, type ReactNode } from 'react';
import { BASE, jdelete, jget, jpatch, jpost } from './api';
import ErrorBoundary from './ErrorBoundary';
import './styles.css';

type RouteKey =
  | 'overview'
  | 'tasks'
  | 'focus'
  | 'alarm-player'
  | 'habits'
  | 'eisenhower-kanban'
  | 'review-anki'
  | 'commands';

const ROUTES: { key: RouteKey; label: string }[] = [
  { key: 'overview', label: 'Overview Grid' },
  { key: 'tasks', label: 'Tasks' },
  { key: 'focus', label: 'Focus / Pomodoro' },
  { key: 'alarm-player', label: 'Alarm / Player' },
  { key: 'habits', label: 'Habits' },
  { key: 'eisenhower-kanban', label: 'Eisenhower / Kanban' },
  { key: 'review-anki', label: 'Review / Anki' },
  { key: 'commands', label: 'Commands' },
];

const DEFAULT_ROUTE: RouteKey = 'overview';

// Module-level dedup set — survives React strict mode double-invoke
const _firedNotifIds = new Set<string>();

function hashMeta() {
  const raw = window.location.hash.replace(/^#\//, '');
  const [routePart, query = ''] = raw.split('?');
  const route = ROUTES.some((r) => r.key === routePart) ? (routePart as RouteKey) : DEFAULT_ROUTE;
  const params = new URLSearchParams(query);
  return {
    route,
    sourceId: params.get('source_id') || '',
    title: params.get('title') || '',
  };
}

function BoxCard({
  title, children, compact = false, testId,
}: { title: string; children: ReactNode; compact?: boolean; testId: string }) {
  return (
    <section className={`box-card ${compact ? 'compact' : ''}`} data-testid={testId} aria-label={`${title} panel`} role="region">
      <h4>{title}</h4>
      {children}
    </section>
  );
}

export default function App() {
  const [route, setRoute] = useState<RouteKey>(hashMeta().route);
  const [linkedSourceId, setLinkedSourceId] = useState<string>(hashMeta().sourceId);
  const [linkedTitle, setLinkedTitle] = useState<string>(hashMeta().title);
  const [tasks, setTasks] = useState<any[]>([]);
  const [newTask, setNewTask] = useState({ title: '', due_at: '', priority: 2 });
  const [taskCreateMsg, setTaskCreateMsg] = useState<string>('');
  const [taskCreateErr, setTaskCreateErr] = useState<string>('');
  const [taskEditId, setTaskEditId] = useState<string>('');
  const [taskEdit, setTaskEdit] = useState({ title: '', due_at: '', priority: 2 });
  const [cmd, setCmd] = useState('');
  const [cmdError, setCmdError] = useState('');
  const [history, setHistory] = useState<any[]>([]);
  const [quick, setQuick] = useState('Pay rent tomorrow 9pm #finance !high');
  const [quickCommit, setQuickCommit] = useState(false);
  const [quickResult, setQuickResult] = useState<string | null>(null);
  const [quickError, setQuickError] = useState<string | null>(null);
  const [reviewState, setReviewState] = useState<any>(null);
  const [currentCard, setCurrentCard] = useState<any>(null);
  const [showBack, setShowBack] = useState(false);
  const [decks, setDecks] = useState<any[]>([]);
  const [selectedDeck, setSelectedDeck] = useState<string>('');
  const [newDeckName, setNewDeckName] = useState('');
  const [newCard, setNewCard] = useState({ front: '', back: '', tags: '' });
  const [alarmForm, setAlarmForm] = useState({ at: '07:30', kind: 'alarm', title: 'Wake up', tts_text: 'Good morning', youtube_link: '' });
  const [alarmFiring, setAlarmFiring] = useState<string | null>(null); // alarm_id currently firing
  const [alarmResult, setAlarmResult] = useState<any>(null);
  const [alarms, setAlarms] = useState<any[]>([]);
  const [matrix, setMatrix] = useState<any>(null);
  const [focus, setFocus] = useState<any>(null);
  const [player, setPlayer] = useState<any>({ queueInput: 'lofi-1,lofi-2', queue: [] as string[], jobs: [] as any[] });
  const [apiMeta, setApiMeta] = useState<any>(null);
  const [habitsWeekly, setHabitsWeekly] = useState<any>(null);
  const [habitList, setHabitList] = useState<string[]>([]);
  const [newHabit, setNewHabit] = useState('');
  const [globalError, setGlobalError] = useState<string>('');
  const [panelErrors, setPanelErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const activeAlarmAudioRef = useRef<HTMLAudioElement | null>(null);
  const lastAlarmPlayAtRef = useRef<Record<string, number>>({});

  function setLoad(key: string, val: boolean) {
    setLoading((l) => ({ ...l, [key]: val }));
  }

  function setPanelError(key: string, message: string) {
    setPanelErrors((prev) => ({ ...prev, [key]: message }));
  }

  function clearPanelError(key: string) {
    setPanelErrors((prev) => {
      if (!prev[key]) return prev;
      const next = { ...prev };
      delete next[key];
      return next;
    });
  }

  function apiErr(panelKey: string, context: string) {
    return (err: any) => {
      console.error(context, err);
      setPanelError(panelKey, `${context}: ${err?.message || 'API error'}`);
    };
  }

  const getReviewSession = useCallback(async () => {
    const params = new URLSearchParams();
    if (selectedDeck) params.set('deck_id', selectedDeck);
    const q = params.toString();
    return jget(`/review/session${q ? `?${q}` : ''}`);
  }, [selectedDeck]);

  const refreshTasks = useCallback(async () => {
    const items = await jget('/tasks/');
    setTasks(items);
  }, []);

  const refreshAlarms = useCallback(async () => {
    const data = await jget('/alarms/');
    setAlarms(data.alarms || []);
  }, []);

  const refreshHabits = useCallback(async () => {
    const [weekly, list] = await Promise.all([jget('/habits/weekly'), jget('/habits/list')]);
    setHabitsWeekly(weekly);
    setHabitList(list.habits?.map((h: any) => h.name) || []);
  }, []);

  // ── Alarm audio/TTS firing ──────────────────────────────────────────────────
  const fireAlarmAudio = useCallback((tts_text: string, youtube_link: string, alarm_id: string) => {
    const now = Date.now();
    const lastPlayAt = lastAlarmPlayAtRef.current[alarm_id] || 0;
    if (now - lastPlayAt < 30_000) {
      console.log('[alarm] duplicate suppressed', { alarm_id, age_ms: now - lastPlayAt });
      return;
    }
    lastAlarmPlayAtRef.current[alarm_id] = now;

    setAlarmFiring(alarm_id);
    console.log('[alarm] firing', { tts_text, youtube_link, alarm_id });
    // Note: TTS is handled by the backend (espeak-ng/say/powershell) via the trigger endpoint.
    // Frontend only handles YouTube playback.
    if (youtube_link) {
      jpost('/player/resolve-url', { url: youtube_link })
        .then((res: any) => {
          console.log('[alarm] resolve-url result', res);
          if (res?.stream_url) {
            clearPanelError('alarm-player');
            if (activeAlarmAudioRef.current) {
              activeAlarmAudioRef.current.pause();
              activeAlarmAudioRef.current.currentTime = 0;
              activeAlarmAudioRef.current = null;
            }
            const audio = new Audio(res.stream_url);
            activeAlarmAudioRef.current = audio;
            audio.volume = 0.8;
            audio.play().catch((e) => console.error('[alarm] audio play blocked', e));
            audio.onended = () => {
              if (activeAlarmAudioRef.current === audio) activeAlarmAudioRef.current = null;
              setAlarmFiring(null);
            };
          } else {
            setPanelError('alarm-player', `Link playback failed: ${res?.error || 'Unable to resolve stream URL. Ensure yt-dlp is installed.'}`);
            setAlarmFiring(null);
          }
        })
        .catch((e) => {
          console.error('[alarm] resolve-url failed', e);
          setPanelError('alarm-player', `Link playback failed: ${e?.message || 'Unable to resolve URL'}`);
          setAlarmFiring(null);
        });
    } else {
      setTimeout(() => setAlarmFiring(null), 5000);
    }
  }, [clearPanelError, setPanelError]);

  // ── Poll notifications every 30s for alarm_trigger scope ───────────────────
  const firedNotifIds = _firedNotifIds; // module-level, not reset on re-render

  useEffect(() => {
    const poll = async () => {
      try {
        const data = await jget('/notifications/?scope=alarm_trigger');
        const items: any[] = data.items || [];
        const unread = items.filter((n: any) => !n.is_read && !n.archived);
        console.log('[alarm-poll] unread items:', unread.length);
        for (const notif of unread) {
          if (firedNotifIds.has(notif.id)) continue;
          firedNotifIds.add(notif.id);
          // Mark read on backend first — if two windows race, only one wins
          const marked = await jpost(`/notifications/${notif.id}/read`).catch(() => null);
          if (!marked) continue; // another instance got it first
          try {
            const payload = JSON.parse(notif.body || '{}');
            fireAlarmAudio(
              payload.tts_text || notif.title,
              payload.youtube_link || '',
              payload.alarm_id || notif.id
            );
          } catch {
            fireAlarmAudio(notif.title, '', notif.id);
          }
        }
      } catch (e) {
        console.error('[alarm-poll] fetch failed', e);
      }
    };
    poll();
    const t = setInterval(poll, 30_000);
    return () => clearInterval(t);
  }, [fireAlarmAudio]);

  // ── rateCard defined BEFORE any useEffect that references it ───────────────
  const rateCard = useCallback(async (rating: string) => {
    const params = new URLSearchParams({ rating });
    if (currentCard?.id) params.append('card_id', currentCard.id);
    try {
      const out = await jpost(`/review/answer?${params.toString()}`);
      setReviewState(out.session);
      setShowBack(false);
      const res = await getReviewSession();
      setCurrentCard(res.card || null);
    } catch (err: any) {
      apiErr('review', 'Rate card')(err);
    }
  }, [currentCard, getReviewSession]);

  useEffect(() => {
    const onHash = () => {
      const meta = hashMeta();
      setRoute(meta.route);
      setLinkedSourceId(meta.sourceId);
      setLinkedTitle(meta.title);
    };
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  useEffect(() => {
    jget('/meta/openapi').then(setApiMeta).catch(() => setApiMeta(null));
  }, []);

  useEffect(() => {
    if (route === 'tasks' || route === 'overview') {
      setLoad('tasks', true);
      refreshTasks().then(() => clearPanelError('tasks')).catch(apiErr('tasks', 'Tasks')).finally(() => setLoad('tasks', false));
    }
    if (route === 'review-anki' || route === 'overview') {
      setLoad('review', true);
      getReviewSession().then((res) => { setReviewState(res); setCurrentCard(res.card || null); setShowBack(false); clearPanelError('review'); })
        .catch(apiErr('review', 'Review session')).finally(() => setLoad('review', false));
      jget('/review/decks')
        .then((res) => {
          const items = (res.items || []).map((d: any) => ({ ...d, id: String(d.id) }));
          setDecks(items);
        })
        .catch(() => {});
    }
    if (route === 'eisenhower-kanban' || route === 'overview') {
      setLoad('matrix', true);
      jget('/boards/matrix-data')
        .then((data) => { setMatrix(data?.quadrants || data || null); clearPanelError('matrix'); })
        .catch(apiErr('matrix', 'Matrix'))
        .finally(() => setLoad('matrix', false));
    }
    if (route === 'focus' || route === 'overview') {
      setLoad('focus', true);
      jget('/focus/status').then((data) => { setFocus(data); clearPanelError('focus'); }).catch(apiErr('focus', 'Focus')).finally(() => setLoad('focus', false));
    }
    if (route === 'alarm-player' || route === 'overview') {
      setLoad('player', true);
      Promise.allSettled([
        jget('/player/queue'),
        jget('/player/predownload/status')
      ]).then((results) => {
        const r0 = results[0] as PromiseFulfilledResult<any>;
        const r1 = results[1] as PromiseFulfilledResult<any>;
        if (results[0].status === 'fulfilled') {
          setPlayer((p: any) => ({ ...p, queue: r0.value.items || [] }));
          clearPanelError('player');
        } else apiErr('player', 'Player queue')((results[0] as PromiseRejectedResult).reason);
        if (results[1].status === 'fulfilled') {
          setPlayer((p: any) => ({ ...p, jobs: r1.value.items || [] }));
          clearPanelError('player');
        } else apiErr('player', 'Player predownload')((results[1] as PromiseRejectedResult).reason);
      }).finally(() => setLoad('player', false));

      setLoad('alarms', true);
      refreshAlarms().then(() => clearPanelError('alarm-player')).catch(apiErr('alarm-player', 'Alarms')).finally(() => setLoad('alarms', false));
    }
    if (route === 'habits' || route === 'overview') {
      setLoad('habits', true);
      refreshHabits().then(() => clearPanelError('habits')).catch(apiErr('habits', 'Habits')).finally(() => setLoad('habits', false));
    }
  }, [route, refreshTasks, getReviewSession, refreshAlarms, refreshHabits]);

  // Keyboard shortcuts for review (1-4)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (route !== 'review-anki' && route !== 'overview') return;
      if (!currentCard) return;
      if (['1', '2', '3', '4'].includes(e.key)) {
        e.preventDefault();
        const rating = e.key === '1' ? 'again' : e.key === '2' ? 'hard' : e.key === '3' ? 'good' : 'easy';
        rateCard(rating);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [route, currentCard, rateCard]);

  // Pomodoro live countdown
  useEffect(() => {
    if (!focus || focus.status !== 'running') return;
    const t = setInterval(() => jget('/focus/status').then((data) => { setFocus(data); clearPanelError('focus'); }).catch(apiErr('focus', 'Focus poll')), 1000);
    return () => clearInterval(t);
  }, [focus?.status]);

  const countdown = useMemo(() => {
    const sec = focus?.remaining_seconds ?? 0;
    const mm = String(Math.floor(sec / 60)).padStart(2, '0');
    const ss = String(sec % 60).padStart(2, '0');
    return `${mm}:${ss}`;
  }, [focus]);

  function navigate(target: RouteKey) {
    window.location.hash = `/${target}`;
  }

  function openZoesCal() {
    window.open('http://localhost:5174', '_blank', 'noopener,noreferrer');
  }

  async function runQuick() {
    setQuickError(null);
    setQuickResult(null);
    try {
      const out = await jpost('/tasks/quick-add', { text: quick, commit: quickCommit });
      if (quickCommit && out.created) {
        setTasks((prev) => [out.created, ...prev]);
        setQuickResult('Task created and added to list');
      } else if (out.parsed) {
        setQuickResult('Parsed: ' + JSON.stringify(out.parsed));
      } else {
        setQuickResult('Parsed OK');
      }
    } catch (err: any) {
      setQuickError(err?.message || 'Quick add failed');
    }
  }

  async function addTask() {
    if (!newTask.title.trim()) return;
    setTaskCreateMsg('');
    setTaskCreateErr('');
    setLoad('task-create', true);
    try {
      await jpost('/tasks/', { title: newTask.title, due_at: newTask.due_at || undefined, priority: newTask.priority });
      await refreshTasks();
      setNewTask({ title: '', due_at: '', priority: 2 });
      setTaskCreateMsg('Task added');
    } catch (err: any) {
      setTaskCreateErr(err?.message || 'Failed to add task');
      apiErr('tasks', 'Add task')(err);
    } finally {
      setLoad('task-create', false);
    }
  }

  async function completeTask(id: string) {
    try {
      await jpatch(`/tasks/${id}/complete`);
      await refreshTasks();
    } catch (err: any) { apiErr('tasks', 'Complete task')(err); }
  }

  function beginEditTask(t: any) {
    setTaskEditId(t.id);
    setTaskEdit({
      title: t.title || '',
      due_at: t.due_at ? String(t.due_at).slice(0, 16) : '',
      priority: Number(t.priority) || 2,
    });
  }

  async function saveTaskEdit() {
    if (!taskEditId || !taskEdit.title.trim()) return;
    try {
      await jpatch(`/tasks/${taskEditId}`, {
        title: taskEdit.title,
        due_at: taskEdit.due_at || null,
        priority: taskEdit.priority,
      });
      setTaskEditId('');
      await refreshTasks();
    } catch (err: any) {
      apiErr('tasks', 'Update task')(err);
    }
  }

  async function deleteTask(id: string) {
    try {
      await jdelete(`/tasks/${id}`);
      if (taskEditId === id) setTaskEditId('');
      await refreshTasks();
    } catch (err: any) {
      apiErr('tasks', 'Delete task')(err);
    }
  }

  async function runCmd() {
    setCmdError('');
    try {
      await jpost('/commands/execute', { text: cmd, confirm: true });
      const h = await jget('/commands/history');
      setHistory(Array.isArray(h) ? h : h.items || []);
      setCmd('');
    } catch (err: any) {
      setCmdError(err?.message || 'Command failed');
    }
  }

  async function createAlarm() {
    try {
      const safeAt = /^\d{1,2}:\d{2}$/.test(alarmForm.at) ? alarmForm.at : '07:30';
      setAlarmResult(await jpost('/alarms/', { ...alarmForm, at: safeAt }));
      await refreshAlarms();
    } catch (err: any) { apiErr('alarm-player', 'Create alarm')(err); }
  }

  async function startPomodoro() {
    try {
      await jpost('/focus/start?minutes=25');
      setFocus(await jget('/focus/status'));
    } catch (err: any) { apiErr('focus', 'Start pomodoro')(err); }
  }

  async function createDeck() {
    if (!newDeckName.trim()) return;
    setLoad('deck-create', true);
    try {
      const d = await jpost(`/review/decks?name=${encodeURIComponent(newDeckName.trim())}`);
      const created = { ...d, id: String(d.id) };
      setDecks((prev) => (prev.some((deck: any) => String(deck.id) === created.id) ? prev : [...prev, created]));
      setSelectedDeck(created.id);
      setNewDeckName('');
      clearPanelError('review');
    } catch (err: any) {
      apiErr('review', 'Create deck')(err);
    } finally {
      setLoad('deck-create', false);
    }
  }

  async function addHabit() {
    if (!newHabit.trim()) return;
    setLoad('habit-add', true);
    try {
      await jpost(`/habits/add?name=${encodeURIComponent(newHabit.trim())}`);
      setNewHabit('');
      await refreshHabits();
      clearPanelError('habits');
    } catch (err: any) {
      apiErr('habits', 'Add habit')(err);
    } finally {
      setLoad('habit-add', false);
    }
  }

  async function addCard() {
    if (!selectedDeck || !newCard.front.trim() || !newCard.back.trim()) return;
    try {
      const tags = newCard.tags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean)
        .join('|');
      await jpost(`/review/decks/${selectedDeck}/cards?front=${encodeURIComponent(newCard.front)}&back=${encodeURIComponent(newCard.back)}&tags=${encodeURIComponent(tags)}`);
      setNewCard({ front: '', back: '', tags: '' });
      // Refresh session
      const res = await getReviewSession();
      setCurrentCard(res.card || null);
      setReviewState(res);
      setShowBack(false);
    } catch (err: any) { apiErr('review', 'Add card')(err); }
  }

  // ── Panel Components ───────────────────────────────────────────────────────

  function TasksBox({ compact = false }: { compact?: boolean }) {
    const orderedTasks = [...tasks].sort((a, b) => Number(!!a.done) - Number(!!b.done));
    return (
      <BoxCard title="Tasks" compact={compact} testId="box-tasks">
        {loading.tasks && <p className="loading">Loading…</p>}
        {panelErrors.tasks && <p className="error-inline">{panelErrors.tasks}</p>}
        {!compact && (
          <>
            <div className="row-group">
              <input value={quick} onChange={(e) => setQuick(e.target.value)} placeholder="Quick add text…" />
              <label title="Save parsed task to database"><input type="checkbox" checked={quickCommit} onChange={(e) => setQuickCommit(e.target.checked)} /> Persist</label>
              <button onClick={runQuick}>Parse</button>
            </div>
            {quickResult && <p className="success-inline">{quickResult}</p>}
            {quickError && <p className="error-inline">{quickError}</p>}
            <div className="row-group">
              <input value={newTask.title} onChange={(e) => setNewTask({ ...newTask, title: e.target.value })} placeholder="New task title" onKeyDown={(e) => e.key === 'Enter' && addTask()} />
              <input type="datetime-local" value={newTask.due_at} onChange={(e) => setNewTask({ ...newTask, due_at: e.target.value })} />
              <select value={newTask.priority} onChange={(e) => setNewTask({ ...newTask, priority: Number(e.target.value) })}>
                <option value={1}>P1 Urgent</option>
                <option value={2}>P2 Normal</option>
                <option value={3}>P3 Low</option>
                <option value={4}>P4 Someday</option>
              </select>
              <button onClick={addTask} disabled={!newTask.title.trim() || !!loading['task-create']}>{loading['task-create'] ? 'Adding…' : 'Add'}</button>
            </div>
            {taskCreateMsg && <p className="success-inline">{taskCreateMsg}</p>}
            {taskCreateErr && <p className="error-inline">{taskCreateErr}</p>}
            <ul className="task-list">
              {orderedTasks.map((t) => (
                <li key={t.id} className={`task-item ${t.done ? 'is-done' : ''} ${linkedSourceId === t.id ? 'is-highlighted' : ''}`}>
                  {taskEditId === t.id ? (
                    <>
                      <span className={`priority p${taskEdit.priority}`}>P{taskEdit.priority}</span>
                      <input className="task-title" value={taskEdit.title} onChange={(e) => setTaskEdit({ ...taskEdit, title: e.target.value })} />
                      <input className="task-due" type="datetime-local" value={taskEdit.due_at} onChange={(e) => setTaskEdit({ ...taskEdit, due_at: e.target.value })} />
                      <select value={taskEdit.priority} onChange={(e) => setTaskEdit({ ...taskEdit, priority: Number(e.target.value) })}>
                        <option value={1}>P1</option>
                        <option value={2}>P2</option>
                        <option value={3}>P3</option>
                        <option value={4}>P4</option>
                      </select>
                      <button onClick={saveTaskEdit} disabled={!taskEdit.title.trim()}>Save</button>
                      <button onClick={() => setTaskEditId('')}>Cancel</button>
                    </>
                  ) : (
                    <>
                      <span className={`priority p${t.priority}`}>P{t.priority}</span>
                      <span className="task-title">{t.title}</span>
                      <span className="task-due">{t.due_at ? (() => { const d = new Date(t.due_at); return isNaN(d.getTime()) ? t.due_at : d.toLocaleDateString(); })() : 'No due date'}</span>
                      <span className="task-state">{t.done ? 'Done' : 'Open'}</span>
                      <button onClick={() => completeTask(t.id)} disabled={!!t.done}>{t.done ? '✓' : 'Complete'}</button>
                      <button onClick={() => beginEditTask(t)}>Edit</button>
                      <button onClick={() => deleteTask(t.id)}>Delete</button>
                    </>
                  )}
                </li>
              ))}
              {orderedTasks.length === 0 && !loading.tasks && <li className="empty">No tasks — add one above</li>}
            </ul>
          </>
        )}
        {compact && <p>Active: {tasks.filter((t) => !t.done).length} / {tasks.length}</p>}
      </BoxCard>
    );
  }

  function ZoesCalBox({ compact = false }: { compact?: boolean }) {
    return (
      <BoxCard title="ZoesCal" compact={compact} testId="box-zoescal">
        <div className="row-group" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <p style={{ margin: '0 0 6px 0' }}>Calendar now lives in ZoesCal as a separate app.</p>
            {!compact && <p className="task-due" style={{ margin: 0 }}>Open the dedicated day, week, and month views on port 5174.</p>}
          </div>
          <button onClick={openZoesCal}>Open ZoesCal</button>
        </div>
      </BoxCard>
    );
  }


  function FocusBox({ compact = false }: { compact?: boolean }) {
    return (
      <BoxCard title="Focus / Pomodoro" compact={compact} testId="box-focus">
        {loading.focus && <p className="loading">Loading…</p>}
        {panelErrors.focus && <p className="error-inline">{panelErrors.focus}</p>}
        {!compact && (
          <div className="row-group">
            <button onClick={startPomodoro}>▶ Start 25</button>
            <button onClick={() => jpost('/focus/pause').then(() => jget('/focus/status').then((data) => { setFocus(data); clearPanelError('focus'); })).catch(apiErr('focus', 'Pause'))}>⏸ Pause</button>
            <button onClick={() => jpost('/focus/resume').then(() => jget('/focus/status').then((data) => { setFocus(data); clearPanelError('focus'); })).catch(apiErr('focus', 'Resume'))}>▶ Resume</button>
            <button onClick={() => jpost('/focus/complete').then(() => jget('/focus/status').then((data) => { setFocus(data); clearPanelError('focus'); })).catch(apiErr('focus', 'Complete'))}>⏹ Done</button>
          </div>
        )}
        <p>Status: <strong>{focus?.status || 'idle'}</strong> • {countdown}</p>
      </BoxCard>
    );
  }

  function AlarmPlayerBox({ compact = false }: { compact?: boolean }) {
    const alarmTimeValue = /^\d{1,2}:\d{2}$/.test(alarmForm.at) ? alarmForm.at : '07:30';
    return (
      <BoxCard title="Alarm / Player" compact={compact} testId="box-alarm-player">
        {loading.player && <p className="loading">Loading…</p>}
        {panelErrors['alarm-player'] && <p className="error-inline">{panelErrors['alarm-player']}</p>}
        {panelErrors.player && <p className="error-inline">{panelErrors.player}</p>}
        {alarmFiring && <p style={{ color: '#e67e22', fontWeight: 600 }}>🔔 Alarm firing…</p>}
        {compact && (
          <div className="row-group" style={{ marginBottom: 8 }}>
            <button onClick={() => navigate('alarm-player')}>Add alarm</button>
          </div>
        )}
        {!compact && (
          <>
            <div className="row-group">
              <input
                type="time"
                value={alarmTimeValue}
                onChange={(e) => setAlarmForm({ ...alarmForm, at: e.target.value })}
                onInput={(e) => setAlarmForm({ ...alarmForm, at: (e.target as HTMLInputElement).value })}
              />
              <input value={alarmForm.title} onChange={(e) => setAlarmForm({ ...alarmForm, title: e.target.value })} placeholder="Label" />
            </div>
            <div className="row-group">
              <input value={alarmForm.tts_text} onChange={(e) => setAlarmForm({ ...alarmForm, tts_text: e.target.value })} placeholder="TTS message (what to say aloud)" style={{ flex: 2 }} />
            </div>
            <div className="row-group">
              <input value={alarmForm.youtube_link} onChange={(e) => setAlarmForm({ ...alarmForm, youtube_link: e.target.value })} placeholder="YouTube link (optional)" style={{ flex: 2 }} />
              <button onClick={createAlarm}>Save alarm</button>
            </div>
            <div className="row-group">
              <input value={player.queueInput} onChange={(e) => setPlayer({ ...player, queueInput: e.target.value })} placeholder="track1,track2" />
              <button onClick={async () => {
                const items = player.queueInput.split(',').map((x: string) => x.trim()).filter(Boolean);
                const out = await jpost('/player/queue', items).catch(apiErr('player', 'Queue'));
                if (out) setPlayer({ ...player, queue: out.items });
              }}>Set queue</button>
            </div>
            <div className="alarms-section" style={{ marginTop: 12 }}>
              <h5 style={{ margin: '0 0 8px 0', fontSize: '0.9em' }}>Alarms</h5>
              {loading.alarms ? (
                <p className="loading">Loading alarms…</p>
              ) : alarms.length === 0 ? (
                <p className="muted" style={{ fontSize: '0.9em' }}>No alarms set</p>
              ) : (
                  <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: '0.9em' }}>
                    {alarms.map(a => (
                    <li key={a.id} className={linkedSourceId === a.id ? 'is-highlighted' : ''} style={{ padding: '4px 0', borderBottom: '1px solid #eee', display: 'flex', alignItems: 'center', gap: 8 }}>
                      <strong>{a.alarm_time}</strong>
                      {a.title && ` – ${a.title}`}
                      {a.tts_text && <span style={{ color: '#888', fontSize: '0.85em' }}> 🔊 {a.tts_text}</span>}
                      {a.muted && ' (muted)'}
                      {!a.enabled && ' (disabled)'}
                      <button
                        style={{ marginLeft: 'auto', fontSize: '0.8em', padding: '2px 8px' }}
                        onClick={async () => {
                          try {
                            const res = await jpost(`/alarms/${a.id}/trigger`);
                            const actions = res.actions || [];
                            const ttsAction = actions.find((x: any) => x.type === 'tts');
                            const tts = ttsAction?.text || a.tts_text || a.title || 'Alarm';
                            fireAlarmAudio(tts, a.youtube_link || '', a.id);
                          } catch (err: any) { apiErr('alarm-player', 'Trigger')(err); }
                        }}
                      >Test ▶</button>
                      <button
                        style={{ fontSize: '0.8em', padding: '2px 8px', color: '#c0392b', borderColor: '#c0392b' }}
                        onClick={async () => {
                          try {
                            await jdelete(`/alarms/${a.id}`);
                            await refreshAlarms();
                          } catch (err: any) { apiErr('alarm-player', 'Delete alarm')(err); }
                        }}
                      >✕</button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}
        <p>Queue: {player.queue.length} • Jobs: {player.jobs.length}{alarmResult ? ` • Alarm saved ✓` : ''}</p>
      </BoxCard>
    );
  }

  function HabitsBox({ compact = false }: { compact?: boolean }) {
    const days = habitsWeekly?.days || [];
    const habitNames: string[] = habitsWeekly?.habits || [];
    const uniqueHabitList = [...new Set(habitList)];

    return (
      <BoxCard title="Habits" compact={compact} testId="box-habits">
        {loading.habits && <p className="loading">Loading…</p>}
        {panelErrors.habits && <p className="error-inline">{panelErrors.habits}</p>}
        {!compact && (
          <>
            <div className="row-group" style={{ marginBottom: 8 }}>
              {uniqueHabitList.map((name) => (
                <span key={name} style={{ display: 'inline-flex', alignItems: 'center', gap: 2 }}>
                  <button className={linkedTitle === name ? 'is-highlighted' : ''} onClick={() => jpost(`/habits/checkin?name=${name}&done=true`).then(refreshHabits).catch(apiErr('habits', 'Checkin'))}>
                    ✓ {name}
                  </button>
                  <button
                    onClick={async () => {
                      if (!confirm(`Delete habit "${name}" and all its logs?`)) return;
                      await jdelete(`/habits/${encodeURIComponent(name)}`).catch(apiErr('habits', 'Delete'));
                      await refreshHabits();
                    }}
                    style={{ fontSize: '0.75em', padding: '2px 5px', color: '#c0392b', borderColor: '#c0392b' }}
                  >✕</button>
                </span>
              ))}
            </div>
            <div className="row-group" style={{ marginBottom: 8 }}>
              <input
                value={newHabit}
                onChange={(e) => setNewHabit(e.target.value)}
                placeholder="New habit name"
                onKeyDown={async (e) => {
                  if (e.key === 'Enter') await addHabit();
                }}
              />
              <button onClick={addHabit} disabled={!newHabit.trim() || !!loading['habit-add']}>
                {loading['habit-add'] ? 'Adding…' : '+ Add'}
              </button>
            </div>
            {habitsWeekly && (
              <p className="habits-summary" style={{marginBottom: 8}}>
                Completion: {habitsWeekly.completion_pct}% • Consistency: {habitsWeekly.consistency}
              </p>
            )}
            {days.length > 0 ? (
              <table className="habits-grid">
                <thead>
                  <tr><th>Habit</th>{days.map((d: any) => <th key={d.date}>{d.label || d.date?.slice(5)}</th>)}</tr>
                </thead>
                <tbody>
                  {habitNames.map((h: string) => (
                    <tr key={h} className={linkedTitle === h ? 'is-highlighted' : ''}>
                      <td>{h}</td>
                      {days.map((d: any) => {
                        const done = d.checkins?.[h];
                        return <td key={d.date} className={done ? 'done' : 'miss'}>{done ? '✓' : '·'}</td>;
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              !loading.habits && <p className="empty">Add a habit above and check in to see your streak grid</p>
            )}
          </>
        )}
        {compact && <p>Weekly data {habitsWeekly ? '✓' : '—'}</p>}
      </BoxCard>
    );
  }

  function EisenhowerKanbanBox({ compact = false }: { compact?: boolean }) {
    const QUADS = ['do', 'schedule', 'delegate', 'eliminate'] as const;
    const meta: Record<string, { label: string; hint: string }> = {
      do: { label: '🔴 Do', hint: 'Urgent + Important' },
      schedule: { label: '🟡 Schedule', hint: 'Not urgent + Important' },
      delegate: { label: '🟢 Delegate', hint: 'Urgent + Less important' },
      eliminate: { label: '⚪ Eliminate', hint: 'Not urgent + Less important' },
    };
    return (
      <BoxCard title="Eisenhower / Kanban" compact={compact} testId="box-eisenhower-kanban">
        {loading.matrix && <p className="loading">Loading…</p>}
        {panelErrors.matrix && <p className="error-inline">{panelErrors.matrix}</p>}
        {compact ? (
          <p>Quadrants: {QUADS.map((q) => matrix?.[q]?.length || 0).join(' / ')}</p>
        ) : (
          <div className="matrix-grid">
            {QUADS.map((q) => (
              <div key={q} className={`matrix-cell matrix-${q}`}>
                <strong>{meta[q].label}</strong>
                <p className="task-due">{meta[q].hint}</p>
                <ul>
                  {(matrix?.[q] || []).map((t: any) => <li key={t.id}>{t.title || 'Untitled task'}</li>)}
                  {(matrix?.[q] || []).length === 0 && <li className="empty">No tasks</li>}
                </ul>
              </div>
            ))}
          </div>
        )}
      </BoxCard>
    );
  }

  function ReviewAnkiBox({ compact = false }: { compact?: boolean }) {
    return (
      <BoxCard title="Review / Anki" compact={compact} testId="box-review-anki">
        {loading.review && <p className="loading">Loading…</p>}
        {panelErrors.review && <p className="error-inline">{panelErrors.review}</p>}
        {!compact && (
          <>
            <div className="row-group" style={{ marginBottom: 8 }}>
              <select value={selectedDeck} onChange={(e) => { setSelectedDeck(e.target.value); setShowBack(false); }}>
                <option value="">— select deck —</option>
                {decks.map((d) => <option key={d.id} value={String(d.id)}>{d.name}</option>)}
              </select>
              <input value={newDeckName} onChange={(e) => setNewDeckName(e.target.value)} placeholder="New deck name" onKeyDown={(e) => e.key === 'Enter' && createDeck()} />
              <button onClick={createDeck} disabled={!newDeckName.trim() || !!loading['deck-create']}>
                {loading['deck-create'] ? 'Creating…' : '+ Deck'}
              </button>
              {selectedDeck && (
                <>
                  <label style={{ cursor: 'pointer', fontSize: '0.85em', padding: '4px 8px', border: '1px solid var(--border)', borderRadius: 4 }} title="Import CSV (front,back,tags)">
                    📥 CSV
                    <input type="file" accept=".csv,.tsv" style={{ display: 'none' }} onChange={async (e) => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      const content = await file.text();
                      const fmt = file.name.endsWith('.tsv') ? 'tsv' : 'csv';
                      try {
                        const res = await jpost(`/review/import?deck_id=${selectedDeck}&fmt=${fmt}`, { content });
                        alert(`Imported ${res.imported ?? '?'} cards`);
                        await getReviewSession();
                      } catch (err: any) { apiErr('review', 'Import CSV')(err); }
                      e.target.value = '';
                    }} />
                  </label>
                  <label style={{ cursor: 'pointer', fontSize: '0.85em', padding: '4px 8px', border: '1px solid var(--border)', borderRadius: 4 }} title="Import .apkg (best-effort; limited compatibility)">
                    📦 .apkg (beta)
                    <input type="file" accept=".apkg" style={{ display: 'none' }} onChange={async (e) => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      const form = new FormData();
                      form.append('file', file);
                      try {
                        const res = await fetch(`${BASE}/review/import-apkg?deck_id=${selectedDeck}`, { method: 'POST', body: form });
                        const data = await res.json();
                        if (!res.ok) throw new Error(data.detail?.msg || JSON.stringify(data));
                        alert(`Imported ${data.imported ?? '?'} cards from ${file.name}`);
                        await getReviewSession();
                      } catch (err: any) { apiErr('review', 'Import apkg')(err); }
                      e.target.value = '';
                    }} />
                  </label>
                </>
              )}
            </div>
            {selectedDeck && (
              <div className="row-group" style={{ marginBottom: 8 }}>
                <input value={newCard.front} onChange={(e) => setNewCard({ ...newCard, front: e.target.value })} placeholder="Front" />
                <input value={newCard.back} onChange={(e) => setNewCard({ ...newCard, back: e.target.value })} placeholder="Back" />
                <input value={newCard.tags} onChange={(e) => setNewCard({ ...newCard, tags: e.target.value })} placeholder="Tags (comma-separated)" />
                <button onClick={addCard}>+ Card</button>
              </div>
            )}
            {currentCard ? (
              <div className="review-card" data-testid="review-card">
                <p><strong>Front:</strong> {currentCard.front}</p>
                {showBack ? (
                  <>
                    <p><strong>Back:</strong> {currentCard.back}</p>
                    {currentCard.tags?.length > 0 && <p><em>Tags: {currentCard.tags.join(', ')}</em></p>}
                    <div className="review-actions">
                      <button onClick={() => rateCard('again')}>1 Again</button>
                      <button onClick={() => rateCard('hard')}>2 Hard</button>
                      <button onClick={() => rateCard('good')}>3 Good</button>
                      <button onClick={() => rateCard('easy')}>4 Easy</button>
                    </div>
                  </>
                ) : (
                  <button onClick={() => setShowBack(true)}>Show answer</button>
                )}
              </div>
            ) : (
              !loading.review && <p className="empty">No cards due — add cards above or all caught up 🎉</p>
            )}
          </>
        )}
        <p>State: {reviewState?.state || '—'} • Interval: {reviewState?.interval ?? '—'}d</p>
      </BoxCard>
    );
  }

  function CommandsBox({ compact = false }: { compact?: boolean }) {
    return (
      <BoxCard title="Commands" compact={compact} testId="box-commands">
        {!compact && (
          <div className="row-group">
            <input value={cmd} onChange={(e) => setCmd(e.target.value)} placeholder="add task …" onKeyDown={(e) => e.key === 'Enter' && runCmd()} />
            <button onClick={runCmd}>Run</button>
          </div>
        )}
        {cmdError && <p className="error-inline">{cmdError}</p>}
        {!compact && history.slice(0, 5).map((h, i) => (
          <p key={i} className="history-item"><code>{h.text}</code> → <em>{h.intent}</em></p>
        ))}
        <p>History: {history.length} entries</p>
      </BoxCard>
    );
  }

  return (
    <div className="layout" role="application">
      {globalError && (
        <div className="global-error" role="alert">
          ⚠ {globalError}
          <button onClick={() => setGlobalError('')}>✕</button>
        </div>
      )}
      <aside className="sidebar" role="navigation" aria-label="Main navigation">
        <div className="app-brand">
          <img className="app-logo" src="/zoe-logo.svg" alt="Zoe'sTM logo" />
          <h3>Zoe'sTM</h3>
        </div>
        {ROUTES.map((r) => (
          <div key={r.key}>
            <button className={route === r.key ? 'active' : ''} onClick={() => navigate(r.key)}>{r.label}</button>
          </div>
        ))}
      </aside>
      <main className="main" id="main-content" role="main">
        <div className="command-bar" aria-live="polite">
          <span className="sr-only">Global Command Bar (BPC)</span>
          ⌘ <input value={cmd} onChange={(e) => setCmd(e.target.value)} placeholder="add task …" aria-label="Command input" onKeyDown={(e) => e.key === 'Enter' && runCmd()} />
          <button onClick={runCmd}>Run</button>
          <button onClick={openZoesCal}>Launch ZoesCal</button>
        </div>
        <div className="status-strip" aria-live="off">
          Route: /{route} • Focus: {focus?.status || 'idle'} • API: {apiMeta?.info?.title || 'offline'}
        </div>

        {route === 'overview' && (
          <section>
            <h4>Overview Grid</h4>
            <div className="overview-grid" data-testid="overview-grid">
              {TasksBox({ compact: true })}
              {ZoesCalBox({ compact: true })}
              {FocusBox({ compact: true })}
              {AlarmPlayerBox({ compact: true })}
              {HabitsBox({ compact: true })}
              {EisenhowerKanbanBox({ compact: true })}
              {ReviewAnkiBox({ compact: true })}
              {CommandsBox({ compact: true })}
            </div>
          </section>
        )}
        {route === 'tasks' && TasksBox({})}
        {route === 'focus' && FocusBox({})}
        {route === 'alarm-player' && AlarmPlayerBox({})}
        {route === 'habits' && HabitsBox({})}
        {route === 'eisenhower-kanban' && EisenhowerKanbanBox({})}
        {route === 'review-anki' && ReviewAnkiBox({})}
        {route === 'commands' && CommandsBox({})}
      </main>
    </div>
  );
}
