import { useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import { Alert, Button, Disclaimer, PageHeader, Spinner, StatCard } from "../components/ui";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function AnalyticsPage() {
  const [models, setModels] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [training, setTraining] = useState(false);

  function load() {
    Promise.all([api.get("/predictions/model/"), api.get("/dashboard/")])
      .then(([modelResponse, dashboardResponse]) => {
        setModels(modelResponse.data.results || modelResponse.data);
        setDashboard(dashboardResponse.data);
      })
      .catch((err) => setError(errorMessage(err)));
  }

  useEffect(() => { load(); }, []);

  const active = (models || []).find((item) => item.is_active) || models?.[0];
  const matrix = active?.confusion_matrix?.matrix || [];
  const labels = active?.confusion_matrix?.labels || [];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Model"
        title="Predictive analytics"
        description="Train the decision tree on completed results. Metrics describe the held-out test split and do not by themselves justify an academic decision."
        actions={<Button type="button" disabled={training} onClick={async () => {
          setTraining(true);
          setError("");
          try {
            const response = await api.post("/predictions/train/");
            setMessage(`Model ${response.data.version} trained.`);
            load();
          } catch (err) {
            setError(errorMessage(err));
          } finally {
            setTraining(false);
          }
        }}>{training ? "Training…" : "Train model"}</Button>}
      />
      <Disclaimer />
      {message ? <Alert kind="success">{message}</Alert> : null}
      {error ? <Alert>{error}</Alert> : null}
      {!active && !dashboard ? <Spinner /> : null}
      {active ? (
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Accuracy" value={`${(active.accuracy * 100).toFixed(1)}%`} />
          <StatCard label="Precision" value={`${(active.precision * 100).toFixed(1)}%`} />
          <StatCard label="Recall" value={`${(active.recall * 100).toFixed(1)}%`} />
          <StatCard label="F1 score" value={`${(active.f1_score * 100).toFixed(1)}%`} detail={active.version} />
        </section>
      ) : null}
      {dashboard ? (
        <section className="panel p-4">
          <h2 className="mb-3 font-serif text-xl text-forest">Students by department</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={dashboard.students_by_department || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" hide />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" fill="#0B3D2E" />
            </BarChart>
          </ResponsiveContainer>
        </section>
      ) : null}
      {matrix.length ? (
        <section className="panel overflow-x-auto p-5">
          <h2 className="font-serif text-2xl text-forest">Confusion matrix</h2>
          <table className="mt-3 text-sm">
            <thead><tr><th className="px-3 py-2">Actual \ Predicted</th>{labels.map((label) => <th key={label} className="px-3 py-2">{label}</th>)}</tr></thead>
            <tbody>
              {matrix.map((row, index) => (
                <tr key={labels[index]}>
                  <th className="px-3 py-2 text-left">{labels[index]}</th>
                  {row.map((value, column) => <td key={`${index}-${column}`} className="px-3 py-2">{value}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}
    </div>
  );
}
