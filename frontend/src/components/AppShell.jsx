import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const LINKS = {
  admin: [
    ["/", "Dashboard"],
    ["/users", "Users"],
    ["/students", "Students"],
    ["/lecturers", "Lecturers"],
    ["/faculties", "Faculties"],
    ["/courses", "Courses"],
    ["/enrolments", "Enrolments"],
    ["/attendance", "Attendance"],
    ["/results", "Results"],
    ["/predictions", "Predictions"],
    ["/at-risk", "At-risk students"],
    ["/analytics", "Analytics"],
    ["/reports", "Reports"],
    ["/settings", "Settings"],
    ["/profile", "Profile"],
  ],
  lecturer: [
    ["/", "Dashboard"],
    ["/courses", "My courses"],
    ["/enrolments", "Enrolments"],
    ["/attendance", "Attendance"],
    ["/results", "Results"],
    ["/predictions", "Predictions"],
    ["/at-risk", "At-risk students"],
    ["/reports", "Reports"],
    ["/profile", "Profile"],
  ],
  student: [
    ["/", "Dashboard"],
    ["/courses", "My courses"],
    ["/attendance", "Attendance"],
    ["/results", "Results"],
    ["/predictions", "Predictions"],
    ["/reports", "My reports"],
    ["/profile", "Profile"],
  ],
};

export default function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const links = LINKS[user?.role] || [];

  return (
    <div className="min-h-screen bg-paper text-ink md:grid md:grid-cols-[260px_1fr]">
      <aside className={`${open ? "block" : "hidden"} border-b border-white/10 bg-forest text-white md:block`}>
        <div className="px-5 py-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gold font-serif text-lg text-forest">NSU</div>
          <p className="mt-4 font-serif text-2xl leading-tight">Nexus State University</p>
          <p className="mt-2 text-xs uppercase tracking-[0.16em] text-[#D7E6DF]">Academic monitoring</p>
        </div>
        <nav className="space-y-1 px-3 pb-6" aria-label="Primary">
          {links.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `block rounded-lg px-3 py-2 text-sm ${isActive ? "bg-white/15 text-white" : "text-[#D7E6DF] hover:bg-white/10"}`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div>
        <header className="flex items-center justify-between gap-3 border-b border-[#E4DDD0] bg-white px-4 py-3 md:px-8">
          <button className="rounded-lg border border-[#D5CBB8] px-3 py-2 text-sm md:hidden" type="button" onClick={() => setOpen((value) => !value)}>
            Menu
          </button>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">{user?.full_name || user?.email}</p>
            <p className="text-xs capitalize text-[#667068]">{user?.role}</p>
          </div>
          <button
            className="rounded-lg px-3 py-2 text-sm font-semibold text-forest"
            type="button"
            onClick={async () => {
              await logout();
              navigate("/login");
            }}
          >
            Sign out
          </button>
        </header>
        <main className="px-4 py-6 md:px-8">
          {user?.is_sample ? (
            <p className="mb-4 rounded-xl border border-[#E4D7B4] bg-[#FBF6EA] px-4 py-3 text-sm text-[#6D5420]">
              You are signed in with sample institutional data. These records are for demonstration and testing.
            </p>
          ) : null}
          <Outlet />
        </main>
      </div>
    </div>
  );
}
