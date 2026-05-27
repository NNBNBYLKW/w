import { Modal } from "./Modal";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({ open, title, message, confirmLabel = "Confirm", onConfirm, onCancel }: ConfirmDialogProps) {
  return (
    <Modal
      open={open}
      onClose={onCancel}
      title={title}
      footer={
        <>
          <button className="secondary-button" onClick={onCancel}>Cancel</button>
          <button className="primary-button" onClick={onConfirm}>{confirmLabel}</button>
        </>
      }
    >
      <p style={{ color: "var(--color-text-secondary, #666)", lineHeight: 1.6 }}>{message}</p>
    </Modal>
  );
}
