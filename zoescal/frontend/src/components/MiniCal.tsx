import { useState } from 'react';
import styles from './MiniCal.module.css';

interface Props {
  onSelect: (date: Date) => void;
}

const DOW = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

export default function MiniCal({ onSelect }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const now = new Date();
  const [monthOffset, setMonthOffset] = useState(0);

  const displayDate = new Date(now.getFullYear(), now.getMonth() + monthOffset, 1);
  const year = displayDate.getFullYear();
  const month = displayDate.getMonth();
  const firstDow = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const cells: (number | null)[] = [
    ...Array(firstDow).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];

  const isCurrentMonth = monthOffset === 0;
  const monthLabel = displayDate.toLocaleDateString(undefined, { month: 'short', year: 'numeric' });

  function handleSelect(day: number) {
    const selected = new Date(year, month, day);
    onSelect(selected);
    setIsOpen(false);
  }

  return (
    <div className={styles.container}>
      <button 
        className={styles.trigger}
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Open calendar"
        title="Jump to date"
      >
        📅
      </button>

      {isOpen && (
        <div className={styles.dropdown}>
          <div className={styles.header}>
            <button 
              className={styles.navBtn}
              onClick={() => setMonthOffset(o => o - 1)}
              aria-label="Previous month"
            >‹</button>
            <span className={styles.monthLabel}>{monthLabel}</span>
            <button 
              className={styles.navBtn}
              onClick={() => setMonthOffset(o => o + 1)}
              aria-label="Next month"
            >›</button>
          </div>

          <div className={styles.dow}>
            {DOW.map(d => <span key={d}>{d}</span>)}
          </div>

          <div className={styles.grid}>
            {cells.map((day, i) => {
              if (day === null) return <span key={`blank-${i}`} />;
              const isToday = isCurrentMonth && day === now.getDate();
              return (
                <button
                  key={day}
                  className={`${styles.day} ${isToday ? styles.today : ''}`}
                  onClick={() => handleSelect(day)}
                >
                  {day}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
