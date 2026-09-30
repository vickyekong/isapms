import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-paper px-6">
      <div className="max-w-lg text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gold">404</p>
        <h1 className="mt-3 font-serif text-4xl text-forest">This page is not part of the system</h1>
        <Link className="mt-6 inline-block font-semibold text-forest" to="/">
          Go to the dashboard
        </Link>
      </div>
    </main>
  );
}
