import { Link } from "react-router-dom";

export default function AccessDeniedPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-paper px-6">
      <div className="max-w-lg text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gold">Restricted</p>
        <h1 className="mt-3 font-serif text-4xl text-forest">You do not have access to that page</h1>
        <p className="mt-3 text-sm text-[#526059]">Your role does not include this part of the academic system.</p>
        <Link className="mt-6 inline-block font-semibold text-forest" to="/">
          Return to your dashboard
        </Link>
      </div>
    </main>
  );
}
