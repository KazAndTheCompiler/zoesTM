import { useEffect, useRef } from 'react';
import styles from './DayView.module.css';

interface NowLineProps {
  isToday: boolean;
}

export default function NowLine({ isToday }: NowLineProps) {
  const lineRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isToday || !lineRef.current) return;

    const updatePosition = () => {
      const now = new Date();
      const pct = (now.getMinutes() / 60) * 100;
      
      if (lineRef.current) {
        lineRef.current.style.top = `${pct.toFixed(1)}%`;
      }
    };

    updatePosition();
    const interval = setInterval(updatePosition, 60000);

    return () => clearInterval(interval);
  }, [isToday]);

  if (!isToday) return null;

  return <div ref={lineRef} className={styles.nowLine} />;
}
