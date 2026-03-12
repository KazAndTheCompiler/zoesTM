import { useState, useEffect, useRef } from 'react';
import type { CalEntry } from '../types';
import styles from './DayView.module.css';
import './DayView.print.css';
import { useSwipe } from '../hooks/useSwipe';
import { usePullToRefresh } from '../hooks/usePullToRefresh';
import { useLongPress } from '../hooks/useLongPress';
import { haptic } from '../utils/haptic';
import { canOpenZoestm, openZoestmEntry } from '../utils/zoestmLink';
import NowLine from './NowLine';

interface Props { 
  entries: CalEntry[]; 
  loading?: boolean; 
  onRefresh?: () => void;
  dayOffset?: number;
  setDayOffset?: (offset: number) => void;
  onLongPressHour?: (time: string) => void;
}

const HOURS = Array.from({ length: 24 }, (_, i) => i);

function fmt12(d: Date) {
  let h = d.getHours(), m = d.getMinutes();
  const ap = h >= 12 ? 'pm' : 'am';
  h = h % 12 || 12;
  return `${h}:${String(m).padStart(2, '0')}${ap}`;
}

function hourLabel(h: number) {
  if (h === 0)  return '12am';
  if (h < 12)   return `${h}am`;
  if (h === 12) return '12pm';
  return `${h - 12}pm`;
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
  if (source === 'task') return 'TM task';
  if (source === 'habit') return 'TM habit';
  if (source === 'alarm') return 'TM alarm';
  return null;
}

