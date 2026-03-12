import { useState } from 'react';
import type { CalEntry } from '../types';
import styles from './WeekView.module.css';
import { useSwipe } from '../hooks/useSwipe';
import { haptic } from '../utils/haptic';
import { canOpenZoestm, openZoestmEntry } from '../utils/zoestmLink';

interface Props { 
  entries: CalEntry[]; 
  loading?: boolean;
  weekOffset?: number;
  setWeekOffset?: (offset: number) => void;
}

const HOURS = Array.from({ length: 24 }, (_, i) => i);
const DOW = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

function hourLabel(h: number) {
  if (h === 0)  return '12a';
  if (h < 12)   return `${h}a`;
  if (h === 12) return '12p';
  return `${h - 12}p`;
}

function fmt12(d: Date) {
  let h = d.getHours(), m = d.getMinutes();
  const ap = h >= 12 ? 'pm' : 'am';
  h = h % 12 || 12;
  return `${h}:${String(m).padStart(2, '0')}${ap}`;
}

function sourceColor(source?: string): string {
  const el = document.querySelector('[data-skin]') || document.documentElement;
  const s = getComputedStyle(el);
  if (source === 'task' || source === 'zoestm-task') return s.getPropertyValue('--task-default').trim();
  if (source === 'alarm')  return s.getPropertyValue('--reminder-default').trim();
  if (source === 'habit')  return s.getPropertyValue('--color-success').trim();
  return s.getPropertyValue('--event-default').trim();
}

function provenanceLabel(source?: string): string | null {
  if (source === 'task') return 'TM';
  if (source === 'habit') return 'TM';
  if (source === 'alarm') return 'TM';
  return null;
}

