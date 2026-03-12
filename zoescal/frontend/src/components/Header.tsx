import type { CalMode, SkinId } from '../types';
import styles from './Header.module.css';
import MiniCal from './MiniCal';

interface Props {
  mode: CalMode;
  onMode: (m: CalMode) => void;
  onOpenSkins: () => void;
  onToday: () => void;
  onSelectDate: (date: Date) => void;
  currentSkinColor: string;
}

const MODES: { id: CalMode; label: string }[] = [
  { id: 'day',   label: 'Day'   },
  { id: 'week',  label: 'Week'  },
  { id: 'month', label: 'Month' },
];

export default function Header({ mode, onMode, onOpenSkins, onToday, onSelectDate, currentSkinColor }: Props) {
  return (
    <header className={styles.header}>
      <span className={styles.title}>ZoesCal</span>
      <nav className={styles.nav}>
        {MODES.map(m => (
          <button
            key={m.id}
            className={`${styles.modeBtn} ${mode === m.id ? styles.active : ''}`}
            onClick={() => onMode(m.id)}
          >
            {m.label}
          </button>
        ))}
        <button
          className={styles.todayBtn}
          onClick={onToday}
          title="Go to today"
        >
          Today
        </button>
      </nav>
      <MiniCal onSelect={onSelectDate} />
      <button
        className={styles.skinBtn}
        style={{ background: currentSkinColor }}
        onClick={onOpenSkins}
        aria-label="Change skin"
        title="Change skin"
      />
    </header>
  );
}
