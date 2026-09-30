import { useState } from "react";
import { api, errorMessage } from "../api/client";
import { Alert, Button, ConfirmDialog, DataTable, Field, PageHeader, Spinner, inputClass } from "../components/ui";
import { usePaged } from "../hooks";

const empty = { email: "", first_name: "", last_name: "", role: "admin", phone: "", password: "", is_active: true };

export default function UsersPage() {
  const list = usePaged("/users/");
  const [form, setForm] = useState(empty);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(null);

  function update(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    setError("");
    try {
      await api.post("/users/", form);
      setForm(empty);
      setMessage("User account created.");
      list.reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Administration" title="User management" description="Create accounts, assign roles, and activate or deactivate access. Restricted actions are also enforced by the API." />
      {message ? <Alert kind="success">{message}</Alert> : null}
      {error || list.error ? <Alert>{error || list.error}</Alert> : null}
      <form className="panel grid gap-4 p-5 md:grid-cols-3" onSubmit={onSubmit}>
        <Field label="First name"><input className={inputClass} name="first_name" value={form.first_name} onChange={update} required /></Field>
        <Field label="Surname"><input className={inputClass} name="last_name" value={form.last_name} onChange={update} required /></Field>
        <Field label="Email"><input className={inputClass} type="email" name="email" value={form.email} onChange={update} required /></Field>
        <Field label="Phone"><input className={inputClass} name="phone" value={form.phone} onChange={update} /></Field>
        <Field label="Role">
          <select className={inputClass} name="role" value={form.role} onChange={update}>
            <option value="admin">Administrator</option>
            <option value="lecturer">Lecturer</option>
            <option value="student">Student</option>
          </select>
        </Field>
        <Field label="Temporary password"><input className={inputClass} name="password" value={form.password} onChange={update} required /></Field>
        <div className="md:col-span-3"><Button type="submit">Create user</Button></div>
      </form>
      <input className={inputClass} placeholder="Search users" value={list.search} onChange={(event) => { list.setSearch(event.target.value); list.setPage(1); }} aria-label="Search users" />
      {list.loading ? <Spinner /> : (
        <DataTable
          columns={[
            { key: "name", label: "Name", render: (row) => row.full_name || row.email },
            { key: "email", label: "Email" },
            { key: "role", label: "Role" },
            { key: "is_active", label: "Status", render: (row) => (row.is_active ? "Active" : "Inactive") },
            { key: "actions", label: "Actions", render: (row) => (
              <Button variant="secondary" type="button" onClick={() => setPending(row)}>{row.is_active ? "Deactivate" : "Activate"}</Button>
            ) },
          ]}
          rows={list.rows}
          page={list.page}
          pages={list.pages}
          onPage={list.setPage}
        />
      )}
      <ConfirmDialog
        open={Boolean(pending)}
        title={pending?.is_active ? "Deactivate account" : "Activate account"}
        message={`This will ${pending?.is_active ? "block" : "restore"} sign-in for ${pending?.email}.`}
        danger={pending?.is_active}
        confirmLabel={pending?.is_active ? "Deactivate" : "Activate"}
        onCancel={() => setPending(null)}
        onConfirm={async () => {
          await api.post(`/users/${pending.id}/${pending.is_active ? "deactivate" : "activate"}/`);
          setPending(null);
          list.reload();
        }}
      />
    </div>
  );
}
