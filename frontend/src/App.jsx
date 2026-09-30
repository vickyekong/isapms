import { Navigate, Route, Routes } from "react-router-dom";
import AppShell from "./components/AppShell";
import { useAuth } from "./context/AuthContext";
import AccessDeniedPage from "./pages/AccessDeniedPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import AttendancePage from "./pages/AttendancePage";
import CoursesPage from "./pages/CoursesPage";
import DashboardPage from "./pages/DashboardPage";
import EnrolmentsPage from "./pages/EnrolmentsPage";
import FacultiesPage from "./pages/FacultiesPage";
import LecturersPage from "./pages/LecturersPage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import PasswordResetPage from "./pages/PasswordResetPage";
import PredictionsPage from "./pages/PredictionsPage";
import AtRiskPage from "./pages/AtRiskPage";
import ProfilePage from "./pages/ProfilePage";
import ReportsPage from "./pages/ReportsPage";
import ResultsPage from "./pages/ResultsPage";
import SettingsPage from "./pages/SettingsPage";
import StudentsPage from "./pages/StudentsPage";
import UsersPage from "./pages/UsersPage";

function Protected({ children, roles }) {
  const { user, ready } = useAuth();
  if (!ready) return <p className="p-8 text-sm">Checking your session…</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/access-denied" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<PasswordResetPage mode="request" />} />
      <Route path="/reset-password" element={<PasswordResetPage mode="confirm" />} />
      <Route path="/access-denied" element={<AccessDeniedPage />} />
      <Route
        element={
          <Protected>
            <AppShell />
          </Protected>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="users" element={<Protected roles={["admin"]}><UsersPage /></Protected>} />
        <Route path="students" element={<Protected roles={["admin"]}><StudentsPage /></Protected>} />
        <Route path="lecturers" element={<Protected roles={["admin"]}><LecturersPage /></Protected>} />
        <Route path="faculties" element={<Protected roles={["admin"]}><FacultiesPage /></Protected>} />
        <Route path="courses" element={<CoursesPage />} />
        <Route path="enrolments" element={<Protected roles={["admin", "lecturer"]}><EnrolmentsPage /></Protected>} />
        <Route path="attendance" element={<AttendancePage />} />
        <Route path="results" element={<ResultsPage />} />
        <Route path="predictions" element={<PredictionsPage />} />
        <Route path="at-risk" element={<Protected roles={["admin", "lecturer"]}><AtRiskPage /></Protected>} />
        <Route path="analytics" element={<Protected roles={["admin"]}><AnalyticsPage /></Protected>} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="settings" element={<Protected roles={["admin"]}><SettingsPage /></Protected>} />
        <Route path="profile" element={<ProfilePage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
