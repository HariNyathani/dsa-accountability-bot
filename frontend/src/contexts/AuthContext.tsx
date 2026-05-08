/* ──────────────────────────────────────────────────────────────────────────
   Auth Context — manages Discord OAuth session state across the app.

   • On mount, checks /auth/me to restore an existing session (cookie-based)
   • Provides login (redirect), logout, user data, and loading state
   • All components can useAuth() to conditionally render personalized content
   ────────────────────────────────────────────────────────────────────────── */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";

export interface AuthUser {
  id: string;
  username: string;
  avatar: string | null;
  avatar_url: string | null;
  discriminator: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  authenticated: boolean;
  login: () => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  authenticated: false,
  login: () => {},
  logout: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  // Check for existing session on mount
  useEffect(() => {
    let cancelled = false;

    async function checkSession() {
      try {
        const res = await fetch("/auth/me", { credentials: "include" });
        if (res.ok) {
          const data = await res.json();
          if (!cancelled && data.authenticated && data.user) {
            setUser(data.user);
          }
        }
      } catch {
        // Not authenticated or network error — that's fine
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    checkSession();
    return () => { cancelled = true; };
  }, []);

  const login = useCallback(() => {
    // Redirect to backend auth route which redirects to Discord
    window.location.href = "/auth/login";
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetch("/auth/logout", {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // Best-effort
    }
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        authenticated: !!user,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
