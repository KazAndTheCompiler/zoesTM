import { useState, useRef, useEffect } from 'react';
import styles from './AddBar.module.css';
import { haptic } from '../utils/haptic';

interface Props {
  onAdd: (title: string, startAt: string, endAt?: string) => void;
  initialTime?: string;
}

const TIME_PATTERNS = [
  /^(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)?$/i,
  /^(\d{1,2})\s*(am|pm|AM|PM)$/i,
  /^(\d{2}):(\d{2})$/,
];

function parseTime(input: string): { hours: number; minutes: number } | null {
  const trimmed = input.trim().toLowerCase();
  
  for (const pattern of TIME_PATTERNS) {
    const match = trimmed.match(pattern);
    if (match) {
      let hours = parseInt(match[1], 10);
      const minutes = match[2] ? parseInt(match[2], 10) : 0;
      const period = match[3]?.toLowerCase();
      
      if (period === 'pm' && hours < 12) hours += 12;
      if (period === 'am' && hours === 12) hours = 0;
      if (!period && hours > 12) hours = hours % 24;
      
      if (hours >= 0 && hours <= 23 && minutes >= 0 && minutes <= 59) {
        return { hours, minutes };
      }
    }
  }
  return null;
}

function extractTimeFromTitle(title: string): { cleanedTitle: string; time: { hours: number; minutes: number } | null } {
  const words = title.split(/\s+/);
  let cleanedParts: string[] = [];
  let foundTime: { hours: number; minutes: number } | null = null;
  
  for (const word of words) {
    const time = parseTime(word);
    if (time && !foundTime) {
      foundTime = time;
    } else {
      cleanedParts.push(word);
    }
  }
  
  return {
    cleanedTitle: cleanedParts.join(' '),
    time: foundTime,
  };
}

function formatDateTime(hours: number, minutes: number): string {
  const now = new Date();
  now.setHours(hours, minutes, 0, 0);
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  const h = String(now.getHours()).padStart(2, '0');
  const min = String(now.getMinutes()).padStart(2, '0');
  return `${y}-${m}-${d}T${h}:${min}`;
}

function fmt12(d: Date) {
  let h = d.getHours(), m = d.getMinutes();
  const ap = h >= 12 ? 'pm' : 'am';
  h = h % 12 || 12;
  return `${h}:${String(m).padStart(2, '0')}${ap}`;
}

export default function AddBar({ onAdd, initialTime }: Props) {
  const [title, setTitle]     = useState('');
  const [expanded, setExpand] = useState(false);
  const [start, setStart]     = useState('');
  const [end, setEnd]         = useState('');
  const [showPreview, setShowPreview] = useState(false);
  const prevTitleRef = useRef('');
  const initialTimeRef = useRef(initialTime);

  useEffect(() => {
    if (initialTimeRef.current && !start) {
      setStart(initialTimeRef.current);
      setExpand(true);
      initialTimeRef.current = undefined;
    }
  }, [initialTime, start]);

  useEffect(() => {
    const prev = prevTitleRef.current;
    const current = title;
    
    if (current.length > prev.length && !expanded && !showPreview) {
      const { time } = extractTimeFromTitle(current);
      if (time) {
        setStart(formatDateTime(time.hours, time.minutes));
        setExpand(true);
      }
    }
    
    prevTitleRef.current = current;
  }, [title, expanded, showPreview]);

  function handlePreview() {
    if (!title.trim()) return;
    setShowPreview(true);
  }

  function handleConfirm() {
    const { cleanedTitle } = extractTimeFromTitle(title);
    const finalTitle = cleanedTitle.trim() || title.trim();
    const startAt = start || new Date().toISOString();
    onAdd(finalTitle, startAt, end || undefined);
    setTitle('');
    setStart('');
    setEnd('');
    setExpand(false);
    setShowPreview(false);
  }

  function handleCancel() {
    setShowPreview(false);
  }

  const { cleanedTitle } = extractTimeFromTitle(title);
  const previewTitle = cleanedTitle.trim() || title.trim();
  const previewStart = start ? new Date(start) : null;
  const previewEnd = end ? new Date(end) : null;

  return (
    <div className={styles.bar}>
      <div className={styles.inner}>
        {!showPreview ? (
          <>
            <div className={styles.row}>
              <input
                className={styles.input}
                value={title}
                onChange={e => setTitle(e.target.value.slice(0, 100))}
                onKeyDown={e => e.key === 'Enter' && handlePreview()}
                placeholder="Add event…"
                autoComplete="off"
                maxLength={100}
              />
              <span className={styles.charCount}>{title.length}/100</span>
              <button
                className={`${styles.expandBtn} ${expanded ? styles.open : ''}`}
                onClick={() => setExpand(v => !v)}
                aria-label="Set date and time"
              >
                ⌃
              </button>
              <button
                className={styles.addBtn}
                onClick={handlePreview}
                disabled={!title.trim()}
              >
                Add
              </button>
            </div>

            {expanded && (
              <div className={styles.extra}>
                <input
                  className={styles.dtInput}
                  type="datetime-local"
                  value={start}
                  onChange={e => setStart(e.target.value)}
                />
                <input
                  className={styles.dtInput}
                  type="datetime-local"
                  value={end}
                  onChange={e => setEnd(e.target.value)}
                  placeholder="End time (optional)"
                />
              </div>
            )}
          </>
        ) : (
          <div className={styles.preview}>
            <div className={styles.previewTitle}>{previewTitle}</div>
            <div className={styles.previewTime}>
              {previewStart && fmt12(previewStart)}
              {previewEnd && ` – ${fmt12(previewEnd)}`}
            </div>
            <div className={styles.previewActions}>
              <button className={styles.cancelBtn} onClick={handleCancel}>
                Cancel
              </button>
              <button className={styles.confirmBtn} onClick={() => { haptic('success'); handleConfirm(); }}>
                Confirm
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
