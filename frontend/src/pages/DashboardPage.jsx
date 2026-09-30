import { useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import { Alert, Badge, Disclaimer, EmptyState, PageHeader, Spinner, StatCard } from "../components/ui";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const RISK_COLORS = { low: "#1F8A5B", medium: "#C4A35A", high: "#9B2C2C" };
const PIE_COLORS = ["#0B3D2E", "#1F8A5B", "#C4A35A", "#8C6A3D", "#9B2C2C", "#315E7A"];

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/dashboard/").then((response) => setData(response.data)).catch((err) => setError(errorMessage(err)));
  }, []);

  if (error) return <Alert>{error}</Alert>;
  if (!data) return <Spinner label="Loading dashboard" />;
  if (data.role === "student") return <StudentDashboard data={data} />;
  if (data.role === "lecturer") return <LecturerDashboard data={data} />;
  return <AdminDashboard data={data} />;
}

function AdminDashboard({ data }) {
  const risk = [
    { name: "Low", value: data.risk_counts.low, fill: RISK_COLORS.low },
    { name: "Medium", value: data.risk_counts.medium, fill: RISK_COLORS.medium },
    { name: "High", value: data.risk_counts.high, fill: RISK_COLORS.high },
  ];
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Administrator" title="Institution dashboard" description="Student population, grade patterns, attendance, and decision-support risk signals." />
      <Disclaimer text={data.disclaimer} />
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Students" value={data.totals.students} />
        <StatCard label="Lecturers" value={data.totals.lecturers} />
        <StatCard label="Active courses" value={data.totals.courses} />
        <StatCard label="Faculties" value={data.totals.faculties} />
      </section>
      <section className="grid gap-4 xl:grid-cols-2">
        <ChartCard title="Students by faculty">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.students_by_faculty}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" hide />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" fill="#0B3D2E" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Grade distribution">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.grade_distribution}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" fill="#C4A35A" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Attendance trend">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={data.attendance_trends}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" hide />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Line dataKey="present" stroke="#1F8A5B" />
              <Line dataKey="absent" stroke="#9B2C2C" />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Risk levels">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={risk} dataKey="value" nameKey="name" outerRadius={90} label>
                {risk.map((entry) => (
                  <Cell key={entry.name} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </section>
      <section className="grid gap-4 xl:grid-cols-2">
        <SimpleList title="At-risk alerts" rows={data.at_risk_alerts} render={(row) => `${row.student.full_name} · ${row.reason}`} empty="No at-risk alerts yet." />
        <SimpleList title="Recent predictions" rows={data.recent_predictions} render={(row) => `${row.student} · ${row.course} · ${row.predicted_grade} (${row.risk_level})`} empty="No predictions have been run." />
      </section>
      <div className="panel p-5">
        <h2 className="font-serif text-2xl text-forest">Recent system activity</h2>
        {data.recent_activity.length ? (
          <ul className="mt-3 space-y-2 text-sm">
            {data.recent_activity.map((item) => (
              <li key={item.id} className="flex justify-between gap-4 border-b border-[#EFE8DC] py-2">
                <span>{item.description}</span>
                <span className="text-[#667068]">{item.actor}</span>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState title="No activity yet" body="Administrative actions will appear here." />
        )}
        {data.active_model ? (
          <p className="mt-4 text-sm text-[#526059]">
            Active model {data.active_model.version}: accuracy {(data.active_model.accuracy * 100).toFixed(1)}%, F1 {(data.active_model.f1_score * 100).toFixed(1)}%.
          </p>
        ) : null}
      </div>
    </div>
  );
}

function LecturerDashboard({ data }) {
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Lecturer" title="Teaching dashboard" description="Assigned courses, attendance, recorded results, and students who may need support." />
      <section className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Assigned courses" value={data.courses.length} />
        <StatCard label="Enrolled students" value={data.enrolled_students} />
        <StatCard label="High-risk signals" value={data.risk_counts.high} />
      </section>
      <div className="panel overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-[#F7F4EE] text-xs uppercase text-[#667068]">
            <tr>
              <th className="px-4 py-3">Course</th>
              <th className="px-4 py-3">Enrolled</th>
              <th className="px-4 py-3">Attendance</th>
              <th className="px-4 py-3">Results</th>
            </tr>
          </thead>
          <tbody>
            {data.courses.map((course) => (
              <tr key={course.id} className="border-t border-[#EFE8DC]">
                <td className="px-4 py-3">{course.code} · {course.title}</td>
                <td className="px-4 py-3">{course.enrolled}</td>
                <td className="px-4 py-3">{course.attendance_percentage ?? "—"}%</td>
                <td className="px-4 py-3">{course.results_recorded}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!data.courses.length ? <EmptyState title="No assigned courses" body="An administrator needs to assign courses to your profile." /> : null}
      </div>
      <SimpleList title="At-risk students" rows={data.at_risk_alerts} render={(row) => `${row.student.full_name} · ${row.reason}`} empty="No at-risk students in your courses." />
    </div>
  );
}

function StudentDashboard({ data }) {
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Student" title={`Welcome, ${data.profile.full_name}`} description={`${data.profile.matric_number} · ${data.profile.department}`} />
      <Disclaimer text={data.disclaimer} />
      <section className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Current CGPA" value={Number(data.current_cgpa).toFixed(2)} />
        <StatCard label="Prior CGPA" value={Number(data.prior_cgpa).toFixed(2)} />
        <StatCard label="Semester GPA" value={data.semester_gpa == null ? "—" : Number(data.semester_gpa).toFixed(2)} />
      </section>
      <ChartCard title="Score trend">
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={data.grade_trend}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" hide />
            <YAxis domain={[0, 100]} />
            <Tooltip />
            <Line dataKey="score" stroke="#0B3D2E" />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
      <div className="grid gap-4 lg:grid-cols-2">
        {data.courses.map((course) => (
          <article key={course.enrolment_id} className="panel p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="font-semibold">{course.code}</h2>
                <p className="text-sm text-[#526059]">{course.title}</p>
              </div>
              <Badge tone={course.below_threshold ? "high" : "low"}>{course.grade || "In progress"}</Badge>
            </div>
            <p className="mt-3 text-sm">Attendance: {course.attendance_percentage ?? "Not recorded"}{course.attendance_percentage != null ? "%" : ""}</p>
            <p className="text-sm">Score: {course.total_score ?? "Awaiting result"}</p>
          </article>
        ))}
      </div>
      <SimpleList title="Academic alerts" rows={data.alerts} render={(row) => row.title} empty="You have no academic alerts." />
    </div>
  );
}

function ChartCard({ title, children }) {
  return (
    <section className="panel p-4">
      <h2 className="mb-3 font-serif text-xl text-forest">{title}</h2>
      {children}
    </section>
  );
}

function SimpleList({ title, rows, render, empty }) {
  return (
    <section className="panel p-5">
      <h2 className="font-serif text-2xl text-forest">{title}</h2>
      {rows?.length ? (
        <ul className="mt-3 space-y-2 text-sm">
          {rows.map((row, index) => (
            <li key={row.id || index} className="border-b border-[#EFE8DC] py-2">{render(row)}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-[#667068]">{empty}</p>
      )}
    </section>
  );
}

export { PIE_COLORS };
