import { AnimatePresence, motion } from "motion/react";
import { useEffect, useId, useRef, type ReactNode } from "react";
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
 *
 * Keyboard a11y:
 *   - Auto-focuses the close button (or first focusable) on open.
 *   - Traps Tab/Shift+Tab within the dialog.
 *   - Restores focus to the element that opened the modal on close.
 *   - Escape key closes the dialog.
 */
export default function Modal({ open, onClose, title, children, size = "md" }: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  // Track the element that had focus before the modal opened so we can restore it.
  const triggerRef = useRef<HTMLElement | null>(null);
  // Stable ID for aria-labelledby association.
  const titleId = useId();

  // Escape key + body scroll lock
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

  // Focus-on-open + restore-on-close
  useEffect(() => {
    if (open) {
      triggerRef.current = document.activeElement as HTMLElement;
      // Wait for AnimatePresence to mount the dialog before querying focusables.
      requestAnimationFrame(() => {
        const focusable = dialogRef.current?.querySelector<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        focusable?.focus();
      });
    } else {
      triggerRef.current?.focus();
    }
  }, [open]);

  // Tab key trap — keep focus inside the dialog
  useEffect(() => {
    if (!open) return;
    const trapTab = (e: KeyboardEvent) => {
      if (e.key !== "Tab" || !dialogRef.current) return;
      const focusables = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )
      );
      if (focusables.length === 0) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", trapTab);
    return () => document.removeEventListener("keydown", trapTab);
  }, [open]);

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
            ref={dialogRef}
            className={s.dialog}
            data-size={size}
            initial={{ opacity: 0, scale: 0.94, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={enterSpring}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby={title ? titleId : undefined}
          >
            <div className={s.header}>
              {title && <h3 id={titleId} className={s.title}>{title}</h3>}
              <button className={s.close} onClick={onClose} aria-label="Close">
                <CloseIcon />
              </button>
            </div>
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