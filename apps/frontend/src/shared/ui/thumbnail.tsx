import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";

import { warmupFileThumbnails } from "../../services/api/fileDetailsApi";
import type { ThumbnailWarmupResponseVM } from "../../services/api/fileDetailsApi";

const DEFAULT_RETRY_DELAYS_MS = [800, 2000, 5000] as const;
const DEFAULT_ROOT_MARGIN = "240px";
const WARMUP_BATCH_SIZE = 20;
const WARMUP_DEBOUNCE_MS = 250;
const WARMUP_FAST_POLL_MS = 2000;
const WARMUP_SLOW_POLL_MS = 5000;
const WARMUP_FAST_WINDOW_MS = 20000;
const WARMUP_MAX_WINDOW_MS = 60000;

function appendThumbnailQueryParams(url: string, params: Record<string, number | string | undefined>): string {
  const queryParts = Object.entries(params)
    .filter(([, value]) => value !== undefined && value !== "")
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);

  if (queryParts.length === 0) {
    return url;
  }

  const hashIndex = url.indexOf("#");
  const urlWithoutHash = hashIndex >= 0 ? url.slice(0, hashIndex) : url;
  const hash = hashIndex >= 0 ? url.slice(hashIndex) : "";
  const separator = urlWithoutHash.includes("?") ? "&" : "?";
  return `${urlWithoutHash}${separator}${queryParts.join("&")}${hash}`;
}

function normalizeWarmupFileIds(fileIds: ReadonlyArray<unknown> | null | undefined): number[] {
  if (!Array.isArray(fileIds)) {
    return [];
  }

  const normalizedIds: number[] = [];
  const seenIds = new Set<number>();
  for (const value of fileIds) {
    const id = typeof value === "number" ? value : typeof value === "string" ? Number(value) : Number.NaN;
    if (!Number.isFinite(id) || id <= 0 || seenIds.has(id)) {
      continue;
    }
    seenIds.add(id);
    normalizedIds.push(id);
  }
  return normalizedIds;
}

function normalizeWarmupResponse(response: Partial<ThumbnailWarmupResponseVM> | null | undefined): ThumbnailWarmupResponseVM {
  return {
    cached: Array.isArray(response?.cached) ? response.cached : [],
    queued: Array.isArray(response?.queued) ? response.queued : [],
    in_progress: Array.isArray(response?.in_progress) ? response.in_progress : [],
    unsupported: Array.isArray(response?.unsupported) ? response.unsupported : [],
    missing: Array.isArray(response?.missing) ? response.missing : [],
    failed: Array.isArray(response?.failed) ? response.failed : [],
  };
}

