import LiquidCapsule, { type CapsuleItem } from "./LiquidCapsule";
import { useTheme, type ThemeMode } from "../contexts/ThemeContext";
import s from "./ThemeSwitcher.module.css";

/**
 * Premium theme selector — 3-segment sliding capsule.
 * Mirrors mobile/lib/features/profile/presentation/screens/tabs/profile_tab.dart:411-493
 * (segment order: Light / Dark / System).
 */
const items: CapsuleItem<ThemeMode>[] = [
  { key: "light", label: "Light", icon: <Sun /> },
  { key: "dark", label: "Dark", icon: <Moon /> },
  { key: "system", label: "System", icon: <Auto /> },
];

export default function ThemeSwitcher({ compact = false }: { compact?: boolean }) {
  const { mode, setMode } = useTheme();
  return (
    <div className={s.switcher} data-compact={compact || undefined}>
      <LiquidCapsule
        items={items}
        value={mode}
        onChange={setMode}
        variant="compact"
        aria-label="Theme"
      />
    </div>
  );
}

function Sun() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="2" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
function Moon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}
function Auto() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" />
      <path d="M12 3v18" stroke="currentColor" strokeWidth="2" />
      <path d="M12 3a9 9 0 010 18z" fill="currentColor" />
    </svg>
  );
}