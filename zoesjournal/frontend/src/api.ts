export const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

declare global {
  interface Window {
    __ZOESJOURNAL_TOKEN_SCOPES__?: string;
  }
}

export function authHeaders() {
  const scopes = window.__ZOESJOURNAL_TOKEN_SCOPES__ || localStorage.getItem('zoestm-token-scopes') || '';
  return scopes ? { 'X-Token-Scopes': scopes } : {};
}

async function unwrap(res: Response) {
  const contentType = res.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  const payload = isJson ? await res.json().catch(() => null) : await res.text().catch(() => '');
  if (!res.ok) {
    const msg = typeof payload === 'string' ? payload : payload?.error?.message || payload?.detail || res.statusText;
    const err = new Error(msg || `HTTP ${res.status}`);
    (err as any).status = res.status;
    (err as any).code = typeof payload === 'string' ? undefined : payload?.error?.code;
    throw err;
  }
  return payload;
}

async function send(method: string, path: string, body?: unknown, extraHeaders?: Record<string, string>) {
  const headers: Record<string, string> = {
    ...authHeaders(),
    ...extraHeaders,
  };
  const init: RequestInit = { method, headers };
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }
  const res = await fetch(`${BASE}${path}`, init);
  return unwrap(res);
}

export const jget = (path: string, headers?: Record<string, string>) => send('GET', path, undefined, headers);
export const jpost = (path: string, body?: unknown) => send('POST', path, body);
export const jpatch = (path: string, body?: unknown) => send('PATCH', path, body);
export const jdelete = (path: string) => send('DELETE', path);
