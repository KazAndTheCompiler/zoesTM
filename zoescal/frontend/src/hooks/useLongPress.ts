import { useState, useRef, useCallback } from 'react';

interface LongPressOptions {
  onLongPress: () => void;
  duration?: number;
}

export function useLongPress({ onLongPress, duration = 500 }: LongPressOptions) {
  const [isLongPressing, setIsLongPressing] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleTouchStart = useCallback(() => {
    setIsLongPressing(true);
    timerRef.current = setTimeout(() => {
      onLongPress();
      setIsLongPressing(false);
    }, duration);
  }, [onLongPress, duration]);

  const handleTouchEnd = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    setIsLongPressing(false);
  }, []);

  const handleTouchMove = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    setIsLongPressing(false);
  }, []);

  return {
    isLongPressing,
    onTouchStart: handleTouchStart,
    onTouchEnd: handleTouchEnd,
    onTouchMove: handleTouchMove,
  };
}
