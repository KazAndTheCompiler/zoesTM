import { useState, useMemo } from 'react';
import type { CalEntry } from '../types';
import styles from './MonthView.module.css';
import { useSwipe } from '../hooks/useSwipe';
import { haptic } from '../utils/haptic';
import { openZoestmEntry } from '../utils/zoestmLink';

interface Props { 
  entries: CalEntry[]; 
  loading?: boolean;
  monthOffset?: number;
  setMonthOffset?: (offset: number) => void;
}

const DOW = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

function sourceColor(source?: string): string {
  const el = document.querySelector('[data-skin]') || document.documentElement;
  const s = getComputedStyle(el);
  if (source === 'task' || source === 'zoestm-task') return s.getPropertyValue('--task-default').trim();
  if (source === 'alarm')  return s.getPropertyValue('--reminder-default').trim();
  if (source === 'habit')  return s.getPropertyValue('--color-success').trim();
  return s.getPropertyValue('--event-default').trim();
}

function provenanceLabel(source?: string): string | null {
  if (source === 'task') return 'TM task';
  if (source === 'habit') return 'TM habit';
  if (source === 'alarm') return 'TM alarm';
  return null;
}

function fmt12(d: Date) {
  let h = d.getHours(), m = d.getMinutes();
  const ap = h >= 12 ? 'pm' : 'am';
  h = h % 12 || 12;
  return `${h}:${String(m).padStart(2, '0')}${ap}`;
}