export default function DayView({ entries, loading, onRefresh, dayOffset: externalDayOffset, setDayOffset: externalSetDayOffset, onLongPressHour }: Props) {
  const [selected, setSelected] = useState<CalEntry | null>(null);
  const [internalDayOffset, setInternalDayOffset] = useState(0);
  const dayOffset = externalDayOffset ?? internalDayOffset;
  const setDayOffset = externalSetDayOffset ?? setInternalDayOffset;
  const scrollRef = useRef<HTMLDivElement>(null);

  const { onTouchStart, onTouchEnd } = useSwipe({
    onSwipeLeft: () => setDayOffset(o => o + 1),
    onSwipeRight: () => setDayOffset(o => o - 1),
  });

  const { isPulling, pullDistance, onTouchStart: onPTRStart, onTouchMove: onPTRMove, onTouchEnd: onPTREnd } = usePullToRefresh({
    onRefresh: () => onRefresh?.(),
  });

  function handleLongPressHour(hour: number) {
    haptic('medium');
    const d = new Date(displayDate);
    d.setHours(hour, 0, 0, 0);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const dStr = String(d.getDate()).padStart(2, '0');
    const h = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    onLongPressHour?.(`${y}-${m}-${dStr}T${h}:${min}`);
  }
  
  const getDisplayDate = (offset: number) => {
    const d = new Date();
    d.setDate(d.getDate() + offset);
    d.setHours(0, 0, 0, 0);
    return d;
  };

  const displayDate = getDisplayDate(dayOffset);
  const displayDateStr = displayDate.toISOString().slice(0, 10);
  const now = new Date();
  const nowStr = now.toISOString().slice(0, 10);
  const isToday = displayDateStr === nowStr;

  const slots: Record<number, CalEntry[]> = {};
  entries.forEach(e => {
    if (!e._d) return;
    if (e._d.toISOString().slice(0, 10) !== displayDateStr) return;
    const k = e._d.getHours();
    (slots[k] = slots[k] || []).push(e);
  });

  useEffect(() => {
    const target = scrollRef.current?.querySelector(`[data-hour="${Math.max(0, isToday ? now.getHours() - 1 : 8)}"]`);
    target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [dayOffset, isToday]);

  const todayCount = Object.values(slots).flat().length;

  return (
    <div 
      className={styles.wrap} 
      ref={scrollRef} 
      onTouchStart={(e) => { onTouchStart(e); onPTRStart(e); }} 
      onTouchMove={onPTRMove}
      onTouchEnd={(e) => { onTouchEnd(e); onPTREnd(); }}
    >
      {isPulling && (
        <div className={styles.pullIndicator} style={{ height: `${pullDistance}px` }}>
          <div className={styles.pullSpinner} style={{ opacity: Math.min(pullDistance / 60, 1) }}>↻</div>
        </div>
      )}
      <div className={styles.navRow}>
        <button 
          className={styles.navBtn} 
          onClick={() => setDayOffset(o => o - 1)}
          aria-label="Previous day"
        >‹</button>
        <div className={styles.dateInfo}>
          <div className={styles.dateBig}>
            {displayDate.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
          </div>
          <div className={styles.dateSub}>
            {displayDate.toLocaleDateString(undefined, { weekday: 'long' })}
            {' · '}{todayCount} event{todayCount !== 1 ? 's' : ''}
          </div>
        </div>
        <button 
          className={styles.navBtn} 
          onClick={() => setDayOffset(o => o + 1)}
          aria-label="Next day"
        >›</button>
        {!isToday && (
          <button 
            className={styles.todayBtn} 
            onClick={() => setDayOffset(0)}
          >Today</button>
        )}
      </div>

      {loading && (
        <div className={styles.skeleton}>
          {HOURS.slice(0, 12).map(h => (
            <div key={h} className={styles.skeletonRow}>
              <div className={styles.skeletonLabel} />
              <div className={styles.skeletonContent}>
                <div className={styles.skeletonChip} style={{ width: `${60 + Math.random() * 40}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && HOURS.map(h => {
        const isNow = isToday && h === now.getHours();
        const evs = slots[h] || [];
        const { onTouchStart, onTouchEnd, onTouchMove } = useLongPress({
          onLongPress: () => handleLongPressHour(h),
        });
        return (
          <div
            key={h}
            className={`${styles.hourBlock} ${isNow ? styles.nowHour : ''}`}
            data-hour={h}
            onTouchStart={onTouchStart}
            onTouchEnd={onTouchEnd}
            onTouchMove={onTouchMove}
          >
            <div className={styles.hourLabel}>{hourLabel(h)}</div>
            <div className={styles.hourEvents}>
              {evs.map((e, i) => (
                <div
                  key={e.id}
                  className={styles.chip}
                  onClick={() => { haptic('light'); setSelected(e); }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(k) => k.key === 'Enter' && setSelected(e)}
                  aria-label={`${e.title} at ${fmt12(e._d!)}`}
                  style={{
                    '--event-color': sourceColor(e.source),
                    animationDelay: `${i * 40}ms`,
                  } as React.CSSProperties}
                >
                  <span className={styles.chipTime}>
                    {fmt12(e._d!)}
                    {e.end_at && <span className={styles.chipEndTime}> – {fmt12(new Date(e.end_at))}</span>}
                  </span>
                  <span className={styles.chipTitle}>{e.title}</span>
                  {provenanceLabel(e.source) && (
                    <button
                      type="button"
                      className={styles.sourceBadge}
                      onClick={(evt) => { evt.stopPropagation(); openZoestmEntry(e); }}
                      aria-label={`Open ${e.title} in ZoesTM`}
                    >
                      {provenanceLabel(e.source)}
                    </button>
                  )}
                  {e.sync_status === 'pending' && <span className={styles.syncPending} title="Pending sync">○</span>}
                  {e.sync_status === 'conflict' && <span className={styles.syncConflict} title="Sync conflict">⚠</span>}
                  {e.sync_status === 'error' && <span className={styles.syncError} title="Sync error">✕</span>}
                  {e.recurrence && <span className={styles.recurring} title={`Repeats ${e.recurrence}`}>↻</span>}
                  {e.read_only && <span className={styles.chipBadge}>read-only</span>}
                </div>
              ))}
            </div>
            {isNow && <NowLine isToday={isToday} />}
          </div>
        );
      })}

      {todayCount === 0 && (
        <div className={styles.empty}>
          <span className={styles.emptyIcon}>☀️</span>
          Clear day — add something below
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
                  {provenanceLabel(selected.source)}
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
