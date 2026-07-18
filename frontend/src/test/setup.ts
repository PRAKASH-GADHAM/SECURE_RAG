import "@testing-library/jest-dom";

class MockResizeObserver {
  callback: ResizeObserverCallback;
  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
  }
  observe() { return null; }
  unobserve() { return null; }
  disconnect() { return null; }
}

globalThis.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;

globalThis.fetch = async () => new Response(null, { status: 404 });