export function useRetryingThumbnail<TElement extends Element>({
  enabled = true,
  onLoad,
  refreshToken = 0,
  rootMargin = DEFAULT_ROOT_MARGIN,
  thumbnailUrl,
  visibleOnly = false,
}: {
  enabled?: boolean;
  onLoad?: () => void;
  refreshToken?: number;
  rootMargin?: string;
  thumbnailUrl?: string;
  visibleOnly?: boolean;
}) {
  const elementRef = useRef<TElement | null>(null);
  const retryTimerRef = useRef<number | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [failed, setFailed] = useState(false);
  const [waitingToRetry, setWaitingToRetry] = useState(false);
  const [retryToken, setRetryToken] = useState(0);
  const [visible, setVisible] = useState(!visibleOnly);

  const clearRetryTimer = useCallback(() => {
    if (retryTimerRef.current !== null) {
      window.clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    clearRetryTimer();
    setAttempt(0);
    setFailed(false);
    setWaitingToRetry(false);
    setRetryToken(0);
    setVisible(!visibleOnly);
  }, [clearRetryTimer, enabled, thumbnailUrl, visibleOnly]);

  useEffect(() => {
    clearRetryTimer();
    setAttempt(0);
    setFailed(false);
    setWaitingToRetry(false);
    setRetryToken(0);
  }, [clearRetryTimer, refreshToken]);

  useEffect(() => {
    if (!visibleOnly || visible || typeof window === "undefined") {
      return;
    }
    if (!("IntersectionObserver" in window)) {
      setVisible(true);
      return;
    }

    const element = elementRef.current;
    if (!element) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin },
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, [rootMargin, visible, visibleOnly]);

  useEffect(() => clearRetryTimer, [clearRetryTimer]);

  const setThumbnailElement = useCallback((element: TElement | null) => {
    elementRef.current = element;
  }, []);

  const handleThumbnailError = useCallback(() => {
    clearRetryTimer();

    const delay = DEFAULT_RETRY_DELAYS_MS[attempt];
    if (delay === undefined) {
      setFailed(true);
      setWaitingToRetry(false);
      return;
    }

    setWaitingToRetry(true);
    retryTimerRef.current = window.setTimeout(() => {
      setAttempt((currentAttempt) => currentAttempt + 1);
      setRetryToken(Date.now());
      setWaitingToRetry(false);
      retryTimerRef.current = null;
    }, delay);
  }, [attempt, clearRetryTimer]);

  const imageSrc = useMemo(() => {
    if (!thumbnailUrl) {
      return undefined;
    }
    return appendThumbnailQueryParams(thumbnailUrl, {
      thumbnailRefresh: refreshToken > 0 ? refreshToken : undefined,
      thumbnailRetry: attempt > 0 ? attempt : undefined,
      thumbnailTs: retryToken > 0 ? retryToken : undefined,
    });
  }, [attempt, refreshToken, retryToken, thumbnailUrl]);

  const handleThumbnailLoad = useCallback(() => {
    onLoad?.();
  }, [onLoad]);

  const shouldRenderImage = Boolean(enabled && thumbnailUrl && visible && !failed && !waitingToRetry);

  return {
    failed,
    imageSrc,
    onError: handleThumbnailError,
    onLoad: handleThumbnailLoad,
    ref: setThumbnailElement,
    shouldRenderImage,
  };
}

async function warmupInBatches(fileIds: number[]) {
  const responses: ThumbnailWarmupResponseVM[] = [];
  for (let index = 0; index < fileIds.length; index += WARMUP_BATCH_SIZE) {
    const batch = fileIds.slice(index, index + WARMUP_BATCH_SIZE);
    responses.push(normalizeWarmupResponse(await warmupFileThumbnails(batch)));
  }
  return responses;
}

type ThumbnailWarmupState = {
  finalFallbackIds: Set<number>;
  loadedIds: Set<number>;
  pendingIds: Set<number>;
  readyIds: Set<number>;
  refreshTokensById: Map<number, number>;
};

type ThumbnailWarmupAction =
  | { type: "reset" }
  | { type: "loaded"; fileId: number }
  | { type: "applyResponses"; responses: ThumbnailWarmupResponseVM[]; token: number };

function createEmptyThumbnailWarmupState(): ThumbnailWarmupState {
  return {
    finalFallbackIds: new Set(),
    loadedIds: new Set(),
    pendingIds: new Set(),
    readyIds: new Set(),
    refreshTokensById: new Map(),
  };
}

function thumbnailWarmupReducer(state: ThumbnailWarmupState, action: ThumbnailWarmupAction): ThumbnailWarmupState {
  if (action.type === "reset") {
    return createEmptyThumbnailWarmupState();
  }

  if (action.type === "loaded") {
    const loadedIds = new Set(state.loadedIds);
    const readyIds = new Set(state.readyIds);
    const pendingIds = new Set(state.pendingIds);
    const finalFallbackIds = new Set(state.finalFallbackIds);

    loadedIds.add(action.fileId);
    readyIds.add(action.fileId);
    pendingIds.delete(action.fileId);
    finalFallbackIds.delete(action.fileId);

    return {
      ...state,
      finalFallbackIds,
      loadedIds,
      pendingIds,
      readyIds,
    };
  }

  const finalFallbackIds = new Set(state.finalFallbackIds);
  const loadedIds = new Set(state.loadedIds);
  const pendingIds = new Set(state.pendingIds);
  const readyIds = new Set(state.readyIds);
  const refreshTokensById = new Map(state.refreshTokensById);

  for (const response of action.responses) {
    for (const id of response.cached) {
      pendingIds.delete(id);
      finalFallbackIds.delete(id);
      if (!readyIds.has(id) && !loadedIds.has(id)) {
        readyIds.add(id);
        refreshTokensById.set(id, action.token);
      }
    }

    for (const id of [...response.unsupported, ...response.missing, ...response.failed]) {
      pendingIds.delete(id);
      if (!readyIds.has(id) && !loadedIds.has(id)) {
        finalFallbackIds.add(id);
      }
    }

    for (const id of [...response.queued, ...response.in_progress]) {
      if (!readyIds.has(id) && !loadedIds.has(id) && !finalFallbackIds.has(id)) {
        pendingIds.add(id);
      }
    }
  }

  return {
    finalFallbackIds,
    loadedIds,
    pendingIds,
    readyIds,
    refreshTokensById,
  };
}

function applyWarmupResponsesToPendingSet(
  currentPendingIds: Set<number>,
  currentReadyIds: Set<number>,
  currentLoadedIds: Set<number>,
  currentFinalFallbackIds: Set<number>,
  responses: ThumbnailWarmupResponseVM[],
): Set<number> {
  const nextPendingIds = new Set(currentPendingIds);
  const nextFinalFallbackIds = new Set(currentFinalFallbackIds);

  for (const response of responses) {
    for (const id of response.cached) {
      nextPendingIds.delete(id);
      nextFinalFallbackIds.delete(id);
    }
    for (const id of [...response.unsupported, ...response.missing, ...response.failed]) {
      nextPendingIds.delete(id);
      if (!currentReadyIds.has(id) && !currentLoadedIds.has(id)) {
        nextFinalFallbackIds.add(id);
      }
    }
    for (const id of [...response.queued, ...response.in_progress]) {
      if (!currentReadyIds.has(id) && !currentLoadedIds.has(id) && !nextFinalFallbackIds.has(id)) {
        nextPendingIds.add(id);
      }
    }
  }

  return nextPendingIds;
}

export function useThumbnailWarmup(fileIds: ReadonlyArray<unknown> | null | undefined) {
  const idsKey = useMemo(() => normalizeWarmupFileIds(fileIds).join(","), [fileIds]);
  const normalizedFileIds = useMemo(() => normalizeWarmupFileIds(idsKey ? idsKey.split(",") : []), [idsKey]);
  const [state, dispatch] = useReducer(thumbnailWarmupReducer, undefined, createEmptyThumbnailWarmupState);
  const finalFallbackIdsRef = useRef(state.finalFallbackIds);
  const loadedIdsRef = useRef(state.loadedIds);
  const pendingIdsRef = useRef(state.pendingIds);
  const readyIdsRef = useRef(state.readyIds);

  useEffect(() => {
    finalFallbackIdsRef.current = state.finalFallbackIds;
    loadedIdsRef.current = state.loadedIds;
    pendingIdsRef.current = state.pendingIds;
    readyIdsRef.current = state.readyIds;
  }, [state.finalFallbackIds, state.loadedIds, state.pendingIds, state.readyIds]);

  useEffect(() => {
    let canceled = false;
    let timer: number | null = null;
    const startedAt = Date.now();

    dispatch({ type: "reset" });
    finalFallbackIdsRef.current = new Set();
    loadedIdsRef.current = new Set();
    pendingIdsRef.current = new Set();
    readyIdsRef.current = new Set();

    if (normalizedFileIds.length === 0) {
      return () => {
        canceled = true;
      };
    }

    const requestWarmup = async (ids: number[]) => {
      if (ids.length === 0) {
        return;
      }
      try {
        const responses = await warmupInBatches(ids);
        if (!canceled) {
          pendingIdsRef.current = applyWarmupResponsesToPendingSet(
            pendingIdsRef.current,
            readyIdsRef.current,
            loadedIdsRef.current,
            finalFallbackIdsRef.current,
            responses,
          );
          dispatch({ type: "applyResponses", responses, token: Date.now() });
        }
      } catch {
        // Keep thumbnail loading best-effort; individual img retry still handles transient failures.
      }
    };

    const pollPending = async () => {
      if (canceled || pendingIdsRef.current.size === 0 || Date.now() - startedAt > WARMUP_MAX_WINDOW_MS) {
        return;
      }
      await requestWarmup([...pendingIdsRef.current]);
      const nextDelay = Date.now() - startedAt < WARMUP_FAST_WINDOW_MS ? WARMUP_FAST_POLL_MS : WARMUP_SLOW_POLL_MS;
      if (!canceled && pendingIdsRef.current.size > 0) {
        timer = window.setTimeout(() => {
          void pollPending();
        }, nextDelay);
      }
    };

    timer = window.setTimeout(() => {
      void requestWarmup(normalizedFileIds).then(() => pollPending());
    }, WARMUP_DEBOUNCE_MS);

    return () => {
      canceled = true;
      if (timer !== null) {
        window.clearTimeout(timer);
      }
    };
  }, [normalizedFileIds]);

  const getRefreshToken = useCallback((fileId: number) => state.refreshTokensById.get(fileId) ?? 0, [state.refreshTokensById]);

  const isThumbnailDisabled = useCallback((fileId: number) => state.finalFallbackIds.has(fileId), [state.finalFallbackIds]);

  const markLoaded = useCallback((fileId: number) => {
    if (!Number.isFinite(fileId) || fileId <= 0) {
      return;
    }
    pendingIdsRef.current = new Set([...pendingIdsRef.current].filter((id) => id !== fileId));
    finalFallbackIdsRef.current = new Set([...finalFallbackIdsRef.current].filter((id) => id !== fileId));
    loadedIdsRef.current = new Set(loadedIdsRef.current).add(fileId);
    readyIdsRef.current = new Set(readyIdsRef.current).add(fileId);
    dispatch({ type: "loaded", fileId });
  }, []);

  const isPending = useCallback((fileId: number) => state.pendingIds.has(fileId), [state.pendingIds]);

  return {
    getRefreshToken,
    isPermanentFallback: isThumbnailDisabled,
    isPending,
    isThumbnailDisabled,
    markLoaded,
  };
}
