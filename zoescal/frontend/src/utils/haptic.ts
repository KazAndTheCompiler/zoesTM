export function haptic(type: 'light' | 'medium' | 'heavy' | 'success' = 'light') {
  if (typeof navigator === 'undefined' || !navigator.vibrate) return;
  
  const patterns: Record<string, number | number[]> = {
    light: 10,
    medium: 25,
    heavy: 50,
    success: [0, 30, 50, 30],
  };
  
  navigator.vibrate(patterns[type]);
}
