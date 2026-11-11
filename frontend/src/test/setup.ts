import "@testing-library/jest-dom/vitest";

// jsdom không có ResizeObserver (Recharts, Radix cần)
class RO { observe() {} unobserve() {} disconnect() {} }
(globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver ??= RO;
