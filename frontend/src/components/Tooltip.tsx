import { AnimatePresence, motion } from "motion/react";
import { useState, type ReactNode } from "react";
import { quickSpring } from "../styles/springs";
import s from "./Tooltip.module.css";

export default function Tooltip({
  content,
  children,
  placement = "up",
}: {
  content: ReactNode;
  children: ReactNode;
  placement?: "up" | "down";
}) {
  const [show, setShow] = useState(false);
  return (
    <span
      className={s.wrap}
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
      onFocus={() => setShow(true)}
      onBlur={() => setShow(false)}
    >
      {children}
      <AnimatePresence>
        {show && content && (
          <motion.span
            className={`${s.tip}${placement === "down" ? ` ${s.tipDown}` : ""}`}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={quickSpring}
            role="tooltip"
          >
            {content}
          </motion.span>
        )}
      </AnimatePresence>
    </span>
  );
}