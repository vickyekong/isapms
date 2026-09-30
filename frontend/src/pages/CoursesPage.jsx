import { useState } from "react";
import { api, errorMessage } from "../api/client";
import { Alert, Button, DataTable, Field, PageHeader, Spinner, inputClass } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useOptions, usePaged } from "../hooks";

const empty = { code: "", title: "", credit_units: 3, faculty: "", department: "", level: 100, academic_session: "", semester: "", status: "active" };

export default function CoursesPage() {
  const { user } = useAuth();
  const list = usePaged("/courses/");
  const options = useOptions();
  const [form, setForm] = useState(empty);
  const [lecturer, setLecturer] = useState("");
  const [courseId, setCourseId] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const canManage = user?.role === "admin";

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Curriculum" title={canManage ? "Courses" : "My courses"} description="Course codes cannot be repeated within the same session and semester." />
      {message ? <Alert kind="success">{message}</Alert> : null}
      {error || list.error ? <Alert>{error || list.error}</Alert> : null}
      {canManage ? (
        <form className="panel grid gap-4 p-5 md:grid-cols-3" onSubmit={async (event) => {
          event.preventDefault();
          try {
            await api.post("/courses/", form);
            setMessage("Course created.");
            setForm(empty);
            list.reload();
          } catch (err) {
            setError(errorMessage(err));
          }
        }}>
          <Field label="Code"><input className={inputClass} value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value })} required /></Field>
          <Field label="Title"><input className={inputClass} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} required /></Field>
          <Field label="Credit units"><input className={inputClass} type="number" min="1" max="6" value={form.credit_units} onChange={(event) => setForm({ ...form, credit_units: Number(event.target.value) })} required /></Field>
          <Field label="Faculty"><select className={inputClass} value={form.faculty} onChange={(event) => setForm({ ...form, faculty: event.target.value })} required><option value="">Select</option>{options.faculties.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
          <Field label="Department"><select className={inputClass} value={form.department} onChange={(event) => setForm({ ...form, department: event.target.value })} required><option value="">Select</option>{options.departments.filter((item) => String(item.faculty) === String(form.faculty)).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
          <Field label="Level"><select className={inputClass} value={form.level} onChange={(event) => setForm({ ...form, level: Number(event.target.value) })}>{[100, 200, 300, 400, 500].map((level) => <option key={level}>{level}</option>)}</select></Field>
          <Field label="Session"><select className={inputClass} value={form.academic_session} onChange={(event) => setForm({ ...form, academic_session: event.target.value })} required><option value="">Select</option>{options.sessions.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
          <Field label="Semester"><select className={inputClass} value={form.semester} onChange={(event) => setForm({ ...form, semester: event.target.value })} required><option value="">Select</option>{options.semesters.filter((item) => !form.academic_session || String(item.session) === String(form.academic_session)).map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></Field>
          <div className="md:col-span-3"><Button type="submit">Create course</Button></div>
        </form>
      ) : null}
      {canManage ? (
        <form className="panel flex flex-col gap-3 p-5 md:flex-row" onSubmit={async (event) => {
          event.preventDefault();
          try {
            await api.post(`/courses/${courseId}/assign/`, { lecturer, is_primary: true });
            setMessage("Lecturer assigned.");
            list.reload();
          } catch (err) {
            setError(errorMessage(err));
          }
        }}>
          <select className={inputClass} aria-label="Course" value={courseId} onChange={(event) => setCourseId(event.target.value)} required>
            <option value="">Course</option>
            {options.courses.map((course) => <option key={course.id} value={course.id}>{course.code}</option>)}
          </select>
          <select className={inputClass} aria-label="Lecturer" value={lecturer} onChange={(event) => setLecturer(event.target.value)} required>
            <option value="">Lecturer</option>
            {options.lecturers.map((item) => <option key={item.id} value={item.id}>{item.full_name}</option>)}
          </select>
          <Button type="submit">Assign lecturer</Button>
        </form>
      ) : null}
      {list.loading ? <Spinner /> : (
        <DataTable
          columns={[
            { key: "code", label: "Code" },
            { key: "title", label: "Title" },
            { key: "credit_units", label: "Units" },
            { key: "level", label: "Level" },
            { key: "session_name", label: "Session" },
            { key: "semester_name", label: "Semester" },
            { key: "lecturers", label: "Lecturers", render: (row) => row.lecturers?.map((item) => item.name).join(", ") || "Unassigned" },
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
