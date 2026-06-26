import { AnimatePresence, motion } from "motion/react";
import { popSpring, quickSpring } from "../styles/springs";
import s from "./Button.module.css";

export type ButtonVariant = "primary" | "ghost" | "outline" | "danger";
export type ButtonSize = "sm" | "md" | "lg";
export type SubmitPhase = "idle" | "loading" | "success";

export interface ButtonProps
  extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "title"> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  block?: boolean;
  /** Renders the 3-phase submit state machine (idle → spinner → spring checkmark).
   *  Ports log_progress_sheet.dart:1214-1304. When phase !== "idle" the button is
   *  disabled and its label is replaced by the phase indicator. */
  submitPhase?: SubmitPhase;
  /** Label text shown when idle / override for the idle phase. */
  label?: React.ReactNode;
}

/**
 * Unified tactile button. `submitPhase` drives the premium submit animation:
 * idle → spinner → elasticOut checkmark pop (popSpring), matching the Flutter
 * submit CTA.
 */
export default function Button({
  variant = "primary",
  size = "md",
  block = false,
  submitPhase = "idle",
  label,
  children,
  disabled,
  className = "",
  ...rest
}: ButtonProps) {
  const idle = label ?? children;
  const busy = submitPhase !== "idle";
  const spring = popSpring;
  return (
    <button
      className={`${s.btn} ${s[variant]} ${s[size]}${block ? ` ${s.block}` : ""}${
        className ? ` ${className}` : ""
      }`}
      disabled={disabled || busy}
      {...rest}
    >
      <span className={s.phase}>
        <AnimatePresence mode="popLayout" initial={false}>
          {submitPhase === "idle" && (
            <motion.span
              key="idle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={quickSpring}
              style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}
            >
              {idle}
            </motion.span>
          )}
          {submitPhase === "loading" && (
            <motion.span
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={quickSpring}
            >
              <span className={s.spinner} />
            </motion.span>
          )}
          {submitPhase === "success" && (
            <motion.span
              key="success"
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={spring}
              style={{ display: "inline-flex" }}
            >
              <CheckIcon />
            </motion.span>
          )}
        </AnimatePresence>
      </span>
    </button>
  );
}

function CheckIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <motion.path
        d="M5 13l4 4L19 7"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
      />
    </svg>
  );
}