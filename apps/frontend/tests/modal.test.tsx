import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Modal } from "../src/shared/ui/components/Modal";
import { ConfirmDialog } from "../src/shared/ui/components/ConfirmDialog";

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

describe("ConfirmDialog", () => {
  it("renders title, message, and buttons", () => {
    render(<ConfirmDialog open={true} title="Delete?" message="This cannot be undone." onConfirm={() => {}} onCancel={() => {}} />);
    expect(screen.getByText("Delete?")).toBeInTheDocument();
    expect(screen.getByText("This cannot be undone.")).toBeInTheDocument();
    expect(screen.getByText("Confirm")).toBeInTheDocument();
    expect(screen.getByText("Cancel")).toBeInTheDocument();
  });

  it("calls onConfirm when confirm clicked", () => {
    const onConfirm = vi.fn();
    render(<ConfirmDialog open={true} title="X" message="Y" onConfirm={onConfirm} onCancel={() => {}} />);
    fireEvent.click(screen.getByText("Confirm"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("calls onCancel when cancel clicked", () => {
    const onCancel = vi.fn();
    render(<ConfirmDialog open={true} title="X" message="Y" onConfirm={() => {}} onCancel={onCancel} />);
    fireEvent.click(screen.getByText("Cancel"));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
