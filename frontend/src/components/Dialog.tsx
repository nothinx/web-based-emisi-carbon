import { useEffect, useRef, type ReactNode } from "react";
import "./dialog.css";

// Native <dialog>: escape stacking context / overflow clipping (lihat DESIGN.md).
export function Dialog({
  open,
  onClose,
  title,
  children,
  width = 520,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  width?: number;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className="dialog"
      style={{ maxWidth: width }}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        // Klik backdrop (di luar konten) menutup.
        if (e.target === ref.current) onClose();
      }}
    >
      <div className="dialog-body">
        <header className="dialog-head">
          <h2>{title}</h2>
          <button className="dialog-x" onClick={onClose} aria-label="Tutup">
            ✕
          </button>
        </header>
        {children}
      </div>
    </dialog>
  );
}
