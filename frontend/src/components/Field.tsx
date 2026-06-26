import { useId, type InputHTMLAttributes, type SelectHTMLAttributes, type TextareaHTMLAttributes, type ReactNode } from "react";
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
  const id = useId();
  return (
    <label className={s.field} htmlFor={id}>
      {label && <span className={s.label}>{label}</span>}
      <input id={id} className={`${s.input}${className ? ` ${className}` : ""}`} {...rest} />
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
  const id = useId();
  return (
    <label className={s.field} htmlFor={id}>
      {label && <span className={s.label}>{label}</span>}
      <select id={id} className={`${s.select}${className ? ` ${className}` : ""}`} {...rest}>
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
  const id = useId();
  return (
    <label className={s.field} htmlFor={id}>
      {label && <span className={s.label}>{label}</span>}
      <textarea id={id} className={`${s.area}${className ? ` ${className}` : ""}`} {...rest} />
      {hint && <span className={s.hint}>{hint}</span>}
    </label>
  );
}