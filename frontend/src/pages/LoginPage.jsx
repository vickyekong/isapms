import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import { Alert, Button, Field, inputClass } from "../components/ui";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [demo, setDemo] = useState(null);

  useEffect(() => {
    api
      .get("/health/")
      .then(({ data }) => setDemo(data.demo ? data : null))
      .catch(() => setDemo(null));
  }, []);

  if (user) return <Navigate to="/" replace />;

  async function signIn(id, secret) {
    setLoading(true);
    setError("");
    try {
      await login(id, secret);
      navigate("/");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(event) {
    event.preventDefault();
    signIn(identifier.trim(), password);
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-[1.1fr_0.9fr]">
      <section className="hidden bg-forest px-12 py-16 text-white lg:flex lg:flex-col lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-gold">Nexus State University</p>
          <h1 className="mt-6 max-w-xl font-serif text-5xl leading-tight">Intelligent Student Academic Performance Monitoring System</h1>
          <p className="mt-6 max-w-lg text-lg text-[#D7E6DF]">
            A single place for student records, attendance, results, and decision-support predictions for a Nigerian university.
          </p>
        </div>
        <p className="text-sm text-[#D7E6DF]">Sample sign-in: sample.admin@nexusstate.edu.ng</p>
      </section>
      <section className="flex items-center justify-center bg-paper px-6 py-12">
        <form className="w-full max-w-md space-y-4" onSubmit={onSubmit}>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gold lg:hidden">Nexus State University</p>
          <h2 className="font-serif text-4xl text-forest">Sign in</h2>
          <p className="text-sm text-[#526059]">Use your email, staff ID, or matriculation number.</p>
          {error ? <Alert>{error}</Alert> : null}
          <Field label="Email, staff ID, or matriculation number">
            <input className={inputClass} value={identifier} onChange={(event) => setIdentifier(event.target.value)} autoComplete="username" required />
          </Field>
          <Field label="Password">
            <input className={inputClass} type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required />
          </Field>
          <Button className="w-full" type="submit" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </Button>
          <Link className="block text-sm font-semibold text-forest" to="/forgot-password">
            Forgot password?
          </Link>
          {demo ? (
            <div className="space-y-3 rounded-lg border border-gold/40 bg-white p-4">
              <p className="text-sm font-semibold text-forest">Demo with fictional sample data</p>
              <p className="text-xs text-[#526059]">
                Changes you make are temporary and reset when the server restarts. Password for every sample account: {demo.demo_password}
              </p>
              <div className="grid gap-2 sm:grid-cols-3">
                {demo.demo_accounts.map((account) => (
                  <Button
                    key={account.identifier}
                    type="button"
                    variant="secondary"
                    disabled={loading}
                    onClick={() => signIn(account.identifier, demo.demo_password)}
                  >
                    {account.role}
                  </Button>
                ))}
              </div>
            </div>
          ) : null}
        </form>
      </section>
    </main>
  );
}
