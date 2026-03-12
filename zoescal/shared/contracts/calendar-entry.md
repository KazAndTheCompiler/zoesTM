# Shared Contract: Calendar Entry Shape

Version: 0.1.0
Date: 2026-03-11

This is the shared data contract between ZoesCal and ZoesTM.

---

## Calendar Entry

```typescript
interface CalendarEntry {
  // Identity (ADR 0002)
  id?: string;                     // canonical internal ID (evt_xxx, tsk_xxx etc)
  source: string;                  // 'zoescal' | 'zoestm' | 'google' | 'caldav'
  source_type: string;             // 'event' | 'task' | 'habit' | 'alarm'
  source_id: string;               // ID within source system
  source_version: string;          // contract version
  dedupe_key: string;              // unique key for deduplication

  // Scheduling
  title: string;
  at: string;                      // ISO 8601 UTC start time
  end_at?: string;                 // ISO 8601 UTC end time
  all_day?: boolean;

  // Conflict scoring (ADR 0003)
  conflict_score: number;          // 0.0 = no conflict risk, 1.0 = high

  // Editability (ADR 0005)
  read_only: boolean;
  editability_class: 'local' | 'readonly_mirror' | 'limited_editable';
  can_edit_time?: boolean;
  can_edit_title?: boolean;
  can_edit_description?: boolean;
  can_delete?: boolean;

  // App overlays (ZoesCal-owned, never written back to source)
  local_note?: string;
  local_color?: string;
  linked_task_id?: string;         // internal ZoesTM task ID

  // Sync state (ADR 0003)
  sync_status?: 'local_only' | 'pending_sync' | 'synced' | 'conflict' | 'error';
}
```

---

## ZoesTM Feed Endpoint

ZoesTM exposes: `GET /calendar/feed?from_=<ISO>&to=<ISO>`

Returns entries owned by ZoesTM (tasks, habits, alarms) shaped as CalendarEntry[].
All entries are `read_only: true` — ZoesCal may display but not mutate them.

---

## Ownership Summary

| Object type | Owner | ZoesCal can edit? |
|---|---|---|
| Calendar events | ZoesCal | Yes (local) |
| Tasks / due dates | ZoesTM | No — read only |
| Habits / logs | ZoesTM | No — read only |
| Alarms | ZoesTM | No — read only |
| External events (Google etc) | Provider | Overlay only |
| Local notes on any entry | ZoesCal | Yes |
