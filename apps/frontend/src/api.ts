export const BASE = (globalThis as any).__ZOESTM_API_BASE__ || (globalThis.location?.protocol === 'file:' ? 'http://127.0.0.1:8000' : '/api');

async function unwrap(response: Response) {
  try {
    let payload: any;
    try {
      payload = await response.json();
    } catch (parseErr) {
      throw new Error(`Failed to parse response: ${response.status} ${response.statusText}`);
    }
    
    if (!response.ok) {
      const msg = payload?.error?.message || payload?.detail || `HTTP ${response.status}`;
      const error = new Error(msg);
      (error as any).status = response.status;
      (error as any).code = payload?.error?.code;
      throw error;
    }
    return payload;
  } catch (err) {
    if (err instanceof Error) throw err;
    throw new Error('Network request failed');
  }
}

export async function jget(path: string) {
  return fetch(BASE + path).then(unwrap);
}

async function jsend(method: string, path: string, body?: any) {
  const init: any = { method };
  if (body !== undefined) {
    init.headers = { 'Content-Type': 'application/json' };
    init.body = JSON.stringify(body);
  }
  return fetch(BASE + path, init).then(unwrap);
}

export async function jpost(path: string, body?: any) {
  return jsend('POST', path, body);
}

export async function jpatch(path: string, body?: any) {
  return jsend('PATCH', path, body);
}

export async function jdelete(path: string) {
  return jsend('DELETE', path);
}
