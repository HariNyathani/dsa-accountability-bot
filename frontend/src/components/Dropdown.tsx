import { AnimatePresence, motion } from "motion/react";
import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { enterSpring } from "../styles/springs";
import s from "./Dropdown.module.css";

export interface DropdownItem<T extends string | number> {
  key: T;
  label: ReactNode;
  icon?: ReactNode;
  danger?: boolean;
  disabled?: boolean;
  /** Render as a visual divider instead of a selectable item. */
  divider?: boolean;
}

export interface DropdownProps<T extends string | number> {
  items: DropdownItem<T>[];
  value?: T;
  placeholder?: ReactNode;
  onChange?: (v: T) => void;
  /** "trigger" = renders the trigger surface (select). "custom" = render your own
   *  children as the trigger (for the user avatar menu, chips, etc.). */
  trigger?: "trigger" | "custom";
  children?: ReactNode;
  /** Panel origin relative to trigger. */
  placement?: "up" | "down";
  ariaLabel?: string;
  className?: string;
  panelClassName?: string;
}

/**
 * Glass popover dropdown — replaces native `<select>` and the user menu.
 * Mirrors the mobile autocomplete options panel spec
 * (log_progress_sheet.dart:837-869): glass gradient + 1px specular border + blur(16)
 * + rounded-16 + soft ambient shadow, plus a heavier drop shadow for elevation.
 */
export default function Dropdown<T extends string | number>({
  items,
  value,
  placeholder = "Select…",
  onChange,
  trigger = "trigger",
  children,
  placement = "down",
  ariaLabel,
  className = "",
  panelClassName = "",
}: DropdownProps<T>) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const id = useId();
  const active = items.find((i) => i.key === value);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onEsc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onEsc);
    };
  }, [open]);

  const select = useCallback(
    (k: T) => {
      onChange?.(k);
      setOpen(false);
    },
    [onChange]
  );

  return (
    <div className={`${s.field}${className ? ` ${className}` : ""}`} ref={ref}>
      {trigger === "trigger" ? (
        <button
          type="button"
          className={s.trigger}
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-label={ariaLabel}
          data-open={open}
          onClick={() => setOpen((o) => !o)}
        >
          <span className={active ? "" : s.placeholder}>
            {active ? (
              <>
                {active.icon && <span>{active.icon}</span>}
                {active.label}
              </>
            ) : (
              placeholder
            )}
          </span>
          <Chevron open={open} />
        </button>
      ) : (
        <div
          role="button"
          aria-haspopup="menu"
          aria-expanded={open}
          data-open={open}
          onClick={() => setOpen((o) => !o)}
          style={{ display: "contents" }}
        >
          {children}
        </div>
      )}

      <AnimatePresence>
        {open && (
          <motion.div
            key={`panel-${id}`}
            className={`${s.panel} ${placement === "up" ? s.up : s.down}${
              panelClassName ? ` ${panelClassName}` : ""
            }`}
            role="listbox"
            initial={{ opacity: 0, y: placement === "up" ? 8 : -8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.97 }}
            transition={enterSpring}
          >
            {items.map((it) =>
              it.divider ? (
                <div key={String(it.key)} className={s.divider} />
              ) : (
                <button
                  key={String(it.key)}
                  type="button"
                  role="option"
                  aria-selected={it.key === value}
                  data-active={it.key === value}
                  className={`${s.item}${it.danger ? ` ${s.danger}` : ""}`}
                  disabled={it.disabled}
                  onClick={() => select(it.key)}
                >
                  {it.icon && <span className={s.iIcon}>{it.icon}</span>}
                  {it.label}
                </button>
              )
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      className={`${s.chev}${open ? ` ${s.chevOpen}` : ""}`}
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
    >
      <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}