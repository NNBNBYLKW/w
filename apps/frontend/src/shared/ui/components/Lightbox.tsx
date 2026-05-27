import { useState } from "react";
import { Modal } from "./Modal";

interface LightboxProps {
  open: boolean;
  src: string;
  alt?: string;
  onClose: () => void;
}

export function Lightbox({ open, src, alt, onClose }: LightboxProps) {
  const [scale, setScale] = useState(1);
  return (
    <Modal open={open} onClose={onClose} title={alt ?? "Preview"} width={960}>
      <div style={{ textAlign: "center", overflow: "hidden" }}>
        <img
          src={src} alt={alt}
          style={{ maxWidth: "100%", maxHeight: "70vh", transform: `scale(${scale})`, transition: "transform 0.2s", cursor: scale > 1 ? "grab" : "zoom-in" }}
          onClick={() => setScale(s => s > 1 ? 1 : 2)}
        />
      </div>
    </Modal>
  );
}