export default function MonthView({ entries, loading, monthOffset: externalMonthOffset, setMonthOffset: externalSetMonthOffset }: Props) {
  const [internalMonthOffset, setInternalMonthOffset] = useState(0);
  const monthOffset = externalMonthOffset ?? internalMonthOffset;
  const setMonthOffset = externalSetMonthOffset ?? setInternalMonthOffset;
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const now = new Date();

  const { onTouchStart, onTouchEnd } = useSwipe({
    onSwipeLeft: () => setMonthOffset(o => o + 1),
    onSwipeRight: () => setMonthOffset(o => o - 1),
  });
  
  const getDisplayDate = (offset: number) => {
    const d = new Date(now);
    d.setMonth(d.getMonth() + offset);
    return d;
  };

  const displayDate = getDisplayDate(monthOffset);
  const year = displayDate.getFullYear();
  const month = displayDate.getMonth();
  const firstDow = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const entriesByDate = useMemo(() => {
    const map: Record<string, CalEntry[]> = {};
    entries.forEach(e => {
      if (!e._d) return;
      const k = e._d.toISOString().slice(0, 10);
      (map[k] = map[k] || []).push(e);
    });
    return map;
  }, [entries]);

  const dotsByDate: Record<string, string[]> = {};
  entries.forEach(e => {
    if (!e._d) return;
    const k = e._d.toISOString().slice(0, 10);
    (dotsByDate[k] = dotsByDate[k] || []).push(sourceColor(e.source));
  });

  const selectedDateStr = selectedDate 
    ? `${year}-${String(month + 1).padStart(2, '0')}-${String(selectedDate).padStart(2, '0')}`
    : null;
  const selectedEvents = selectedDateStr ? entriesByDate[selectedDateStr] || [] : [];
  const selectedDateObj = selectedDate ? new Date(year, month, parseInt(selectedDate)) : null;

  const cells: (number | null)[] = [
    ...Array(firstDow).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];

  const monthLabel = displayDate.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });

  const isCurrentMonth = displayDate.getMonth() === now.getMonth() && displayDate.getFullYear() === now.getFullYear();

  const monthEventCount = Object.values(entriesByDate).flat().length;

  return (
    <div className={styles.wrap} onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
      <div className={styles.navRow}>
        <button 
          className={styles.navBtn} 
          onClick={() => setMonthOffset(o => o - 1)}
          aria-label="Previous month"
        >‹</button>
        <span className={styles.navTitle}>{monthLabel}</span>
        <button 
          className={styles.navBtn} 
          onClick={() => setMonthOffset(o => o + 1)}
          aria-label="Next month"
        >›</button>
        {!isCurrentMonth && (
          <button 
            className={styles.todayBtn} 
            onClick={() => setMonthOffset(0)}
          >Today</button>
        )}
      </div>

      <div className={styles.dowRow}>
        {DOW.map(d => <div key={d} className={styles.dow}>{d}</div>)}
      </div>

      {loading && (
        <div className={styles.grid}>
          {Array(35).fill(null).map((_, i) => (
            <div key={i} className={styles.cell}>
              <div className={styles.skeletonCell}>
                <div className={styles.skeletonNum} />
                <div className={styles.skeletonDots}>
                  <div className={styles.skeletonDot} />
                  <div className={styles.skeletonDot} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && (
        <div className={styles.grid}>
          {cells.map((day, i) => {
            if (day === null) return <div key={`blank-${i}`} />;
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const isToday = isCurrentMonth && day === now.getDate();
            const dots = (dotsByDate[dateStr] || []).slice(0, 3);
            const eventCount = dotsByDate[dateStr]?.length || 0;
            const hasMore = eventCount > 3;

            return (
              <div 
                key={day} 
                className={`${styles.cell} ${isToday ? styles.today : ''}`}
                onClick={() => { haptic('light'); setSelectedDate(String(day)); }}
                role="button"
                tabIndex={0}
                onKeyDown={(k) => k.key === 'Enter' && setSelectedDate(String(day))}
                aria-label={`${displayDate.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })} ${day}${eventCount > 0 ? `, ${eventCount} events` : ''}`}
              >
                <span className={styles.num}>{day}</span>
                {dots.length > 0 && (
                  <div className={styles.dots}>
                    {dots.map((c, di) => (
                      <div key={di} className={styles.dot} style={{ background: c }} />
                    ))}
                    {hasMore && <span className={styles.moreBadge}>+{eventCount - 3}</span>}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!loading && monthEventCount === 0 && (
        <div className={styles.empty}>
          <span className={styles.emptyIcon}>📅</span>
          No events this month — add something below
        </div>
      )}

      {selectedDate && selectedDateObj && (
        <div className={styles.popover} onClick={() => setSelectedDate(null)}>
          <div className={styles.popoverCard} onClick={(e) => e.stopPropagation()}>
            <button className={styles.popoverClose} onClick={() => setSelectedDate(null)} aria-label="Close">×</button>
            <div className={styles.popoverTitle}>
              {selectedDateObj.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })}
            </div>
            {selectedEvents.length === 0 ? (
              <div className={styles.popoverEmpty}>No events</div>
            ) : (
              <div className={styles.popoverEvents}>
                {selectedEvents
                  .sort((a, b) => (a._d?.getTime() || 0) - (b._d?.getTime() || 0))
                  .map(e => (
                    <div key={e.id} className={styles.popoverEvent}>
                      <div 
                        className={styles.popoverEventDot}
                        style={{ background: sourceColor(e.source) }}
                      />
                      <span className={styles.popoverEventTime}>
                        {e._d && fmt12(e._d)}
                      </span>
                      <span className={styles.popoverEventTitle}>{e.title}</span>
                      {provenanceLabel(e.source) && (
                        <button
                          type="button"
                          className={styles.popoverSourceBadge}
                          onClick={() => openZoestmEntry(e)}
                          aria-label={`Open ${e.title} in ZoesTM`}
                        >
                          {provenanceLabel(e.source)}
                        </button>
                      )}
                      {e.sync_status === 'pending' && <span className={styles.popoverSyncPending} title="Pending sync">○</span>}
                      {e.sync_status === 'conflict' && <span className={styles.popoverSyncConflict} title="Sync conflict">⚠</span>}
                      {e.sync_status === 'error' && <span className={styles.popoverSyncError} title="Sync error">✕</span>}
                      {e.recurrence && <span className={styles.popoverRecurring} title={`Repeats ${e.recurrence}`}>↻</span>}
                      {e.read_only && <span className={styles.popoverEventBadge}>read-only</span>}
                    </div>
                  ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
