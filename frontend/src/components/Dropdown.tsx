import { AnimatePresence, motion } from "motion/react";
import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
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
 *
 * Keyboard model (ARIA listbox pattern):
 *  - Enter / Space: toggle open
 *  - ArrowDown / ArrowUp: move activeIndex through selectable items
 *  - Home / End: jump to first / last
 *  - Enter on open: select the active option
 *  - Escape: close
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
  const [activeIndex, setActiveIndex] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const id = useId();

  // Selectable items only (skip dividers) for keyboard navigation.
  const selectableItems = items.filter((it) => !it.divider && !it.disabled);
  const activeKey = selectableItems[activeIndex]?.key;

  const active = items.find((i) => i.key === value);

  const openDropdown = useCallback(() => {
    setActiveIndex(0);
    setOpen(true);
  }, []);

  const closeDropdown = useCallback(() => {
    setOpen(false);
  }, []);

  const toggle = useCallback(() => {
    setOpen((o) => {
      if (!o) setActiveIndex(0);
      return !o;
    });
  }, []);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: globalThis.KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const select = useCallback(
    (k: T) => {
      onChange?.(k);
      setOpen(false);
    },
    [onChange]
  );

  const handleListKeyDown = (e: KeyboardEvent<HTMLElement>) => {
    if (!open) {
      if (e.key === "Enter" || e.key === " " || e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        openDropdown();
        return;
      }
      return;
    }
    switch (e.key) {
      case "ArrowDown": {
        e.preventDefault();
        setActiveIndex((i) => (i + 1) % Math.max(selectableItems.length, 1));
        break;
      }
      case "ArrowUp": {
        e.preventDefault();
        setActiveIndex((i) => (i - 1 + Math.max(selectableItems.length, 1)) % Math.max(selectableItems.length, 1));
        break;
      }
      case "Home": {
        e.preventDefault();
        setActiveIndex(0);
        break;
      }
      case "End": {
        e.preventDefault();
        setActiveIndex(Math.max(selectableItems.length - 1, 0));
        break;
      }
      case "Enter":
      case " ": {
        e.preventDefault();
        if (activeKey !== undefined) select(activeKey as T);
        break;
      }
      case "Escape": {
        e.preventDefault();
        closeDropdown();
        break;
      }
      default:
        break;
    }
  };

  const activedescendantId = open && activeKey !== undefined
    ? `${id}-opt-${String(activeKey)}`
    : undefined;

  return (
    <div className={`${s.field}${className ? ` ${className}` : ""}`} ref={ref}>
      {trigger === "trigger" ? (
        <button
          type="button"
          className={s.trigger}
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-label={ariaLabel}
          aria-activedescendant={activedescendantId}
          data-open={open}
          onClick={toggle}
          onKeyDown={handleListKeyDown}
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
          tabIndex={0}
          aria-haspopup="menu"
          aria-expanded={open}
          aria-label={ariaLabel}
          aria-activedescendant={activedescendantId}
          data-open={open}
          onClick={toggle}
          onKeyDown={handleListKeyDown}
          style={{ display: "block", width: "100%" }}
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
            {items.map((it) => {
              if (it.divider) {
                return <div key={`divider-${String(it.key)}`} className={s.divider} />;
              }
              const isActive = open && it.key === activeKey;
              const isSelected = it.key === value;
              return (
                <button
                  key={String(it.key)}
                  type="button"
                  id={`${id}-opt-${String(it.key)}`}
                  role="option"
                  aria-selected={isSelected}
                  data-active={isActive ? "true" : "false"}
                  data-selected={isSelected ? "true" : "false"}
                  className={`${s.item}${it.danger ? ` ${s.danger}` : ""}`}
                  disabled={it.disabled}
                  onClick={() => select(it.key)}
                  onMouseEnter={() => {
                    const idx = selectableItems.findIndex((s) => s.key === it.key);
                    if (idx >= 0) setActiveIndex(idx);
                  }}
                >
                  {it.icon && <span className={s.iIcon}>{it.icon}</span>}
                  {it.label}
                </button>
              );
            })}
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
