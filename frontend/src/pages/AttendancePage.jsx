import { useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import { Alert, Badge, Button, PageHeader, Spinner, inputClass } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useOptions } from "../hooks";

export default function AttendancePage() {
  const { user } = useAuth();
  const options = useOptions();
  const [course, setCourse] = useState("");
  const [date, setDate] = useState("");
  const [rows, setRows] = useState([]);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const canMark = user?.role === "admin" || user?.role === "lecturer";

  useEffect(() => {
    if (!course) return;
    setLoading(true);
    Promise.all([
      api.get("/attendance/summary/", { params: { course } }),
      api.get("/attendance/", { params: { course, page_size: 20 } }),
    ]).then(([summary, past]) => {
      setRows(summary.data.map((row) => ({ ...row, status: "present" })));
      setHistory(past.data.results || []);
    }).catch((err) => setError(errorMessage(err))).finally(() => setLoading(false));
  }, [course]);

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Monitoring" title="Attendance" description="Mark students present, absent, or excused. Percentages exclude excused sessions, and students below the configured threshold are flagged." />
      {message ? <Alert kind="success">{message}</Alert> : null}
      {error ? <Alert>{error}</Alert> : null}
      <div className="grid gap-3 md:grid-cols-2">
        <select className={inputClass} aria-label="Course" value={course} onChange={(event) => setCourse(event.target.value)}>
          <option value="">Select a course</option>
          {options.courses.map((item) => <option key={item.id} value={item.id}>{item.code} · {item.title}</option>)}
        </select>
        {canMark ? <input className={inputClass} aria-label="Attendance date" type="date" value={date} onChange={(event) => setDate(event.target.value)} /> : null}
      </div>
      {loading ? <Spinner /> : null}
      {rows.length ? (
        <form className="panel overflow-x-auto" onSubmit={async (event) => {
          event.preventDefault();
          try {
            await api.post("/attendance/mark/", { course, date, records: rows.map((row) => ({ enrolment: row.enrolment, status: row.status })) });
            setMessage("Attendance saved.");
          } catch (err) {
            setError(errorMessage(err));
          }
        }}>
          <table className="min-w-full text-left text-sm">
            <thead className="bg-[#F7F4EE] text-xs uppercase text-[#667068]"><tr><th className="px-4 py-3">Student</th><th className="px-4 py-3">Percentage</th><th className="px-4 py-3">Flag</th>{canMark ? <th className="px-4 py-3">Today</th> : null}</tr></thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={row.enrolment} className="border-t border-[#EFE8DC]">
                  <td className="px-4 py-3">{row.matric_number} · {row.student_name}</td>
                  <td className="px-4 py-3">{row.percentage ?? "—"}{row.percentage != null ? "%" : ""}</td>
                  <td className="px-4 py-3">{row.below_threshold ? <Badge tone="high">Below threshold</Badge> : <Badge tone="low">OK</Badge>}</td>
                  {canMark ? <td className="px-4 py-3"><select className={inputClass} aria-label={`Status for ${row.student_name}`} value={row.status} onChange={(event) => setRows((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, status: event.target.value } : item))}><option value="present">Present</option><option value="absent">Absent</option><option value="excused">Excused</option></select></td> : null}
                </tr>
              ))}
            </tbody>
          </table>
          {canMark ? <div className="p-4"><Button type="submit" disabled={!date}>Save attendance</Button></div> : null}
        </form>
      ) : null}
      <section className="panel p-5">
        <h2 className="font-serif text-2xl text-forest">Recent history</h2>
        <ul className="mt-3 text-sm">{history.map((item) => <li key={item.id} className="border-b border-[#EFE8DC] py-2">{item.date} · {item.matric_number} · {item.status}</li>)}</ul>
        {!history.length ? <p className="mt-2 text-sm text-[#667068]">No attendance has been recorded for this course.</p> : null}
      </section>
    </div>
  );
}
