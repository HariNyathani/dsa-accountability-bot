import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import Layout from "./components/Layout";
import AdminRoute from "./components/AdminRoute";
import DashboardPage from "./pages/DashboardPage";
import LeaderboardPage from "./pages/LeaderboardPage";
import AnalyticsPage from "./pages/AnalyticsPage";

import UserProfilePage from "./pages/UserProfilePage";
import MyDashboardPage from "./pages/MyDashboardPage";
import AdminPage from "./pages/AdminPage";
import RevisionBankPage from "./pages/RevisionBankPage";

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
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
      </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
