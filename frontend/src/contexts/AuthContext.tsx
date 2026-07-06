/* ──────────────────────────────────────────────────────────────────────────
   Auth Context — manages Discord OAuth session state across the app.

   Bearer-only flow (Module 9 / backend security audit):
   • JWT is stored in localStorage under 'dsa_token' (never in a cookie).
   • On mount:
       1. If ?code= is present in the URL, redeem it via POST /auth/exchange
          to get the JWT, persist it, then clean the URL.
       2. Otherwise restore an existing session from localStorage by calling
          GET /auth/me with the stored token as Authorization: Bearer.
   • All API calls attach the token via the Authorization: Bearer header
     (handled centrally in api.ts / getAuthHeaders()).
   • login()  → redirects to /auth/login (Discord OAuth).
   • logout() → calls POST /auth/logout (revokes JTI on server), then
                clears localStorage and React state.
   ────────────────────────────────────────────────────────────────────────── */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";

const TOKEN_KEY = "dsa_token";
const BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

/** Read the stored JWT (or null if absent). */
export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

/** Build the Authorization: Bearer header object for fetch() calls. */
export function getAuthHeaders(): Record<string, string> {
  const token = getStoredToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface AuthUser {
  id: string;
  username: string;
  profile_handle: string | null;
  avatar: string | null;
  avatar_url: string | null;
  discriminator: string;
  is_admin: boolean;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  authenticated: boolean;
  isAdmin: boolean;
  login: () => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  authenticated: false,
  isAdmin: false,
  login: () => {},
  logout: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        // ── Step 1: Handle the post-OAuth redirect (?code=<opaque>) ──────
        const params = new URLSearchParams(window.location.search);
        const exchangeCode = params.get("code");

        if (exchangeCode) {
          // Redeem the opaque exchange code for the JWT.
          const res = await fetch(`${BASE}/auth/exchange`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code: exchangeCode }),
          });

          if (res.ok) {
            const { token } = await res.json();
            if (token) {
              localStorage.setItem(TOKEN_KEY, token);
            }
          }

          // Clean the URL regardless of exchange outcome — the code is
          // single-use and must never persist in browser history.
          const cleanUrl = window.location.pathname;
          window.history.replaceState({}, document.title, cleanUrl);
        }

        // ── Step 2: Restore session from localStorage ─────────────────────
        const storedToken = getStoredToken();
        if (!storedToken) {
          if (!cancelled) setLoading(false);
          return;
        }

        const meRes = await fetch(`${BASE}/auth/me`, {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${storedToken}`,
          },
        });

        if (meRes.ok) {
          const data = await meRes.json();
          if (!cancelled && data.authenticated && data.user) {
            setUser(data.user);
          }
        } else if (meRes.status === 401) {
          // Token expired or revoked — clear stale storage.
          localStorage.removeItem(TOKEN_KEY);
        }
      } catch {
        // Network error during bootstrap — degrade gracefully, stay logged out.
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    bootstrap();
    return () => { cancelled = true; };
  }, []);

  const login = useCallback(() => {
    // Redirect to backend auth route which starts the Discord OAuth dance.
    window.location.href = `${BASE}/auth/login`;
  }, []);

  const logout = useCallback(async () => {
    const token = getStoredToken();
    try {
      // Revoke the JTI on the server so the token is dead immediately.
      await fetch(`${BASE}/auth/logout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
    } catch {
      // Best-effort — clear local state regardless.
    }
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        authenticated: !!user,
        isAdmin: !!user?.is_admin,
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
