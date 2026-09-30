export function Button({ children, variant = "primary", className = "", ...props }) {
  const styles = {
    primary: "bg-forest text-white hover:bg-pine",
    secondary: "border border-[#D5CBB8] bg-white text-ink hover:bg-[#F7F4EE]",
    danger: "bg-[#8C2F2F] text-white hover:bg-[#732626]",
    ghost: "text-forest hover:bg-[#E7F2EC]",
  };
  return (
    <button
      className={`inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60 ${styles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Field({ label, children, hint }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-semibold text-ink">{label}</span>
      {children}
      {hint ? <span className="mt-1 block text-xs text-[#667068]">{hint}</span> : null}
    </label>
  );
}

export const inputClass =
  "w-full rounded-lg border border-[#D5CBB8] bg-white px-3 py-2 text-sm text-ink outline-none focus:border-forest";

export function Alert({ kind = "error", children }) {
  const styles = {
    error: "border-[#E7C1C1] bg-[#FDF2F2] text-[#7A2424]",
    success: "border-[#C9E2D4] bg-[#F1FAF5] text-[#145C45]",
    info: "border-[#E4D7B4] bg-[#FBF6EA] text-[#6D5420]",
  };
  return <div className={`rounded-xl border px-4 py-3 text-sm ${styles[kind]}`}>{children}</div>;
}

export function Badge({ children, tone = "neutral" }) {
  const styles = {
    neutral: "bg-[#EEF1EF] text-[#314039]",
    low: "bg-[#E5F6EC] text-[#146C43]",
    medium: "bg-[#FFF4D8] text-[#8A5A00]",
    high: "bg-[#FDE8E8] text-[#9B2C2C]",
    sample: "bg-[#F3E8C8] text-[#6D5420]",
  };
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${styles[tone] || styles.neutral}`}>{children}</span>;
}

export function Spinner({ label = "Loading" }) {
  return (
    <div className="flex items-center gap-3 py-8 text-sm text-[#526059]" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-forest border-t-transparent" />
      {label}
    </div>
  );
}

export function EmptyState({ title, body }) {
  return (
    <div className="px-4 py-12 text-center">
      <p className="font-serif text-xl text-forest">{title}</p>
      <p className="mt-2 text-sm text-[#667068]">{body}</p>
    </div>
  );
}

export function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div>
        {eyebrow ? <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gold">{eyebrow}</p> : null}
        <h1 className="font-serif text-3xl text-forest">{title}</h1>
        {description ? <p className="mt-2 max-w-3xl text-sm text-[#526059]">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}

export function Modal({ open, title, children, onClose }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center" role="presentation">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-auto rounded-2xl bg-white p-5 shadow-xl" role="dialog" aria-modal="true" aria-label={title}>
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 className="font-serif text-2xl text-forest">{title}</h2>
          <button className="rounded-md px-2 py-1 text-sm" onClick={onClose} type="button">
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function ConfirmDialog({ open, title, message, confirmLabel = "Confirm", danger = false, onConfirm, onCancel }) {
  return (
    <Modal open={open} title={title} onClose={onCancel}>
      <p className="text-sm text-[#526059]">{message}</p>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="secondary" onClick={onCancel} type="button">
          Cancel
        </Button>
        <Button variant={danger ? "danger" : "primary"} onClick={onConfirm} type="button">
          {confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}

export function Disclaimer({ text }) {
  return (
    <Alert kind="info">
      {text ||
        "Predictions support lecturers and administrators. They do not replace professional academic judgement and are not final academic decisions."}
    </Alert>
  );
}

export function DataTable({ columns, rows, page, pages, onPage, empty }) {
  if (!rows?.length) return <div className="panel">{empty || <EmptyState title="No records" body="Nothing matches the current filters." />}</div>;
  return (
    <div className="panel overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-[#F7F4EE] text-xs uppercase tracking-wide text-[#667068]">
            <tr>
              {columns.map((column) => (
                <th key={column.key} className="px-4 py-3 font-semibold">
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={row.id || index} className="border-t border-[#EFE8DC]">
                {columns.map((column) => (
                  <td key={column.key} className="px-4 py-3 align-top">
                    {column.render ? column.render(row) : row[column.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {pages > 1 ? (
        <div className="flex items-center justify-between border-t border-[#EFE8DC] px-4 py-3 text-sm">
          <span>
            Page {page} of {pages}
          </span>
          <div className="flex gap-2">
            <Button variant="secondary" type="button" disabled={page <= 1} onClick={() => onPage(page - 1)}>
              Previous
            </Button>
            <Button variant="secondary" type="button" disabled={page >= pages} onClick={() => onPage(page + 1)}>
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function StatCard({ label, value, detail }) {
  return (
    <article className="panel p-5">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#667068]">{label}</p>
      <p className="mt-2 font-serif text-3xl text-forest">{value ?? "—"}</p>
      {detail ? <p className="mt-1 text-sm text-[#526059]">{detail}</p> : null}
    </article>
  );
}
