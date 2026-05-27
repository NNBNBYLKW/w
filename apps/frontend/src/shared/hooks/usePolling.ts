import { useEffect, useRef, useState } from "react";

export function usePolling<T>(
  fetcher: () => Promise<T>,
  isDone: (data: T) => boolean,
  intervalMs: number = 2000,
) {
  const [data, setData] = useState<T | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stop = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setIsPolling(false);
  };

  const start = () => {
    stop();
    setIsPolling(true);
    const tick = async () => {
      try {
        const result = await fetcher();
        setData(result);
        if (isDone(result)) {
          setIsPolling(false);
          return;
        }
      } catch {
        /* continue polling on error */
      }
      timerRef.current = setTimeout(tick, intervalMs);
    };
    tick();
  };

  useEffect(() => () => stop(), []);

  return { data, isPolling, start, stop };
}
