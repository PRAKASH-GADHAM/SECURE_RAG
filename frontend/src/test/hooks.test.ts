import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDebounce, useLocalStorage, useMediaQuery, useKeyboardShortcut } from "@/hooks";

describe("useDebounce", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns initial value immediately", () => {
    const { result } = renderHook(() => useDebounce("hello", 500));
    expect(result.current).toBe("hello");
  });

  it("returns debounced value after delay", () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: "hello", delay: 500 } },
    );

    expect(result.current).toBe("hello");

    rerender({ value: "world", delay: 500 });
    expect(result.current).toBe("hello");

    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(result.current).toBe("world");
  });

  it("resets timer on rapid updates", () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: "a", delay: 500 } },
    );

    rerender({ value: "b", delay: 500 });
    act(() => { vi.advanceTimersByTime(300); });

    rerender({ value: "c", delay: 500 });
    act(() => { vi.advanceTimersByTime(300); });

    expect(result.current).toBe("a");

    act(() => { vi.advanceTimersByTime(200); });
    expect(result.current).toBe("c");
  });
});

describe("useLocalStorage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("reads initial value when no stored value exists", () => {
    const { result } = renderHook(() => useLocalStorage<string>("test-key", "default"));
    expect(result.current[0]).toBe("default");
  });

  it("reads stored value from localStorage", () => {
    localStorage.setItem("test-key", JSON.stringify("stored"));
    const { result } = renderHook(() => useLocalStorage<string>("test-key", "default"));
    expect(result.current[0]).toBe("stored");
  });

  it("updates localStorage when value is set", () => {
    const { result } = renderHook(() => useLocalStorage<string>("test-key", "default"));

    act(() => {
      result.current[1]("updated");
    });

    expect(result.current[0]).toBe("updated");
    expect(JSON.parse(localStorage.getItem("test-key")!)).toBe("updated");
  });

  it("handles JSON parse errors gracefully", () => {
    localStorage.setItem("test-key", "not-valid-json{{{");
    const { result } = renderHook(() => useLocalStorage<string>("test-key", "fallback"));
    expect(result.current[0]).toBe("fallback");
  });
});

describe("useMediaQuery", () => {
  it("returns false when no match by default", () => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    });

    const { result } = renderHook(() => useMediaQuery("(min-width: 768px)"));
    expect(result.current).toBe(false);
  });

  it("returns true when query matches", () => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: true,
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    });

    const { result } = renderHook(() => useMediaQuery("(min-width: 768px)"));
    expect(result.current).toBe(true);
  });

  it("responds to media query changes", () => {
    let changeHandler: ((e: MediaQueryListEvent) => void) | undefined;

    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        addEventListener: vi.fn((_: string, handler: (e: MediaQueryListEvent) => void) => {
          changeHandler = handler;
        }),
        removeEventListener: vi.fn(),
      })),
    });

    const { result } = renderHook(() => useMediaQuery("(min-width: 768px)"));
    expect(result.current).toBe(false);

    act(() => {
      changeHandler?.({ matches: true } as MediaQueryListEvent);
    });

    expect(result.current).toBe(true);
  });
});

describe("useKeyboardShortcut", () => {
  it("fires callback on key press", () => {
    const callback = vi.fn();
    renderHook(() => useKeyboardShortcut("k", callback));

    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "k" }));
    });

    expect(callback).toHaveBeenCalledTimes(1);
  });

  it("does not fire callback for different key", () => {
    const callback = vi.fn();
    renderHook(() => useKeyboardShortcut("k", callback));

    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "j" }));
    });

    expect(callback).not.toHaveBeenCalled();
  });

  it("respects ctrl modifier", () => {
    const callback = vi.fn();
    renderHook(() => useKeyboardShortcut("k", callback, { ctrl: true }));

    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: false }));
    });
    expect(callback).not.toHaveBeenCalled();

    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }));
    });
    expect(callback).toHaveBeenCalledTimes(1);
  });

  it("respects shift modifier", () => {
    const callback = vi.fn();
    renderHook(() => useKeyboardShortcut("k", callback, { shift: true }));

    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", shiftKey: false }));
    });
    expect(callback).not.toHaveBeenCalled();

    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", shiftKey: true }));
    });
    expect(callback).toHaveBeenCalledTimes(1);
  });
});
