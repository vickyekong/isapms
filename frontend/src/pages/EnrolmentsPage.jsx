import { useState } from "react";
import { api, errorMessage } from "../api/client";
import { Alert, Button, DataTable, Field, PageHeader, Spinner, inputClass } from "../components/ui";
import { useOptions, usePaged } from "../hooks";

export default function EnrolmentsPage() {
  const list = usePaged("/enrolments/");
  const options = useOptions();
  const [student, setStudent] = useState("");
  const [course, setCourse] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [file, setFile] = useState(null);

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Registration" title="Course enrolment" description="Enrol a student once per course. CSV import uses matric_number, course_code, and optional session and semester columns." />
      {message ? <Alert kind="success">{message}</Alert> : null}
      {error || list.error ? <Alert>{error || list.error}</Alert> : null}
      <form className="panel grid gap-3 p-5 md:grid-cols-3" onSubmit={async (event) => {
        event.preventDefault();
        try {
          await api.post("/enrolments/", { student, course });
          setMessage("Student enrolled.");
          list.reload();
        } catch (err) {
          setError(errorMessage(err));
        }
      }}>
        <Field label="Student"><select className={inputClass} value={student} onChange={(event) => setStudent(event.target.value)} required><option value="">Select</option>{options.students.map((item) => <option key={item.id} value={item.id}>{item.matric_number} · {item.full_name}</option>)}</select></Field>
        <Field label="Course"><select className={inputClass} value={course} onChange={(event) => setCourse(event.target.value)} required><option value="">Select</option>{options.courses.map((item) => <option key={item.id} value={item.id}>{item.code} · {item.session_name}</option>)}</select></Field>
        <div className="self-end"><Button type="submit">Enrol</Button></div>
      </form>
      <form className="panel flex flex-col gap-3 p-5 md:flex-row md:items-end" onSubmit={async (event) => {
        event.preventDefault();
        const body = new FormData();
        body.append("file", file);
        try {
          const response = await api.post("/enrolments/import_csv/", body);
          setMessage(`Imported ${response.data.created} rows. ${response.data.errors.length} rows need attention.`);
          list.reload();
        } catch (err) {
          setError(errorMessage(err));
        }
      }}>
        <Field label="Import CSV"><input className={inputClass} type="file" accept=".csv" onChange={(event) => setFile(event.target.files?.[0] || null)} required /></Field>
        <Button type="submit">Upload enrolment file</Button>
      </form>
      <input className={inputClass} aria-label="Search enrolments" placeholder="Search matric number or course" value={list.search} onChange={(event) => { list.setSearch(event.target.value); list.setPage(1); }} />
      {list.loading ? <Spinner /> : (
        <DataTable
          columns={[
            { key: "matric_number", label: "Matric number" },
            { key: "student_name", label: "Student" },
            { key: "course_code", label: "Course" },
            { key: "session_name", label: "Session" },
            { key: "semester_name", label: "Semester" },
            { key: "status", label: "Status" },
          ]}
          rows={list.rows}
          page={list.page}
          pages={list.pages}
          onPage={list.setPage}
        />
      )}
    </div>
  );
}
