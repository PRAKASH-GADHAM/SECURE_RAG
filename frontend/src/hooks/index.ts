import { useEffect, useRef, useCallback, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notificationService } from "@/services";

export function useKeyboardShortcut(
  key: string,
  callback: () => void,
  modifiers: { ctrl?: boolean; shift?: boolean; alt?: boolean } = {},
) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === key) {
        if (modifiers.ctrl && !e.ctrlKey && !e.metaKey) return;
        if (modifiers.shift && !e.shiftKey) return;
        if (modifiers.alt && !e.altKey) return;
        e.preventDefault();
        callback();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [key, callback, modifiers]);
}

export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debouncedValue;
}

export function useLocalStorage<T>(key: string, initialValue: T): [T, (value: T) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const setValue = useCallback(
    (value: T) => {
      setStoredValue(value);
      window.localStorage.setItem(key, JSON.stringify(value));
    },
    [key],
  );

  return [storedValue, setValue];
}

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia(query);
    setMatches(mq.matches);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [query]);
  return matches;
}

export function useIntersectionObserver(
  ref: React.RefObject<HTMLElement | null>,
  options?: IntersectionObserverInit,
): boolean {
  const [isVisible, setIsVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry) setIsVisible(entry.isIntersecting);
    }, options);
    observer.observe(el);
    return () => observer.disconnect();
  }, [ref, options]);
  return isVisible;
}

export function useStreamingResponse() {
  const [content, setContent] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const startStream = useCallback(async (params: {
    query: string;
    session_id?: string;
    retrieval_mode?: string;
    top_k?: number;
  }) => {
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    setIsStreaming(true);
    setContent("");

    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch("/api/v1/chat/query/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(params),
        signal: abortRef.current.signal,
      });

      const reader = res.body?.getReader();
      if (!reader) return;
      const decoder = new TextDecoder();
      let accumulated = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value);
        const lines = text.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data === "[DONE]") break;
            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                accumulated += parsed.content;
                setContent(accumulated);
              }
            } catch {
              accumulated += data;
              setContent(accumulated);
            }
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") throw err;
    } finally {
      setIsStreaming(false);
    }
  }, []);

  const stopStream = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
  }, []);

  return { content, isStreaming, startStream, stopStream };
}

export function useNotifications() {
  const queryClient = useQueryClient();

  const { data: notifications, isLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: notificationService.list,
    refetchInterval: 60000,
  });

  const markReadMutation = useMutation({
    mutationFn: notificationService.markRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const markAllReadMutation = useMutation({
    mutationFn: notificationService.markAllRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const dismissMutation = useMutation({
    mutationFn: notificationService.dismiss,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const unreadCount = notifications?.filter((n) => !n.read).length ?? 0;

  return {
    notifications: notifications ?? [],
    unreadCount,
    isLoading,
    markRead: markReadMutation.mutate,
    markAllRead: markAllReadMutation.mutate,
    dismiss: dismissMutation.mutate,
  };
}

export function useHealthPoll(intervalMs = 30000) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const { healthService } = await import("@/services");
      return healthService.getHealth();
    },
    refetchInterval: intervalMs,
    retry: false,
  });

  return { health: data, isLoading, error, refetch };
}
