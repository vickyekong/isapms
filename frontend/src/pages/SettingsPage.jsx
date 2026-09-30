import { useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import { Alert, Button, Field, PageHeader, Spinner, inputClass } from "../components/ui";

export default function SettingsPage() {
  const [rows, setRows] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    api.get("/settings/", { params: { page_size: 50 } })
      .then((response) => {
        const results = response.data.results || [];
        setRows(results);
        setDrafts(Object.fromEntries(results.map((row) => [row.key, JSON.stringify(row.value)])));
      })
      .catch((err) => setError(errorMessage(err)));
  }, []);

  if (!rows.length && !error) return <Spinner />;

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Configuration" title="System settings" description="Attendance threshold, assessment limits, and the grading scale can be changed here. Existing results are not rewritten until scores are saved again." />
      {message ? <Alert kind="success">{message}</Alert> : null}
      {error ? <Alert>{error}</Alert> : null}
      <div className="space-y-4">
        {rows.map((row) => (
          <form key={row.key} className="panel space-y-3 p-5" onSubmit={async (event) => {
            event.preventDefault();
            try {
              const value = JSON.parse(drafts[row.key]);
              await api.patch(`/settings/${row.key}/`, { value });
              setMessage(`${row.key} updated.`);
            } catch (err) {
              setError(err instanceof SyntaxError ? "Enter valid JSON." : errorMessage(err));
            }
          }}>
            <Field label={row.key.replaceAll("_", " ")} hint={row.description}>
              <textarea className={inputClass} rows={row.key === "grading_scale" ? 8 : 2} value={drafts[row.key] || ""} onChange={(event) => setDrafts({ ...drafts, [row.key]: event.target.value })} />
            </Field>
            <Button type="submit">Save</Button>
          </form>
        ))}
      </div>
    </div>
  );
}
