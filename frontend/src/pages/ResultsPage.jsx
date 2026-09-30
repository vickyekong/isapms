import { useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import { Alert, Button, DataTable, PageHeader, Spinner, inputClass } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useOptions, usePaged } from "../hooks";

export default function ResultsPage() {
  const { user } = useAuth();
  const options = useOptions();
  const list = usePaged("/results/");
  const [course, setCourse] = useState("");
  const [rows, setRows] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const canScore = user?.role === "admin" || user?.role === "lecturer";

  useEffect(() => {
    if (!course || !canScore) return;
    api.get("/enrolments/", { params: { course, page_size: 100 } }).then((response) => {
      setRows((response.data.results || []).map((item) => ({ enrolment: item.id, name: `${item.matric_number} · ${item.student_name}`, ca_score: "", exam_score: "" })));
    }).catch((err) => setError(errorMessage(err)));
  }, [course, canScore]);

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Assessment" title="Results" description="Continuous assessment and examination scores are totalled automatically. Grades follow the administrator's grading scale." />
      {message ? <Alert kind="success">{message}</Alert> : null}
      {error || list.error ? <Alert>{error || list.error}</Alert> : null}
      {canScore ? (
        <form className="panel space-y-3 p-5" onSubmit={async (event) => {
          event.preventDefault();
          try {
            await api.post("/assessments/upload/", {
              course,
              scores: rows.filter((row) => row.ca_score !== "").map((row) => ({ enrolment: row.enrolment, ca_score: row.ca_score, exam_score: row.exam_score === "" ? null : row.exam_score })),
            });
            setMessage("Scores saved and grades recalculated.");
            list.reload();
          } catch (err) {
            setError(errorMessage(err));
          }
        }}>
          <select className={inputClass} aria-label="Course for scores" value={course} onChange={(event) => setCourse(event.target.value)}>
            <option value="">Select a course</option>
            {options.courses.map((item) => <option key={item.id} value={item.id}>{item.code}</option>)}
          </select>
          {rows.map((row, index) => (
            <div key={row.enrolment} className="grid gap-2 md:grid-cols-[1.5fr_1fr_1fr]">
              <p className="self-center text-sm">{row.name}</p>
              <input className={inputClass} aria-label={`CA for ${row.name}`} placeholder="CA" value={row.ca_score} onChange={(event) => setRows((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, ca_score: event.target.value } : item))} />
              <input className={inputClass} aria-label={`Exam for ${row.name}`} placeholder="Exam" value={row.exam_score} onChange={(event) => setRows((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, exam_score: event.target.value } : item))} />
            </div>
          ))}
          {course ? <Button type="submit">Save scores</Button> : null}
        </form>
      ) : null}
      {list.loading ? <Spinner /> : (
        <DataTable
          columns={[
            { key: "matric_number", label: "Matric number" },
            { key: "student_name", label: "Student" },
            { key: "course_code", label: "Course" },
            { key: "ca_score", label: "CA" },
            { key: "exam_score", label: "Exam" },
            { key: "total_score", label: "Total" },
            { key: "grade", label: "Grade" },
            { key: "grade_point", label: "Point" },
          ]}
          rows={list.rows}
          page={list.page}
          pages={list.pages}
          onPage={list.setPage}
          empty={<p className="p-6 text-sm">No validated results yet.</p>}
        />
      )}
    </div>
  );
}
