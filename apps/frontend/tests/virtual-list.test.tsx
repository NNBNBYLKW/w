import { describe, test, expect } from "vitest";

describe("useVirtualList", () => {
  // useVirtualList requires ResizeObserver + scroll events not available in jsdom
  test("placeholder — module exists and exports correctly", async () => {
    const mod = await import("../src/shared/hooks/useVirtualList");
    expect(typeof mod.useVirtualList).toBe("function");
  });
});
