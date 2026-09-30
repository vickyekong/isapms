import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import { Alert, Button, Field, inputClass } from "../components/ui";

export default function PasswordResetPage({ mode }) {
  const [params] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [debugUrl, setDebugUrl] = useState("");

  async function onSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      if (mode === "request") {
        const response = await api.post("/auth/password-reset/", { email });
        setMessage(response.data.detail);
        setDebugUrl(response.data.debug_reset_url || "");
      } else {
        const response = await api.post("/auth/password-reset/confirm/", {
          uid: params.get("uid"),
          token: params.get("token"),
          password,
        });
        setMessage(response.data.detail);
      }
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-paper px-6">
      <form className="panel w-full max-w-md space-y-4 p-6" onSubmit={onSubmit}>
        <h1 className="font-serif text-3xl text-forest">{mode === "request" ? "Reset password" : "Choose a new password"}</h1>
        {error ? <Alert>{error}</Alert> : null}
        {message ? <Alert kind="success">{message}</Alert> : null}
        {debugUrl ? (
          <Alert kind="info">
            Development reset link: <a className="font-semibold underline" href={debugUrl}>{debugUrl}</a>
          </Alert>
        ) : null}
        {mode === "request" ? (
          <Field label="Email address">
            <input className={inputClass} type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </Field>
        ) : (
          <Field label="New password" hint="At least 8 characters, not entirely numeric.">
            <input className={inputClass} type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          </Field>
        )}
        <Button type="submit">{mode === "request" ? "Send reset link" : "Update password"}</Button>
        <Link className="block text-sm font-semibold text-forest" to="/login">
          Back to sign in
        </Link>
      </form>
    </main>
  );
}
