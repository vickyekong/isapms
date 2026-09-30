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
    </div>
  );
}
