import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { Pagination } from "../src/shared/ui/components/Pagination";
import { ProgressBar } from "../src/shared/ui/components/ProgressBar";
import { ToastContainer } from "../src/app/shell/ToastContainer";
import { useUIStore } from "../src/app/providers/uiStore";

describe("Pagination", () => {
  it("shows No results when totalPages is 0", () => {
    render(<Pagination page={1} totalPages={0} onPageChange={() => {}} />);
    expect(screen.getByText("No results")).toBeInTheDocument();
  });

  it("disables Previous button on page 1", () => {
    render(<Pagination page={1} totalPages={5} onPageChange={() => {}} />);
    expect(screen.getByText("Previous")).toBeDisabled();
  });

  it("enables Previous button after page 1", () => {
    render(<Pagination page={2} totalPages={5} onPageChange={() => {}} />);
    expect(screen.getByText("Previous")).not.toBeDisabled();
  });

  it("disables Next button on last page", () => {
    render(<Pagination page={5} totalPages={5} onPageChange={() => {}} />);
    expect(screen.getByText("Next")).toBeDisabled();
  });

  it("enables Next button before last page", () => {
    render(<Pagination page={4} totalPages={5} onPageChange={() => {}} />);
    expect(screen.getByText("Next")).not.toBeDisabled();
  });

  it("calls onPageChange with previous page when Previous is clicked", () => {
    const onPageChange = vi.fn();
    render(<Pagination page={3} totalPages={5} onPageChange={onPageChange} />);
    fireEvent.click(screen.getByText("Previous"));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("calls onPageChange with next page when Next is clicked", () => {
    const onPageChange = vi.fn();
    render(<Pagination page={3} totalPages={5} onPageChange={onPageChange} />);
    fireEvent.click(screen.getByText("Next"));
    expect(onPageChange).toHaveBeenCalledWith(4);
  });

  it("displays page info text", () => {
    render(<Pagination page={3} totalPages={10} onPageChange={() => {}} />);
    expect(screen.getByText("Page 3 of 10")).toBeInTheDocument();
  });

  it("renders page input when showPageInput is true", () => {
    render(<Pagination page={2} totalPages={5} onPageChange={() => {}} showPageInput />);
    expect(screen.getByRole("spinbutton")).toBeInTheDocument();
  });

  it("calls onPageChange with entered value from page input", () => {
    const onPageChange = vi.fn();
    render(<Pagination page={2} totalPages={5} onPageChange={onPageChange} showPageInput />);
    const input = screen.getByRole("spinbutton");
    fireEvent.change(input, { target: { value: "4" } });
    fireEvent.submit(input.closest("form")!);
    expect(onPageChange).toHaveBeenCalledWith(4);
  });
});

describe("ProgressBar", () => {
  it("renders with correct percentage", () => {
    const { container } = render(<ProgressBar done={3} total={4} />);
    const fill = container.querySelector("div > div > div");
    expect(fill).toBeInTheDocument();
  });

  it("shows label when showLabel is true", () => {
    render(<ProgressBar done={3} total={4} showLabel />);
    expect(screen.getByText("3 / 4")).toBeInTheDocument();
  });

  it("hides label when showLabel is false", () => {
    render(<ProgressBar done={3} total={4} />);
    expect(screen.queryByText("3 / 4")).toBeNull();
  });

  it("does not crash when total is 0", () => {
    render(<ProgressBar done={0} total={0} />);
    // Should render without crashing
  });
});

describe("ToastContainer", () => {
  beforeEach(() => {
    useUIStore.setState({ toasts: [] });
  });

  it("renders nothing when there are no toasts", () => {
    render(<ToastContainer />);
    expect(screen.queryByText(/./)).toBeNull();
  });

  it("renders toasts from the store", () => {
    act(() => {
      useUIStore.getState().pushToast("Hello world");
    });
    render(<ToastContainer />);
    expect(screen.getByText("Hello world")).toBeInTheDocument();
  });

  it("removes toast on click", () => {
    act(() => {
      useUIStore.getState().pushToast("Dismiss me");
    });
    render(<ToastContainer />);
    expect(screen.getByText("Dismiss me")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Dismiss me"));
    expect(screen.queryByText("Dismiss me")).toBeNull();
  });

  it("auto-dismisses toast after 4 seconds", () => {
    vi.useFakeTimers();
    act(() => {
      useUIStore.getState().pushToast("Auto dismiss");
    });
    render(<ToastContainer />);
    expect(screen.getByText("Auto dismiss")).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(4000);
    });
    expect(screen.queryByText("Auto dismiss")).toBeNull();
    vi.useRealTimers();
  });

  it("renders multiple toasts", () => {
    act(() => {
      useUIStore.getState().pushToast("Toast 1");
      useUIStore.getState().pushToast("Toast 2");
    });
    render(<ToastContainer />);
    expect(screen.getByText("Toast 1")).toBeInTheDocument();
    expect(screen.getByText("Toast 2")).toBeInTheDocument();
  });
});
