import { useState, useEffect } from 'react';
import styles from './OfflineBanner.module.css';

interface Props {
  offline: boolean;
}

export default function OfflineBanner({ offline }: Props) {
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    setDismissed(false);
  }, [offline]);

  if (!offline || dismissed) return null;

  return (
    <div className={styles.banner}>
      <span className={styles.icon}>📡</span>
      <span className={styles.text}>You're offline — showing cached data</span>
      <button 
        className={styles.dismiss} 
        onClick={() => setDismissed(true)}
        aria-label="Dismiss offline notice"
      >×</button>
    </div>
  );
}
