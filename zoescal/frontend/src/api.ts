export const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001';

async function apiFetch(path: string, opts: RequestInit = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(opts.headers as Record<string, string> || {}) },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw new Error(err?.error?.message || res.statusText);
  }
  return res.status === 204 ? null : res.json();
}

export const jget    = (p: string)              => apiFetch(p);
export const jpost   = (p: string, b?: unknown) => apiFetch(p, { method: 'POST',   body: JSON.stringify(b) });
export const jpatch  = (p: string, b?: unknown) => apiFetch(p, { method: 'PATCH',  body: JSON.stringify(b) });
export const jdelete = (p: string)              => apiFetch(p, { method: 'DELETE' });
