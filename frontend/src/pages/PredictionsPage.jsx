import { useState } from "react";
import { api, errorMessage } from "../api/client";
import { Alert, Badge, Button, DataTable, Disclaimer, Field, PageHeader, Spinner, inputClass } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useOptions, usePaged } from "../hooks";

export default function PredictionsPage() {
  const { user } = useAuth();
  const options = useOptions();
  const list = usePaged("/predictions/");
  const [student, setStudent] = useState("");
  const [course, setCourse] = useState("");
  const [latest, setLatest] = useState(null);
  const [error, setError] = useState("");
  const canRun = user?.role === "admin" || user?.role === "lecturer";

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Decision support" title="Grade predictions" description="A decision tree estimates a grade, confidence, and risk level from attendance, assessment, course load, and previous performance." />
      <Disclaimer />
      {error || list.error ? <Alert>{error || list.error}</Alert> : null}
      {canRun ? (
        <form className="panel grid gap-3 p-5 md:grid-cols-3" onSubmit={async (event) => {
          event.preventDefault();
          setError("");
          try {
            const response = await api.post("/predictions/", { student, course });
            setLatest(response.data);
            list.reload();
          } catch (err) {
            setError(errorMessage(err));
          }
        }}>
          <Field label="Student"><select className={inputClass} value={student} onChange={(event) => setStudent(event.target.value)} required><option value="">Select</option>{options.students.map((item) => <option key={item.id} value={item.id}>{item.matric_number} · {item.full_name}</option>)}</select></Field>
          <Field label="Course"><select className={inputClass} value={course} onChange={(event) => setCourse(event.target.value)} required><option value="">Select</option>{options.courses.map((item) => <option key={item.id} value={item.id}>{item.code}</option>)}</select></Field>
          <div className="self-end"><Button type="submit">Run prediction</Button></div>
        </form>
      ) : null}
      {latest ? (
        <section className="panel grid gap-3 p-5 sm:grid-cols-4">
          <Metric label="Predicted grade" value={latest.predicted_grade} />
          <Metric label="Confidence" value={`${Math.round(latest.confidence * 100)}%`} />
          <Metric label="Risk" value={<Badge tone={latest.risk_level}>{latest.risk_level}</Badge>} />
          <Metric label="Data" value={latest.data_status} />
          <p className="sm:col-span-4 text-sm text-[#526059]">{latest.disclaimer}</p>
        </section>
      ) : null}
      {list.loading ? <Spinner /> : (
        <DataTable
          columns={[
            { key: "matric_number", label: "Matric number" },
            { key: "student_name", label: "Student" },
            { key: "course_code", label: "Course" },
            { key: "predicted_grade", label: "Grade" },
            { key: "confidence", label: "Confidence", render: (row) => `${Math.round(row.confidence * 100)}%` },
            { key: "risk_level", label: "Risk", render: (row) => <Badge tone={row.risk_level}>{row.risk_level}</Badge> },
          ]}
          rows={list.rows}
          page={list.page}
          pages={list.pages}
          onPage={list.setPage}
          empty={<p className="p-6 text-sm">No predictions have been stored.</p>}
        />
      )}
    </div>
  );
}

function Metric({ label, value }) {
  return <div><p className="text-xs uppercase tracking-wide text-[#667068]">{label}</p><p className="mt-1 font-serif text-2xl text-forest">{value}</p></div>;
}
