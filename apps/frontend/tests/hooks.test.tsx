import { describe, test, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { useErrorMessage } from "../src/shared/hooks/useErrorMessage";

describe("useErrorMessage", () => {
  test("returns user-friendly message for known error code", () => {
    const error = Object.assign(new Error("scan running"), { code: "SCAN_ALREADY_RUNNING" });
    const { result } = renderHook(() => useErrorMessage(error));
    expect(result.current).toContain("scan is already running");
  });

  test("returns raw message for unknown error", () => {
    const error = new Error("something unique broke");
    const { result } = renderHook(() => useErrorMessage(error));
    expect(result.current).toBe("something unique broke");
  });

  test("returns string for non-Error values", () => {
    const { result } = renderHook(() => useErrorMessage("plain string error"));
    expect(result.current).toBe("plain string error");
  });
});
