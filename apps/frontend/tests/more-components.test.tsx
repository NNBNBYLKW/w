import { describe, test, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CardSkeleton } from "../src/shared/ui/components/CardSkeleton";
import { Lightbox } from "../src/shared/ui/components/Lightbox";
import { ErrorState } from "../src/shared/ui/components/ErrorState";
import { EmptyState } from "../src/shared/ui/components/EmptyState";

describe("CardSkeleton", () => {
  test("renders default count of 6", () => {
    render(<CardSkeleton />);
    const cards = document.querySelectorAll(".skeleton-card");
    expect(cards.length).toBe(6);
  });

  test("renders custom count", () => {
    render(<CardSkeleton count={3} />);
    const cards = document.querySelectorAll(".skeleton-card");
    expect(cards.length).toBe(3);
  });
});

describe("Lightbox", () => {
  test("renders nothing when closed", () => {
    render(<Lightbox open={false} src="/img.jpg" onClose={() => {}} />);
    expect(screen.queryByRole("img")).toBeNull();
  });

  test("renders image when open", () => {
    render(<Lightbox open={true} src="/img.jpg" alt="test" onClose={() => {}} />);
    expect(screen.getByRole("img")).toHaveAttribute("src", "/img.jpg");
  });

  test("click toggles zoom scale", () => {
    render(<Lightbox open={true} src="/img.jpg" onClose={() => {}} />);
    const img = screen.getByRole("img");
    expect(img.style.transform).toBe("scale(1)");
    fireEvent.click(img);
    expect(img.style.transform).toBe("scale(2)");
    fireEvent.click(img);
    expect(img.style.transform).toBe("scale(1)");
  });
});

describe("ErrorState", () => {
  test("renders message text", () => {
    render(<ErrorState message="Something failed" />);
    expect(screen.getByText("Something failed")).toBeInTheDocument();
  });

  test("calls onRetry when Retry button clicked", () => {
    const retry = vi.fn();
    render(<ErrorState message="Failed" onRetry={retry} />);
    fireEvent.click(screen.getByText("Retry"));
    expect(retry).toHaveBeenCalledTimes(1);
  });
});

describe("EmptyState", () => {
  test("renders title and description", () => {
    render(<EmptyState title="No items" description="Add items to get started" />);
    expect(screen.getByText("No items")).toBeInTheDocument();
  });

  test("renders action button when provided", () => {
    render(<EmptyState title="Empty" description="" action={{ label: "Add Item", onClick: vi.fn() }} />);
    expect(screen.getByText("Add Item")).toBeInTheDocument();
  });
});
