import { useState, useRef, useCallback, useEffect } from "react";

interface VirtualListOptions {
  itemHeight: number;
  overscan?: number;
  totalItems: number;
}

export function useVirtualList(
  containerRef: React.RefObject<HTMLElement>,
  { itemHeight, overscan = 3, totalItems }: VirtualListOptions,
) {
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(0);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      setContainerHeight(entry.contentRect.height);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [containerRef]);

  const onScroll = useCallback((e: React.UIEvent<HTMLElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  const visibleCount = Math.ceil(containerHeight / itemHeight);
  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
  const endIndex = Math.min(totalItems, startIndex + visibleCount + overscan * 2);
  const offsetY = startIndex * itemHeight;

  return { startIndex, endIndex, offsetY, totalHeight: totalItems * itemHeight, onScroll };
}
