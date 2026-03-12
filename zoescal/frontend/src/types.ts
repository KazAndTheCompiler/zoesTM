export type CalMode = 'day' | 'week' | 'month';

export type SkinId =
  | 'warm-analog'
  | 'midnight-neon'
  | 'paper-minimal'
  | 'aurora'
  | 'high-contrast'
  | 'retro'
  | 'soft-pastel'
  | 'glassy-modern'
  | 'muted-professional';

export interface SkinMeta {
  id: SkinId;
  name: string;
  colors: [string, string, string]; // [bg, accent, secondary]
}

export interface CalEntry {
  id: string;
  title: string;
  at: string;
  end_at?: string;
  source_id?: string;
  all_day?: boolean;
  read_only?: boolean;
  editability_class?: string;
  source?: string;
  source_type?: string;
  local_note?: string;
  linked_task_id?: string;
  sync_status?: string;
  recurrence?: string;
  _d?: Date; // parsed client-side
}

export interface CalViewData {
  mode: string;
  window?: { start: string; end: string };
  entries: CalEntry[];
}
