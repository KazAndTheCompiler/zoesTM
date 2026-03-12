import { useEffect, useRef } from 'react';
import { SKINS } from '../skins';
import type { SkinId } from '../types';
import styles from './SkinDrawer.module.css';

interface Props {
  open: boolean;
  current: SkinId;
  onSelect: (id: SkinId) => void;
  onClose: () => void;
}

export default function SkinDrawer({ open, current, onSelect, onClose }: Props) {
  const sheetRef = useRef<HTMLDivElement>(null);
  const firstFocusableRef = useRef<HTMLButtonElement>(null);
  const lastFocusableRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }

      if (e.key === 'Tab' && sheetRef.current) {
        const focusable = sheetRef.current.querySelectorAll<HTMLButtonElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    
    const focusable = sheetRef.current?.querySelectorAll<HTMLButtonElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    focusable?.[0]?.focus();

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open, onClose]);

  return (
    <div
      className={`${styles.overlay} ${open ? styles.open : ''}`}
      role="dialog"
      aria-modal="true"
      aria-label="Choose calendar skin"
    >
      <div className={styles.backdrop} onClick={onClose} role="button" tabIndex={-1} aria-label="Close skin picker" />
      <div className={styles.sheet} ref={sheetRef}>
        <div className={styles.handle} />
        <p className={styles.title}>Choose your skin</p>
        <div className={styles.grid}>
          {SKINS.map((s, i) => (
            <button
              key={s.id}
              ref={i === 0 ? firstFocusableRef : i === SKINS.length - 1 ? lastFocusableRef : undefined}
              className={`${styles.option} ${s.id === current ? styles.active : ''}`}
              onClick={() => { onSelect(s.id); onClose(); }}
              aria-label={`Apply ${s.name} skin`}
            >
              <div className={styles.swatch} style={{ background: s.colors[0] }}>
                <div className={styles.swatchA} style={{ background: s.colors[1] }} />
                <div className={styles.swatchB} style={{ background: s.colors[2] }} />
                {s.id === current && <span className={styles.check}>✓</span>}
              </div>
              <span className={styles.name}>{s.name}</span>
            </button>
          ))}
        </div>
        <p className={styles.credit}>Built free by KazAndTheCompiler ☕</p>
      </div>
    </div>
  );
}
