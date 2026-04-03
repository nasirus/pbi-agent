import { useEffect, useState, type ReactNode } from "react";

interface Props {
  title: string;
  body: ReactNode;
  confirmLabel?: string;
  onConfirm: () => Promise<void>;
  onClose: () => void;
}

export function DeleteConfirmModal({
  title,
  body,
  confirmLabel = "Delete",
  onConfirm,
  onClose,
}: Props) {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  async function handleConfirm() {
    setIsPending(true);
    setError(null);
    try {
      await onConfirm();
    } catch (err) {
      setError((err as Error).message);
      setIsPending(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-card modal-card--confirm"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-card__header">
          <h2 className="modal-card__title">{title}</h2>
          <button
            type="button"
            className="modal-card__close"
            onClick={onClose}
            disabled={isPending}
          >
            &times;
          </button>
        </div>
        <div className="confirm-modal">
          <div className="confirm-modal__body">{body}</div>
          {error && <div className="confirm-modal__error">{error}</div>}
          <div className="confirm-modal__actions">
            <button
              type="button"
              className="btn btn--ghost"
              onClick={onClose}
              disabled={isPending}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn btn--danger"
              onClick={() => {
                void handleConfirm();
              }}
              disabled={isPending}
            >
              {isPending ? "Deleting…" : confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
