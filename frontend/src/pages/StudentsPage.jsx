import { useState } from "react";
import { api, errorMessage } from "../api/client";
import { Alert, Button, ConfirmDialog, DataTable, Field, PageHeader, Spinner, inputClass } from "../components/ui";
import { useOptions, usePaged } from "../hooks";

const empty = {
  matric_number: "", first_name: "", surname: "", email: "", telephone: "", gender: "female",
  date_of_birth: "", faculty: "", department: "", programme: "", level: 100, admission_year: 2026,
  current_session: "", prior_cgpa: "0.00", password: "",
};

export default function StudentsPage() {
  const list = usePaged("/students/");
  const options = useOptions();
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [viewing, setViewing] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(null);
  const [facultyFilter, setFacultyFilter] = useState("");
  const filtered = usePaged("/students/", facultyFilter ? { faculty: facultyFilter } : {});

  function update(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    setError("");
    try {
      const payload = { ...form, prior_cgpa: form.prior_cgpa || "0" };
      if (!payload.password) delete payload.password;
      if (!payload.current_session) delete payload.current_session;
      const response = editing ? await api.patch(`/students/${editing}/`, payload) : await api.post("/students/", payload);
      setMessage(response.data.temporary_password ? `Student saved. Temporary password: ${response.data.temporary_password}` : "Student record saved.");
      setForm(empty);
      setEditing(null);
      list.reload();
      filtered.reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const source = facultyFilter ? filtered : list;

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Records" title="Students" description="Matriculation numbers and email addresses must be unique. Search, filter, and activate or deactivate records." />
      {message ? <Alert kind="success">{message}</Alert> : null}
      {error || source.error ? <Alert>{error || source.error}</Alert> : null}
      <form className="panel grid gap-4 p-5 md:grid-cols-3" onSubmit={onSubmit}>
        <Field label="Matriculation number"><input className={inputClass} name="matric_number" value={form.matric_number} onChange={update} required /></Field>
        <Field label="First name"><input className={inputClass} name="first_name" value={form.first_name} onChange={update} required /></Field>
        <Field label="Surname"><input className={inputClass} name="surname" value={form.surname} onChange={update} required /></Field>
        <Field label="Email"><input className={inputClass} type="email" name="email" value={form.email} onChange={update} required /></Field>
        <Field label="Telephone"><input className={inputClass} name="telephone" value={form.telephone} onChange={update} required /></Field>
        <Field label="Gender">
          <select className={inputClass} name="gender" value={form.gender} onChange={update}><option value="female">Female</option><option value="male">Male</option></select>
        </Field>
        <Field label="Date of birth"><input className={inputClass} type="date" name="date_of_birth" value={form.date_of_birth} onChange={update} required /></Field>
        <Field label="Faculty">
          <select className={inputClass} name="faculty" value={form.faculty} onChange={update} required>
            <option value="">Select</option>
            {options.faculties.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </Field>
        <Field label="Department">
          <select className={inputClass} name="department" value={form.department} onChange={update} required>
            <option value="">Select</option>
            {options.departments.filter((item) => !form.faculty || String(item.faculty) === String(form.faculty)).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </Field>
        <Field label="Programme"><input className={inputClass} name="programme" value={form.programme} onChange={update} required /></Field>
        <Field label="Level">
          <select className={inputClass} name="level" value={form.level} onChange={update}>{[100, 200, 300, 400, 500].map((level) => <option key={level} value={level}>{level}</option>)}</select>
        </Field>
        <Field label="Admission year"><input className={inputClass} name="admission_year" value={form.admission_year} onChange={update} required /></Field>
        <Field label="Current session">
          <select className={inputClass} name="current_session" value={form.current_session} onChange={update}>
            <option value="">Select</option>
            {options.sessions.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </Field>
        <Field label="Prior CGPA"><input className={inputClass} name="prior_cgpa" value={form.prior_cgpa} onChange={update} /></Field>
        <Field label="Password" hint="Leave blank to generate a temporary password."><input className={inputClass} name="password" value={form.password} onChange={update} /></Field>
        <div className="md:col-span-3 flex gap-2">
          <Button type="submit">{editing ? "Save changes" : "Register student"}</Button>
          {editing ? <Button type="button" variant="secondary" onClick={() => { setEditing(null); setForm(empty); }}>Cancel edit</Button> : null}
        </div>
      </form>
      <div className="grid gap-3 md:grid-cols-2">
        <input className={inputClass} aria-label="Search students" placeholder="Search name, email, or matric number" value={source.search} onChange={(event) => { source.setSearch(event.target.value); source.setPage(1); }} />
        <select className={inputClass} aria-label="Filter by faculty" value={facultyFilter} onChange={(event) => setFacultyFilter(event.target.value)}>
          <option value="">All faculties</option>
          {options.faculties.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
      </div>
      {source.loading ? <Spinner /> : (
        <DataTable
          columns={[
            { key: "matric_number", label: "Matric number" },
            { key: "full_name", label: "Name" },
            { key: "department_name", label: "Department" },
            { key: "level", label: "Level" },
            { key: "status", label: "Status" },
            { key: "actions", label: "Actions", render: (row) => (
              <div className="flex flex-wrap gap-2">
                <Button variant="ghost" type="button" onClick={() => setViewing(row)}>View</Button>
                <Button variant="secondary" type="button" onClick={() => { setEditing(row.id); setForm({ ...empty, ...row, date_of_birth: row.date_of_birth, password: "" }); }}>Edit</Button>
                <Button variant="secondary" type="button" onClick={() => setPending(row)}>{row.status === "active" ? "Deactivate" : "Activate"}</Button>
              </div>
            ) },
          ]}
          rows={source.rows}
          page={source.page}
          pages={source.pages}
          onPage={source.setPage}
        />
      )}
      {viewing ? (
        <div className="panel p-5 text-sm">
          <h2 className="font-serif text-2xl text-forest">{viewing.full_name}</h2>
          <p>{viewing.matric_number} · {viewing.email} · {viewing.telephone}</p>
          <p>{viewing.programme}, level {viewing.level}. Prior CGPA {viewing.prior_cgpa}. Current CGPA {viewing.current_cgpa}.</p>
        </div>
      ) : null}
      <ConfirmDialog
        open={Boolean(pending)}
        title="Change student status"
        message={`${pending?.full_name} will be ${pending?.status === "active" ? "suspended" : "reactivated"}.`}
        danger={pending?.status === "active"}
        confirmLabel="Confirm"
        onCancel={() => setPending(null)}
        onConfirm={async () => {
          await api.post(`/students/${pending.id}/${pending.status === "active" ? "deactivate" : "activate"}/`);
          setPending(null);
          source.reload();
        }}
      />
    </div>
  );
}
