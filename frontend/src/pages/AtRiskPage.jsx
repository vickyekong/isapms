import { useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import { Alert, Badge, DataTable, Disclaimer, PageHeader, Spinner } from "../components/ui";

export default function AtRiskPage() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/predictions/at-risk/")
      .then((response) => setRows(response.data.results || []))
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Support" title="At-risk students" description="Students are listed when the latest prediction is medium or high risk, or when attendance falls below the configured threshold." />
      <Disclaimer />
      {error ? <Alert>{error}</Alert> : null}
      {loading ? <Spinner /> : (
        <DataTable
          columns={[
            { key: "matric", label: "Matric number", render: (row) => row.student.matric_number },
            { key: "name", label: "Student", render: (row) => row.student.full_name },
            { key: "department", label: "Department", render: (row) => row.student.department },
            { key: "course", label: "Course", render: (row) => row.course?.code || "—" },
            { key: "risk_level", label: "Risk", render: (row) => <Badge tone={row.risk_level}>{row.risk_level}</Badge> },
            { key: "reason", label: "Reason" },
          ]}
          rows={rows.map((row, index) => ({ ...row, id: `${row.student.id}-${index}` }))}
          page={1}
          pages={1}
        />
      )}
    </div>
  );
}
