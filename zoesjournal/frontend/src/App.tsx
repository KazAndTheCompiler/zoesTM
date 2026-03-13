import { useEffect, useMemo, useState } from 'react';
import { BASE, authHeaders, jdelete, jget, jpatch, jpost } from './api';
import { renderMarkdown } from './lib/markdown';

type NavKey = 'today' | 'history' | 'export';
type JournalEntry = {
  id: string;
  date: string;
  markdown_body: string;
  emoji: string | null;
  created_at: string;
  updated_at: string;
};

type ExportPayload = {
  date: string;
  journal: JournalEntry | null;
  habits: { done: number; total: number; names: string[] };
  events: Array<{ title?: string; at?: string }>;
};

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function hashToView(): NavKey {
  const raw = window.location.hash.replace(/^#\/?/, '');
  return raw === 'history' || raw === 'export' ? raw : 'today';
}

function formatFriendlyDate(date: string) {
  const d = new Date(`${date}T00:00:00`);
  return isNaN(d.getTime()) ? date : d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
}

export default function App() {
  const [view, setView] = useState<NavKey>(hashToView());
  const [selectedDate, setSelectedDate] = useState(todayIso());
  const [current, setCurrent] = useState<JournalEntry | null>(null);
  const [markdown, setMarkdown] = useState('');
  const [emoji, setEmoji] = useState('');
  const [history, setHistory] = useState<JournalEntry[]>([]);
  const [exportFormat, setExportFormat] = useState<'json' | 'text' | 'markdown'>('markdown');
  const [exportData, setExportData] = useState<ExportPayload | string | null>(null);
  const [loading, setLoading] = useState({ entry: false, history: false, save: false, export: false, delete: false });
  const [error, setError] = useState<string>('');
  const [notice, setNotice] = useState<string>('');

  useEffect(() => {
    const onHash = () => setView(hashToView());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  useEffect(() => {
    void loadEntry(selectedDate);
  }, [selectedDate]);

  useEffect(() => {
    if (view === 'history') void loadHistory();
    if (view === 'export') void loadExport(exportFormat);
  }, [view]);

  async function loadEntry(date: string) {
    setLoading((s) => ({ ...s, entry: true }));
    setError('');
    setNotice('');
    try {
      const entry = await jget(`/journal/by-date/${date}`) as JournalEntry;
      setCurrent(entry);
      setMarkdown(entry.markdown_body || '');
      setEmoji(entry.emoji || '');
    } catch (err: any) {
      if (err?.status === 404) {
        setCurrent(null);
        setMarkdown('');
        setEmoji('');
      } else {
        setError(err?.message || 'Could not load journal entry');
      }
    } finally {
      setLoading((s) => ({ ...s, entry: false }));
    }
  }

  async function loadHistory() {
    setLoading((s) => ({ ...s, history: true }));
    setError('');
    try {
      const items = await jget('/journal/?limit=60') as JournalEntry[];
      setHistory(Array.isArray(items) ? items : []);
    } catch (err: any) {
      setError(err?.message || 'Could not load history');
    } finally {
      setLoading((s) => ({ ...s, history: false }));
    }
  }

  async function saveEntry() {
    setLoading((s) => ({ ...s, save: true }));
    setError('');
    setNotice('');
    try {
      const trimmed = markdown.trim();
      if (!trimmed) {
        throw new Error('Write something before saving');
      }
      const payload = { date: selectedDate, markdown_body: trimmed, emoji: emoji.trim() || null };
      const next = current
        ? await jpatch(`/journal/${current.id}`, { markdown_body: payload.markdown_body, emoji: payload.emoji }) as JournalEntry
        : await jpost('/journal/', payload) as JournalEntry;
      setCurrent(next);
      setMarkdown(next.markdown_body || '');
      setEmoji(next.emoji || '');
      setNotice(current ? 'Entry updated' : 'Entry saved');
      if (view === 'history') void loadHistory();
    } catch (err: any) {
      setError(err?.message || 'Could not save entry');
    } finally {
      setLoading((s) => ({ ...s, save: false }));
    }
  }

  async function deleteEntry() {
    if (!current) return;
    if (!window.confirm(`Delete journal entry for ${current.date}?`)) return;
    setLoading((s) => ({ ...s, delete: true }));
    setError('');
    setNotice('');
    try {
      await jdelete(`/journal/${current.id}`);
      setCurrent(null);
      setMarkdown('');
      setEmoji('');
      setNotice('Entry deleted');
      if (view === 'history') void loadHistory();
    } catch (err: any) {
      setError(err?.message || 'Could not delete entry');
    } finally {
      setLoading((s) => ({ ...s, delete: false }));
    }
  }

  async function loadExport(format: 'json' | 'text' | 'markdown' = exportFormat) {
    setLoading((s) => ({ ...s, export: true }));
    setError('');
    try {
      const payload = await jget(`/journal/export/${selectedDate}?format=${format}`, format === 'json' ? undefined : { Accept: 'text/plain' });
      setExportData(payload as any);
    } catch (err: any) {
      setError(err?.message || 'Could not load export');
    } finally {
      setLoading((s) => ({ ...s, export: false }));
    }
  }

  async function copyExport() {
    const format = exportFormat;
    try {
      const res = await fetch(`${BASE}/journal/export/${selectedDate}?format=${format}`, { headers: authHeaders() });
      const text = await res.text();
      await navigator.clipboard.writeText(text);
      setNotice('Export copied');
    } catch {
      setError('Could not copy export');
    }
  }

  const previewHtml = useMemo(() => renderMarkdown(markdown), [markdown]);

  function go(next: NavKey) {
    window.location.hash = `/${next}`;
    setView(next);
    setNotice('');
    setError('');
  }

  return (
    <div className="journal-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Mobile-first companion</p>
          <h1>ZoesJournal</h1>
        </div>
        <img src="/zoe-logo.svg" alt="Zoe logo" className="logo" />
      </header>

      <nav className="tabs" aria-label="Journal navigation">
        <button className={view === 'today' ? 'is-active' : ''} onClick={() => go('today')}>Today</button>
        <button className={view === 'history' ? 'is-active' : ''} onClick={() => go('history')}>History</button>
        <button className={view === 'export' ? 'is-active' : ''} onClick={() => go('export')}>Export</button>
      </nav>

      <main className="content">
        <section className="hero-card">
          <div>
            <p className="hero-label">Day entry</p>
            <h2>{formatFriendlyDate(selectedDate)}</h2>
          </div>
          <div className="date-controls">
            <button onClick={() => setSelectedDate(new Date(new Date(`${selectedDate}T00:00:00`).getTime() - 86400000).toISOString().slice(0, 10))}>←</button>
            <input type="date" value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)} />
            <button onClick={() => setSelectedDate(new Date(new Date(`${selectedDate}T00:00:00`).getTime() + 86400000).toISOString().slice(0, 10))}>→</button>
          </div>
        </section>

        {error && <section className="status-card error">{error}</section>}
        {notice && <section className="status-card success">{notice}</section>}

        {view === 'today' && (
          <>
            <section className="editor-card">
              <label>
                <span>Emoji</span>
                <input value={emoji} onChange={(e) => setEmoji(e.target.value)} placeholder="📝" maxLength={8} />
              </label>
              <label>
                <span>Markdown</span>
                <textarea
                  value={markdown}
                  onChange={(e) => setMarkdown(e.target.value)}
                  placeholder="# Today\n- dumped links\n- grocery list\n- feelings\n- whatever matters"
                  rows={14}
                />
              </label>
              <div className="editor-actions">
                <button onClick={saveEntry} disabled={loading.save || loading.entry}>{loading.save ? 'Saving…' : current ? 'Update entry' : 'Save entry'}</button>
                <button className="secondary" onClick={() => void loadEntry(selectedDate)} disabled={loading.entry}>Reload</button>
                <button className="danger secondary" onClick={deleteEntry} disabled={!current || loading.delete}>{loading.delete ? 'Deleting…' : 'Delete'}</button>
              </div>
              <p className="helper">One entry per day. Backdating is supported by changing the date above.</p>
            </section>

            <section className="preview-card">
              <div className="preview-heading">
                <h3>Preview</h3>
                <span>{emoji || '✍️'}</span>
              </div>
              {loading.entry ? (
                <p className="muted">Loading entry…</p>
              ) : markdown.trim() ? (
                <article className="markdown-body" dangerouslySetInnerHTML={{ __html: previewHtml }} />
              ) : (
                <div className="empty-state">
                  <h3>No entry yet</h3>
                  <p>Start with a heading, a list, or a couple of lines. This companion app stores raw markdown and keeps the backend contract unchanged.</p>
                </div>
              )}
            </section>
          </>
        )}

        {view === 'history' && (
          <section className="list-card">
            <div className="section-head">
              <h3>History</h3>
              <button className="secondary" onClick={() => void loadHistory()} disabled={loading.history}>{loading.history ? 'Refreshing…' : 'Refresh'}</button>
            </div>
            {loading.history ? (
              <p className="muted">Loading entries…</p>
            ) : history.length === 0 ? (
              <div className="empty-state"><h3>No entries yet</h3><p>Your journal history will show up here once you save one.</p></div>
            ) : (
              <ul className="history-list">
                {history.map((item) => (
                  <li key={item.id}>
                    <button
                      className={`history-item ${item.date === selectedDate ? 'is-selected' : ''}`}
                      onClick={() => {
                        setSelectedDate(item.date);
                        go('today');
                      }}
                    >
                      <div>
                        <strong>{item.emoji || '🗒️'} {formatFriendlyDate(item.date)}</strong>
                        <p>{(item.markdown_body || '').split(/\r?\n/)[0] || 'Untitled entry'}</p>
                      </div>
                      <span>Open</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}

        {view === 'export' && (
          <section className="export-card">
            <div className="section-head">
              <h3>Daily digest export</h3>
              <div className="inline-controls">
                <select value={exportFormat} onChange={(e) => setExportFormat(e.target.value as 'json' | 'text' | 'markdown')}>
                  <option value="markdown">Markdown</option>
                  <option value="text">Text</option>
                  <option value="json">JSON</option>
                </select>
                <button onClick={() => void loadExport(exportFormat)} disabled={loading.export}>{loading.export ? 'Loading…' : 'Load export'}</button>
                <button className="secondary" onClick={copyExport}>Copy</button>
              </div>
            </div>
            <p className="helper">If Calendar or related services are unavailable, export should degrade gracefully instead of crashing.</p>
            {loading.export ? (
              <p className="muted">Loading export…</p>
            ) : exportData == null ? (
              <div className="empty-state"><h3>No export loaded</h3><p>Load the digest for the selected day.</p></div>
            ) : typeof exportData === 'string' ? (
              <pre className="export-block">{exportData}</pre>
            ) : (
              <pre className="export-block">{JSON.stringify(exportData, null, 2)}</pre>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
