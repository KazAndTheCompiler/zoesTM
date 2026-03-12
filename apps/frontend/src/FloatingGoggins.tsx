import { useEffect, useRef, useState } from 'react';
import { BASE } from './api';

const LABELS = [
  "WHO'S GONNA CARRY THE BOATS",
  'STAY HARD',
  'CALL HIM SOFT',
];

export default function FloatingGoggins() {
  const [labelIndex, setLabelIndex] = useState(0);
  const [quote, setQuote] = useState('');
  const [visible, setVisible] = useState(false);
  const [shaking, setShaking] = useState(false);
  const quoteTimerRef = useRef<number | null>(null);
  const fadeTimerRef = useRef<number | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    return () => {
      if (quoteTimerRef.current) window.clearTimeout(quoteTimerRef.current);
      if (fadeTimerRef.current) window.clearTimeout(fadeTimerRef.current);
      audioContextRef.current?.close().catch(() => {});
    };
  }, []);

  async function playAudio() {
    const res = await fetch(`${BASE}/goggins/trigger`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to trigger Goggins audio');
    const buffer = await res.arrayBuffer();
    const AudioCtx = window.AudioContext || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioCtx) throw new Error('Web Audio API unavailable');
    if (!audioContextRef.current || audioContextRef.current.state === 'closed') {
      audioContextRef.current = new AudioCtx();
    }
    const ctx = audioContextRef.current;
    if (ctx.state === 'suspended') await ctx.resume();
    const decoded = await ctx.decodeAudioData(buffer.slice(0));
    const source = ctx.createBufferSource();
    source.buffer = decoded;
    source.connect(ctx.destination);
    source.start(0);
  }

  async function showQuote() {
    const res = await fetch(`${BASE}/goggins/quote`);
    if (!res.ok) throw new Error('Failed to fetch Goggins quote');
    const data = await res.json();
    setQuote(data.quote || 'Stay hard.');
    setVisible(true);
    if (quoteTimerRef.current) window.clearTimeout(quoteTimerRef.current);
    if (fadeTimerRef.current) window.clearTimeout(fadeTimerRef.current);
    quoteTimerRef.current = window.setTimeout(() => setVisible(false), 5000);
    fadeTimerRef.current = window.setTimeout(() => setQuote(''), 5600);
  }

  async function handleClick() {
    setShaking(true);
    window.setTimeout(() => setShaking(false), 420);
    setLabelIndex((i) => (i + 1) % LABELS.length);
    await Promise.allSettled([playAudio(), showQuote()]);
  }

  return (
    <div className="goggins-wrap" aria-live="polite">
      {quote && (
        <div className={`goggins-quote ${visible ? 'is-visible' : 'is-fading'}`}>
          {quote}
        </div>
      )}
      <button
        type="button"
        className={`goggins-button ${shaking ? 'is-shaking' : ''}`}
        onClick={handleClick}
        aria-label="Emergency dopamine button"
      >
        {LABELS[labelIndex]}
      </button>
    </div>
  );
}
