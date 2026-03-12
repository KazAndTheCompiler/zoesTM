import type { CalEntry } from '../types';

function routeFor(entry: CalEntry): string | null {
  if (entry.source === 'task') return 'tasks';
  if (entry.source === 'habit') return 'habits';
  if (entry.source === 'alarm') return 'alarm-player';
  return null;
}

export function canOpenZoestm(entry: CalEntry): boolean {
  return Boolean(routeFor(entry));
}

export function openZoestmEntry(entry: CalEntry): void {
  const route = routeFor(entry);
  if (!route) return;
  const params = new URLSearchParams();
  if (entry.source_id) params.set('source_id', entry.source_id);
  if (entry.title) params.set('title', entry.title);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  window.open(`http://localhost:5173/#/${route}${suffix}`, '_blank', 'noopener,noreferrer');
}
