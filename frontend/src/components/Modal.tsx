import { AnimatePresence, motion } from "motion/react";
import { useEffect, type ReactNode } from "react";
import { enterSpring, quickSpring } from "../styles/springs";
import s from "./Modal.module.css";

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  children: ReactNode;
  size?: "md" | "lg";
}

/**
 * Universal glass dialog. Spring-scale entrance mirrors the Flutter modal-sheet
 * presentation; the checkmark/submit pattern lives in the caller.
 */
export default function Modal({ open, onClose, title, children, size = "md" }: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className={s.scrim}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={quickSpring}
          onClick={onClose}
        >
          <motion.div
            className={s.dialog}
            data-size={size}
            initial={{ opacity: 0, scale: 0.94, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={enterSpring}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            {title && (
              <div className={s.header}>
                <h3 className={s.title}>{title}</h3>
                <button className={s.close} onClick={onClose} aria-label="Close">
                  <CloseIcon />
                </button>
              </div>
            )}
            <div className={s.body}>{children}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}