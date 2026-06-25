import type { InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes, ReactNode } from "react";
import s from "./Field.module.css";

interface BaseProps {
  label?: string;
  hint?: ReactNode;
}

export function TextInput({
  label,
  hint,
  className = "",
  ...rest
}: BaseProps & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className={s.field}>
      {label && <span className={s.label}>{label}</span>}
      <input className={`${s.input}${className ? ` ${className}` : ""}`} {...rest} />
      {hint && <span className={s.hint}>{hint}</span>}
    </label>
  );
}

export function Select({
  label,
  hint,
  className = "",
  children,
  ...rest
}: BaseProps & SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <label className={s.field}>
      {label && <span className={s.label}>{label}</span>}
      <select className={`${s.select}${className ? ` ${className}` : ""}`} {...rest}>
        {children}
      </select>
      {hint && <span className={s.hint}>{hint}</span>}
    </label>
  );
}

export function TextArea({
  label,
  hint,
  className = "",
  ...rest
}: BaseProps & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <label className={s.field}>
      {label && <span className={s.label}>{label}</span>}
      <textarea className={`${s.area}${className ? ` ${className}` : ""}`} {...rest} />
      {hint && <span className={s.hint}>{hint}</span>}
    </label>
  );
}