export default function WeekView({ entries, loading, weekOffset: externalWeekOffset, setWeekOffset: externalSetWeekOffset }: Props) {
  const [internalWeekOffset, setInternalWeekOffset] = useState(0);
  const weekOffset = externalWeekOffset ?? internalWeekOffset;
  const setWeekOffset = externalSetWeekOffset ?? setInternalWeekOffset;
  const [selected, setSelected] = useState<CalEntry | null>(null);

  const { onTouchStart, onTouchEnd } = useSwipe({
    onSwipeLeft: () => setWeekOffset(o => o + 1),
    onSwipeRight: () => setWeekOffset(o => o - 1),
  });
  const now = new Date();
  
  const getWeekStart = (offset: number) => {
    const d = new Date(now);
    d.setDate(d.getDate() - d.getDay() + offset * 7);
    d.setHours(0, 0, 0, 0);
    return d;
  };

  const weekStart = getWeekStart(weekOffset);
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + i);
    return d;
  });

  const formatMonthYear = () => {
    const first = days[0];
    const last = days[6];
    if (first.getMonth() === last.getMonth()) {
      return first.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
    }
    return `${first.toLocaleDateString(undefined, { month: 'short' })} – ${last.toLocaleDateString(undefined, { month: 'short', year: 'numeric' })}`;
  };

  function getWeekNumber(date: Date): number {
    const d = new Date(date);
    d.setHours(0, 0, 0, 0);
    d.setDate(d.getDate() + 4 - (d.getDay() || 7));
    const yearStart = new Date(d.getFullYear(), 0, 1);
    return Math.ceil((((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
  }

  const weekNumber = getWeekNumber(days[0]);

  const slots: Record<string, CalEntry[]> = {};
  entries.forEach(e => {
    if (!e._d) return;
    const k = `${e._d.toISOString().slice(0, 10)}_${e._d.getHours()}`;
    (slots[k] = slots[k] || []).push(e);
  });

  const weekEventCount = Object.values(slots).flat().length;

  return (
    <div className={styles.wrap} onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
      <div className={styles.navRow}>
        <button 
          className={styles.navBtn} 
          onClick={() => setWeekOffset(o => o - 1)}
          aria-label="Previous week"
        >‹</button>
        <div className={styles.navTitleGroup}>
          <span className={styles.navTitle}>{formatMonthYear()}</span>
          <span className={styles.weekNum}>Week {weekNumber}</span>
        </div>
        <button 
          className={styles.navBtn} 
          onClick={() => setWeekOffset(o => o + 1)}
          aria-label="Next week"
        >›</button>
        {weekOffset !== 0 && (
          <button 
            className={styles.todayBtn} 
            onClick={() => setWeekOffset(0)}
          >Today</button>
        )}
      </div>

      <div className={styles.headRow}>
        <div className={styles.cornerCell} />
        {days.map((d, i) => {
          const isToday = d.toDateString() === now.toDateString();
          return (
            <div key={i} className={`${styles.headCell} ${isToday ? styles.today : ''}`}>
              <span className={styles.dow}>{DOW[d.getDay()]}</span>
              <span className={`${styles.dayNum} ${isToday ? styles.todayNum : ''}`}>{d.getDate()}</span>
            </div>
          );
        })}
      </div>

      {loading && (
        <div className={styles.scrollArea}>
          <div className={styles.grid} style={{ gridTemplateColumns: `44px repeat(7, 1fr)` }}>
            {HOURS.slice(0, 10).map(h => (
              <>
                <div key={`lbl-${h}`} className={styles.hourLabel}>{hourLabel(h)}</div>
                {days.map((d, di) => (
                  <div key={`cell-${h}-${di}`} className={styles.cell}>
                    <div className={styles.skeletonDot} />
                  </div>
                ))}
              </>
            ))}
          </div>
        </div>
      )}

      {!loading && (
        <div className={styles.scrollArea}>
          <div className={styles.grid} style={{ gridTemplateColumns: `44px repeat(7, 1fr)` }}>
            {HOURS.map(h => (
              <>
                <div key={`lbl-${h}`} className={styles.hourLabel}>{hourLabel(h)}</div>
                {days.map((d, di) => {
                  const dateStr = d.toISOString().slice(0, 10);
                  const isToday = d.toDateString() === now.toDateString();
                  const isNowHour = isToday && h === now.getHours();
                  const evs = slots[`${dateStr}_${h}`] || [];
                  return (
                    <div
                      key={`cell-${h}-${di}`}
                      className={`${styles.cell} ${isToday ? styles.todayCol : ''} ${isNowHour ? styles.nowHourCol : ''}`}
                    >
                      {evs.map(e => (
                        <div
                          key={e.id}
                          className={styles.dot}
                          style={{ '--ev-color': sourceColor(e.source) } as any}
                          onClick={() => { haptic('light'); setSelected(e); }}
                          role="button"
                          tabIndex={0}
                          onKeyDown={(k) => k.key === 'Enter' && setSelected(e)}
                          aria-label={`${e.title} at ${e._d ? fmt12(e._d) : ''}`}
                        >
                          {provenanceLabel(e.source) && (
                            <button
                              type="button"
                              className={styles.dotSource}
                              onClick={(evt) => { evt.stopPropagation(); openZoestmEntry(e); }}
                              aria-label={`Open ${e.title} in ZoesTM`}
                            >
                              {provenanceLabel(e.source)}
                            </button>
                          )}
                          {e.sync_status === 'pending' && <span className={styles.dotSync} title="Pending sync">○</span>}
                          {e.sync_status === 'conflict' && <span className={styles.dotSync} title="Sync conflict">⚠</span>}
                          {e.sync_status === 'error' && <span className={styles.dotSync} title="Sync error">✕</span>}
                          {e.recurrence && <span className={styles.dotSync} title={`Repeats ${e.recurrence}`}>↻</span>}
                          {e.title}
                        </div>
                      ))}
                    </div>
                  );
                })}
              </>
            ))}
          </div>
        </div>
      )}

      {!loading && weekEventCount === 0 && (
        <div className={styles.empty}>
          <span className={styles.emptyIcon}>📅</span>
          No events this week — add something below
        </div>
      )}

      {selected && (
        <div className={styles.popover} onClick={() => setSelected(null)}>
          <div className={styles.popoverCard} onClick={(e) => e.stopPropagation()}>
            <button className={styles.popoverClose} onClick={() => setSelected(null)} aria-label="Close">×</button>
            <div className={styles.popoverHeader}>
              <div 
                className={styles.popoverDot}
                style={{ background: sourceColor(selected.source) }}
              />
              <div className={styles.popoverTitle}>{selected.title}</div>
            </div>
            <div className={styles.popoverTime}>
              {selected._d && fmt12(selected._d)}
              {selected.end_at && ` – ${fmt12(new Date(selected.end_at))}`}
            </div>
            {selected.source && (
              <div className={styles.popoverMeta}>
                <span className={styles.popoverLabel}>Source</span>
                <span className={styles.popoverValue}>{selected.source}</span>
              </div>
            )}
            {provenanceLabel(selected.source) && canOpenZoestm(selected) && (
              <div className={styles.popoverMeta}>
                <span className={styles.popoverLabel}>Imported from</span>
                <button type="button" className={styles.popoverLink} onClick={() => openZoestmEntry(selected)}>
                  ZoesTM {selected.source}
                </button>
              </div>
            )}
            {selected.read_only && (
              <div className={styles.popoverReadonly}>Read-only</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
