import { useState, useEffect } from 'react';
import './skins/warm-analog.css';
import './skins/skins.css';
import './styles/global.css';

import Header from './components/Header';
import SkinDrawer from './components/SkinDrawer';
import DayView from './components/DayView';
import WeekView from './components/WeekView';
import MonthView from './components/MonthView';
import AddBar from './components/AddBar';
import InstallBanner from './components/InstallBanner';
import OfflineBanner from './components/OfflineBanner';
import ErrorBoundary from './components/ErrorBoundary';

import { useCalendar } from './hooks/useCalendar';
import { SKINS } from './skins';
import type { CalMode, SkinId } from './types';

const SKIN_KEY = 'zoescal-skin';

export default function App() {
  const [mode, setMode]         = useState<CalMode>('day');
  const [skin, setSkin]         = useState<SkinId>(
    () => (localStorage.getItem(SKIN_KEY) as SkinId) || 'warm-analog'
  );
  const [drawerOpen, setDrawer] = useState(false);
  const [viewKey, setViewKey]   = useState(0);
  const [dayOffset, setDayOffset] = useState(0);
  const [weekOffset, setWeekOffset] = useState(0);
  const [monthOffset, setMonthOffset] = useState(0);
  const [initialTime, setInitialTime] = useState<string | undefined>(undefined);

  const { entries, offline, addEvent, loading, reload } = useCalendar(mode);

  useEffect(() => {
    document.documentElement.dataset.skin = skin;
    document.querySelector('meta[name="theme-color"]')
      ?.setAttribute('content', SKINS.find(s => s.id === skin)?.colors[1] ?? '#8b6f47');
    localStorage.setItem(SKIN_KEY, skin);
  }, [skin]);

  const skinMeta = SKINS.find(s => s.id === skin)!;

  function handleToday() {
    setDayOffset(0);
    setWeekOffset(0);
    setMonthOffset(0);
    setViewKey(k => k + 1);
  }

  function handleSelectDate(date: Date) {
    const today = new Date();
    const diffTime = date.getTime() - today.getTime();
    const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24));
    
    setDayOffset(diffDays);
    setWeekOffset(Math.floor(diffDays / 7));
    setMonthOffset((date.getFullYear() - today.getFullYear()) * 12 + (date.getMonth() - today.getMonth()));
    setViewKey(k => k + 1);
  }

  return (
    <ErrorBoundary>
      <div className="app-shell" data-skin={skin}>
      <InstallBanner />
      <OfflineBanner offline={offline} />
      <Header
        mode={mode}
        onMode={setMode}
        onOpenSkins={() => setDrawer(true)}
        onToday={handleToday}
        onSelectDate={handleSelectDate}
        currentSkinColor={skinMeta.colors[1]}
      />

      <main style={{ overflow: 'hidden', position: 'relative', height: '100%' }}>
        {mode === 'day'   && <DayView   key={viewKey} entries={entries} loading={loading} onRefresh={reload} dayOffset={dayOffset} setDayOffset={setDayOffset} onLongPressHour={setInitialTime} />}
        {mode === 'week'  && <WeekView key={viewKey} entries={entries} loading={loading} weekOffset={weekOffset} setWeekOffset={setWeekOffset} />}
        {mode === 'month' && <MonthView key={viewKey} entries={entries} loading={loading} monthOffset={monthOffset} setMonthOffset={setMonthOffset} />}
      </main>

      <AddBar onAdd={addEvent} initialTime={initialTime} />

      <SkinDrawer
        open={drawerOpen}
        current={skin}
        onSelect={id => setSkin(id)}
        onClose={() => setDrawer(false)}
      />
      </div>
    </ErrorBoundary>
  );
}
