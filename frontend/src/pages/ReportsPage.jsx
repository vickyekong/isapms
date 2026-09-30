import { useState } from "react";
import { api, errorMessage } from "../api/client";
import { Alert, Button, Disclaimer, Field, PageHeader, inputClass } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useOptions } from "../hooks";

const TYPES = [
  ["student_performance", "Student academic performance"],
  ["course_performance", "Course performance"],
  ["attendance", "Attendance"],
  ["results", "Results"],
  ["at_risk", "At-risk students"],
  ["predictions", "Predictive analytics"],
  ["faculty_department", "Faculty and department performance"],
];

export default function ReportsPage() {
  const { user } = useAuth();
  const options = useOptions();
  const allowed = user?.role === "student" ? TYPES.filter(([value]) => ["student_performance", "attendance", "results"].includes(value)) : TYPES;
  const [filters, setFilters] = useState({ type: allowed[0][0], format: "pdf", session: "", semester: "", faculty: "", department: "", level: "", course: "", student: "", risk_level: "" });
  const [error, setError] = useState("");

  function update(event) {
    setFilters((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Exports" title="Reports" description="Filter institutional reports and download them as PDF, Excel, or CSV." />
      {["predictions", "at_risk"].includes(filters.type) ? <Disclaimer /> : null}
      {error ? <Alert>{error}</Alert> : null}
      <form className="panel grid gap-4 p-5 md:grid-cols-3" onSubmit={async (event) => {
        event.preventDefault();
        setError("");
        try {
          const params = Object.fromEntries(Object.entries(filters).filter(([, value]) => value));
          const response = await api.get("/reports/", { params, responseType: "blob" });
          const blob = new Blob([response.data]);
          const url = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = url;
          link.download = `${filters.type}.${filters.format === "excel" ? "xlsx" : filters.format}`;
          link.click();
          URL.revokeObjectURL(url);
        } catch (err) {
          setError(errorMessage(err));
        }
      }}>
        <Field label="Report"><select className={inputClass} name="type" value={filters.type} onChange={update}>{allowed.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field>
        <Field label="Format"><select className={inputClass} name="format" value={filters.format} onChange={update}><option value="pdf">PDF</option><option value="xlsx">Excel</option><option value="csv">CSV</option></select></Field>
        <Field label="Session"><select className={inputClass} name="session" value={filters.session} onChange={update}><option value="">All</option>{options.sessions.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
        <Field label="Semester"><select className={inputClass} name="semester" value={filters.semester} onChange={update}><option value="">All</option>{options.semesters.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></Field>
        <Field label="Faculty"><select className={inputClass} name="faculty" value={filters.faculty} onChange={update}><option value="">All</option>{options.faculties.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
        <Field label="Department"><select className={inputClass} name="department" value={filters.department} onChange={update}><option value="">All</option>{options.departments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
        <Field label="Level"><select className={inputClass} name="level" value={filters.level} onChange={update}><option value="">All</option>{[100, 200, 300, 400, 500].map((level) => <option key={level}>{level}</option>)}</select></Field>
        <Field label="Course"><select className={inputClass} name="course" value={filters.course} onChange={update}><option value="">All</option>{options.courses.map((item) => <option key={item.id} value={item.id}>{item.code}</option>)}</select></Field>
        {user?.role !== "student" ? <Field label="Student"><select className={inputClass} name="student" value={filters.student} onChange={update}><option value="">All</option>{options.students.map((item) => <option key={item.id} value={item.id}>{item.full_name}</option>)}</select></Field> : null}
        <Field label="Risk level"><select className={inputClass} name="risk_level" value={filters.risk_level} onChange={update}><option value="">All</option><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></Field>
        <div className="md:col-span-3"><Button type="submit">Download report</Button></div>
      </form>
    </div>
  );
}
