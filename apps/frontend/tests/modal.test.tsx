import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Modal } from "../src/shared/ui/components/Modal";

describe("Modal", () => {
  it("renders nothing when closed", () => {
    render(<Modal open={false} onClose={() => {}} title="Test"><p>content</p></Modal>);
    expect(screen.queryByText("Test")).toBeNull();
  });

  it("renders title and children when open", () => {
    render(<Modal open={true} onClose={() => {}} title="My Title"><p>body text</p></Modal>);
    expect(screen.getByText("My Title")).toBeInTheDocument();
    expect(screen.getByText("body text")).toBeInTheDocument();
  });

  it("calls onClose on Escape key", async () => {
    const onClose = vi.fn();
    render(<Modal open={true} onClose={onClose} title="X"><p>a</p></Modal>);
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose on overlay click", () => {
    const onClose = vi.fn();
    render(<Modal open={true} onClose={onClose} title="X"><p>a</p></Modal>);
    const overlay = screen.getByRole("dialog").parentElement!;
    fireEvent.click(overlay);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("renders footer when provided", () => {
    render(<Modal open={true} onClose={() => {}} title="X" footer={<button>Save</button>}><p>a</p></Modal>);
    expect(screen.getByText("Save")).toBeInTheDocument();
  });
});
