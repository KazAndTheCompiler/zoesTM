import { useState, useRef, useCallback } from 'react';

interface PullToRefreshOptions {
  onRefresh: () => void;
  threshold?: number;
  maxPullDistance?: number;
}

export function usePullToRefresh({ onRefresh, threshold = 80, maxPullDistance = 150 }: PullToRefreshOptions) {
  const [isPulling, setIsPulling] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);
  const startY = useRef<number | null>(null);
  const currentY = useRef<number | null>(null);
  const isRefreshing = useRef(false);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    if (scrollTop === 0 && !isRefreshing.current) {
      startY.current = e.touches[0].clientY;
      currentY.current = e.touches[0].clientY;
    }
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (startY.current === null) return;
    
    currentY.current = e.touches[0].clientY;
    const diff = currentY.current - startY.current;
    
    if (diff > 0 && diff <= maxPullDistance) {
      setIsPulling(true);
      setPullDistance(diff);
      e.preventDefault();
    }
  }, [maxPullDistance]);

  const handleTouchEnd = useCallback(() => {
    if (pullDistance >= threshold && !isRefreshing.current) {
      isRefreshing.current = true;
      setPullDistance(0);
      setIsPulling(false);
      onRefresh();
      setTimeout(() => {
        isRefreshing.current = false;
      }, 1000);
    } else {
      setPullDistance(0);
      setIsPulling(false);
    }
    startY.current = null;
    currentY.current = null;
  }, [pullDistance, threshold, onRefresh]);

  return {
    isPulling,
    pullDistance,
    onTouchStart: handleTouchStart,
    onTouchMove: handleTouchMove,
    onTouchEnd: handleTouchEnd,
  };
}
