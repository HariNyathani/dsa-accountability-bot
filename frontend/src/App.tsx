import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import Layout from "./components/Layout";
import AdminRoute from "./components/AdminRoute";

const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const LeaderboardPage = lazy(() => import("./pages/LeaderboardPage"));
const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"));
const UserProfilePage = lazy(() => import("./pages/UserProfilePage"));
const MyDashboardPage = lazy(() => import("./pages/MyDashboardPage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));
const RevisionBankPage = lazy(() => import("./pages/RevisionBankPage"));

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Suspense fallback={<div>Loading…</div>}>
            <Routes>
              <Route element={<Layout />}>
                <Route index element={<DashboardPage />} />
                <Route path="leaderboard" element={<LeaderboardPage />} />
                <Route path="analytics" element={<AnalyticsPage />} />
                <Route path="users/:userId" element={<UserProfilePage />} />
                <Route path="u/:identifier" element={<UserProfilePage />} />

                <Route path="me" element={<MyDashboardPage />} />
                <Route path="revision" element={<RevisionBankPage />} />

                {/* Admin — guarded by AdminRoute (403 wall for non-admin) */}
                <Route element={<AdminRoute />}>
                  <Route path="admin" element={<AdminPage />} />
                </Route>
              </Route>
            </Routes>
          </Suspense>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
