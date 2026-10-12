import { useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import { Alert, Button, Field, PageHeader, inputClass } from "../components/ui";
import { useAuth } from "../context/AuthContext";

export default function ProfilePage() {
  const { user } = useAuth();
  const [profile, setProfile] = useState(null);
  const [phone, setPhone] = useState(user?.phone || "");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const path = user?.role === "student" ? "/students/me/" : "/auth/me/";
    api.get(path).then((response) => setProfile(response.data)).catch((err) => setError(errorMessage(err)));
  }, [user?.role]);

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Account" title="Profile" description="Personal details available to your role. Academic records stay on the courses, attendance, and results pages." />
      {message ? <Alert kind="success">{message}</Alert> : null}
      {error ? <Alert>{error}</Alert> : null}
      <form className="panel max-w-xl space-y-4 p-5" onSubmit={async (event) => {
        event.preventDefault();
        try {
          await api.patch("/auth/me/", { phone });
          setMessage("Profile updated.");
        } catch (err) {
          setError(errorMessage(err));
        }
      }}>
        <p className="text-sm">Name: {user?.full_name}</p>
        <p className="text-sm">Email: {user?.email}</p>
        <p className="text-sm capitalize">Role: {user?.role}</p>
        {profile?.matric_number ? <p className="text-sm">Matriculation number: {profile.matric_number}</p> : null}
        {profile?.staff_id ? <p className="text-sm">Staff ID: {profile.staff_id}</p> : null}
        {profile?.programme ? <p className="text-sm">Programme: {profile.programme}, level {profile.level}</p> : null}
        <Field label="Telephone"><input className={inputClass} value={phone} onChange={(event) => setPhone(event.target.value)} /></Field>
        <Button type="submit">Save profile</Button>
      </form>
      <ChangePasswordForm />
    </div>
  );
}

const emptyPasswords = { current: "", next: "", confirm: "" };

function ChangePasswordForm() {
  const { changePassword } = useAuth();
  const [form, setForm] = useState(emptyPasswords);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  function update(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    setMessage("");
    setError("");
    if (form.next !== form.confirm) {
      setError("The new passwords do not match.");
      return;
    }
    setSaving(true);
    try {
      setMessage(await changePassword(form.current, form.next));
      setForm(emptyPasswords);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="panel max-w-xl space-y-4 p-5" onSubmit={onSubmit}>
      <h2 className="font-serif text-2xl text-forest">Change password</h2>
      {message ? <Alert kind="success">{message}</Alert> : null}
      {error ? <Alert>{error}</Alert> : null}
      <Field label="Current password">
        <input className={inputClass} type="password" name="current" autoComplete="current-password" value={form.current} onChange={update} required />
      </Field>
      <Field label="New password" hint="At least 8 characters. Avoid common words and anything close to your name or email.">
        <input className={inputClass} type="password" name="next" autoComplete="new-password" minLength={8} value={form.next} onChange={update} required />
      </Field>
      <Field label="Confirm new password">
        <input className={inputClass} type="password" name="confirm" autoComplete="new-password" minLength={8} value={form.confirm} onChange={update} required />
      </Field>
      <Button type="submit" disabled={saving}>{saving ? "Changing…" : "Change password"}</Button>
    </form>
  );
}
