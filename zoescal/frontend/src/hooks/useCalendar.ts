import { useState, useCallback, useEffect } from 'react';
import { jget, jpost } from '../api';
import type { CalEntry, CalMode } from '../types';

function parseEntries(raw: any[]): CalEntry[] {
  return (raw || []).map(e => ({
    ...e,
    _d: e.at ? new Date(e.at) : null,
  })).filter((e): e is CalEntry & { _d: Date } => e._d !== null && !isNaN(e._d.getTime()));
}

function demoEntries(): CalEntry[] {
  const now = new Date();
  const d = (h: number, m = 0) => { const x = new Date(now); x.setHours(h, m, 0, 0); return x; };
  const iso = (x: Date) => x.toISOString();
  return [
    { id:'d1', title:'Morning pages',        at: iso(d(7,30)), source:'task',    _d: d(7,30) },
    { id:'d2', title:'Team standup',          at: iso(d(9,0)),  source:'zoescal', _d: d(9,0) },
    { id:'d3', title:'Deep work block',       at: iso(d(10,0)), source:'task',    _d: d(10,0) },
    { id:'d4', title:'Lunch',                 at: iso(d(12,30)),source:'zoescal', _d: d(12,30) },
    { id:'d5', title:'Review pull requests',  at: iso(d(14,0)), source:'task',    _d: d(14,0) },
    { id:'d6', title:'Evening run 🏃',        at: iso(d(18,0)), source:'alarm',   _d: d(18,0) },
  ];
}

export function useCalendar(mode: CalMode) {
  const [entries, setEntries] = useState<CalEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState<string | null>(null);
  const [offline, setOffline] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await jget(`/calendar/view?mode=${mode}`);
      setEntries(parseEntries(data.entries || []));
      setOffline(false);
    } catch (e: any) {
      setError(e.message);
      setOffline(true);
      setEntries(demoEntries());
    } finally {
      setLoading(false);
    }
  }, [mode]);

  useEffect(() => { load(); }, [load]);

  const addEvent = useCallback(async (title: string, startAt: string, endAt?: string) => {
    try {
      await jpost('/calendar/events', {
        title,
        start_at: new Date(startAt).toISOString(),
        end_at: endAt ? new Date(endAt).toISOString() : undefined,
      });
      await load();
    } catch {
      await load(); // re-render with current state
    }
  }, [load]);

  return { entries, loading, error, offline, reload: load, addEvent };
}
