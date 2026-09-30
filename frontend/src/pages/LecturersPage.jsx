import { useState } from "react";
import { api, errorMessage } from "../api/client";
import { Alert, Button, DataTable, Field, PageHeader, Spinner, inputClass } from "../components/ui";
import { useOptions, usePaged } from "../hooks";

const empty = { staff_id: "", first_name: "", surname: "", email: "", telephone: "", faculty: "", department: "", employment_status: "active", password: "" };

export default function LecturersPage() {
  const list = usePaged("/lecturers/");
  const options = useOptions();
  const [form, setForm] = useState(empty);
  const [courses, setCourses] = useState([]);
  const [selected, setSelected] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function onSubmit(event) {
    event.preventDefault();
    setError("");
    try {
      const payload = { ...form };
      if (!payload.password) delete payload.password;
      const response = await api.post("/lecturers/", payload);
      setMessage(response.data.temporary_password ? `Lecturer created. Temporary password: ${response.data.temporary_password}` : "Lecturer created.");
      setForm(empty);
      list.reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Staff" title="Lecturers" description="Register lecturers and assign one or more courses." />
      {message ? <Alert kind="success">{message}</Alert> : null}
      {error || list.error ? <Alert>{error || list.error}</Alert> : null}
      <form className="panel grid gap-4 p-5 md:grid-cols-3" onSubmit={onSubmit}>
        {["staff_id", "first_name", "surname", "email", "telephone"].map((name) => (
          <Field key={name} label={name.replace("_", " ")}>
            <input className={inputClass} name={name} type={name === "email" ? "email" : "text"} value={form[name]} onChange={(event) => setForm({ ...form, [name]: event.target.value })} required={name !== "telephone"} />
          </Field>
        ))}
        <Field label="Faculty">
          <select className={inputClass} value={form.faculty} onChange={(event) => setForm({ ...form, faculty: event.target.value, department: "" })} required>
            <option value="">Select</option>
            {options.faculties.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </Field>
        <Field label="Department">
          <select className={inputClass} value={form.department} onChange={(event) => setForm({ ...form, department: event.target.value })} required>
            <option value="">Select</option>
            {options.departments.filter((item) => String(item.faculty) === String(form.faculty)).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </Field>
        <Field label="Password"><input className={inputClass} value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /></Field>
        <div className="md:col-span-3"><Button type="submit">Register lecturer</Button></div>
      </form>
      {list.loading ? <Spinner /> : (
        <DataTable
          columns={[
            { key: "staff_id", label: "Staff ID" },
            { key: "full_name", label: "Name" },
            { key: "department_name", label: "Department" },
            { key: "employment_status", label: "Status" },
            { key: "courses", label: "Courses", render: (row) => row.assigned_courses?.map((course) => course.code).join(", ") || "None" },
            { key: "assign", label: "Assign", render: (row) => <Button variant="secondary" type="button" onClick={() => { setSelected(row); setCourses(row.assigned_courses?.map((course) => course.id) || []); }}>Courses</Button> },
          ]}
          rows={list.rows}
          page={list.page}
          pages={list.pages}
          onPage={list.setPage}
        />
      )}
      {selected ? (
        <form
          className="panel space-y-3 p-5"
          onSubmit={async (event) => {
            event.preventDefault();
            await api.post(`/lecturers/${selected.id}/assign_courses/`, { course_ids: courses.map(Number), primary_course: courses[0] });
            setMessage("Courses assigned.");
            setSelected(null);
            list.reload();
          }}
        >
          <h2 className="font-serif text-2xl text-forest">Assign courses to {selected.full_name}</h2>
          <select className={inputClass} multiple value={courses.map(String)} onChange={(event) => setCourses(Array.from(event.target.selectedOptions).map((option) => option.value))} aria-label="Courses">
            {options.courses.map((course) => <option key={course.id} value={course.id}>{course.code} · {course.title}</option>)}
          </select>
          <Button type="submit">Save assignments</Button>
        </form>
      ) : null}
    </div>
  );
}
