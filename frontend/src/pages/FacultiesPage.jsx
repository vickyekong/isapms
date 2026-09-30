import { useState } from "react";
import { api, errorMessage } from "../api/client";
import { Alert, Button, DataTable, Field, PageHeader, Spinner, inputClass } from "../components/ui";
import { useOptions, usePaged } from "../hooks";

export default function FacultiesPage() {
  const [tab, setTab] = useState("faculties");
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Structure" title="Faculties, departments, and sessions" description="Organise the institution, then filter dashboards and reports by these units." />
      <div className="flex gap-2">
        {["faculties", "departments", "sessions"].map((item) => (
          <Button key={item} type="button" variant={tab === item ? "primary" : "secondary"} onClick={() => setTab(item)}>{item}</Button>
        ))}
      </div>
      {tab === "faculties" ? <SimpleResource path="/faculties/" title="Faculty" fields={[{ name: "name" }, { name: "code" }, { name: "description", required: false }]} columns={["name", "code", "department_count"]} /> : null}
      {tab === "departments" ? <DepartmentForm /> : null}
      {tab === "sessions" ? <SessionForms /> : null}
    </div>
  );
}

function SimpleResource({ path, title, fields, columns }) {
  const list = usePaged(path);
  const [form, setForm] = useState({});
  const [error, setError] = useState("");
  async function onSubmit(event) {
    event.preventDefault();
    try {
      await api.post(path, form);
      setForm({});
      list.reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }
  return (
    <div className="space-y-4">
      {error || list.error ? <Alert>{error || list.error}</Alert> : null}
      <form className="panel grid gap-3 p-5 md:grid-cols-3" onSubmit={onSubmit}>
        {fields.map((field) => (
          <Field key={field.name} label={field.name}>
            <input className={inputClass} value={form[field.name] || ""} onChange={(event) => setForm({ ...form, [field.name]: event.target.value })} required={field.required !== false} />
          </Field>
        ))}
        <div className="md:col-span-3"><Button type="submit">Create {title}</Button></div>
      </form>
      {list.loading ? <Spinner /> : <DataTable columns={columns.map((key) => ({ key, label: key.replaceAll("_", " ") }))} rows={list.rows} page={list.page} pages={list.pages} onPage={list.setPage} />}
    </div>
  );
}

function DepartmentForm() {
  const list = usePaged("/departments/");
  const options = useOptions();
  const [form, setForm] = useState({ name: "", code: "", faculty: "" });
  const [error, setError] = useState("");
  return (
    <div className="space-y-4">
      {error || list.error ? <Alert>{error || list.error}</Alert> : null}
      <form className="panel grid gap-3 p-5 md:grid-cols-3" onSubmit={async (event) => {
        event.preventDefault();
        try { await api.post("/departments/", form); setForm({ name: "", code: "", faculty: "" }); list.reload(); } catch (err) { setError(errorMessage(err)); }
      }}>
        <Field label="Faculty"><select className={inputClass} value={form.faculty} onChange={(event) => setForm({ ...form, faculty: event.target.value })} required><option value="">Select</option>{options.faculties.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
        <Field label="Name"><input className={inputClass} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required /></Field>
        <Field label="Code"><input className={inputClass} value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value })} required /></Field>
        <div className="md:col-span-3"><Button type="submit">Create department</Button></div>
      </form>
      {list.loading ? <Spinner /> : <DataTable columns={[{ key: "faculty_name", label: "Faculty" }, { key: "name", label: "Department" }, { key: "code", label: "Code" }]} rows={list.rows} page={list.page} pages={list.pages} onPage={list.setPage} />}
    </div>
  );
}

function SessionForms() {
  const sessions = usePaged("/sessions/");
  const semesters = usePaged("/semesters/");
  const [session, setSession] = useState({ name: "", start_date: "", end_date: "", is_current: false });
  const [semester, setSemester] = useState({ session: "", name: "first", is_current: false });
  const [error, setError] = useState("");
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {error ? <div className="lg:col-span-2"><Alert>{error}</Alert></div> : null}
      <form className="panel space-y-3 p-5" onSubmit={async (event) => {
        event.preventDefault();
        try { await api.post("/sessions/", session); sessions.reload(); } catch (err) { setError(errorMessage(err)); }
      }}>
        <h2 className="font-serif text-2xl text-forest">Academic session</h2>
        <Field label="Name"><input className={inputClass} placeholder="2026/2027" value={session.name} onChange={(event) => setSession({ ...session, name: event.target.value })} required /></Field>
        <Field label="Starts"><input className={inputClass} type="date" value={session.start_date} onChange={(event) => setSession({ ...session, start_date: event.target.value })} required /></Field>
        <Field label="Ends"><input className={inputClass} type="date" value={session.end_date} onChange={(event) => setSession({ ...session, end_date: event.target.value })} required /></Field>
        <label className="text-sm"><input type="checkbox" checked={session.is_current} onChange={(event) => setSession({ ...session, is_current: event.target.checked })} /> Current session</label>
        <Button type="submit">Create session</Button>
        {sessions.loading ? <Spinner /> : <ul className="text-sm">{sessions.rows.map((item) => <li key={item.id}>{item.name}{item.is_current ? " · current" : ""}</li>)}</ul>}
      </form>
      <form className="panel space-y-3 p-5" onSubmit={async (event) => {
        event.preventDefault();
        try { await api.post("/semesters/", semester); semesters.reload(); } catch (err) { setError(errorMessage(err)); }
      }}>
        <h2 className="font-serif text-2xl text-forest">Semester</h2>
        <Field label="Session"><select className={inputClass} value={semester.session} onChange={(event) => setSemester({ ...semester, session: event.target.value })} required><option value="">Select</option>{sessions.rows.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
        <Field label="Name"><select className={inputClass} value={semester.name} onChange={(event) => setSemester({ ...semester, name: event.target.value })}><option value="first">First semester</option><option value="second">Second semester</option></select></Field>
        <label className="text-sm"><input type="checkbox" checked={semester.is_current} onChange={(event) => setSemester({ ...semester, is_current: event.target.checked })} /> Current semester</label>
        <Button type="submit">Create semester</Button>
        {semesters.loading ? <Spinner /> : <ul className="text-sm">{semesters.rows.map((item) => <li key={item.id}>{item.label}</li>)}</ul>}
      </form>
    </div>
  );
}
