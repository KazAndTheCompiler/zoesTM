import { useState, useEffect } from 'react';
import styles from './InstallBanner.module.css';

export default function InstallBanner() {
  const [prompt, setPrompt] = useState<any>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setPrompt(e);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  if (!prompt || dismissed) return null;

  async function install() {
    prompt.prompt();
    await prompt.userChoice;
    setPrompt(null);
  }

  return (
    <div className={styles.banner}>
      <span className={styles.text}>📅 Add ZoesCal to your home screen</span>
      <button className={styles.installBtn} onClick={install} aria-label="Install app">Install</button>
      <button className={styles.dismiss} onClick={() => setDismissed(true)} aria-label="Dismiss">✕</button>
    </div>
  );
}
