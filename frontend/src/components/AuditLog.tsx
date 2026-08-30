import { useEffect, useState } from "react";
import { fetchAuditLog } from "../api/client";
import type { AuditLogEntry } from "../types";

export default function AuditLog() {
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    setError(null);
    fetchAuditLog(100)
      .then(setEntries)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  if (loading)
    return (
      <div className="flex items-center justify-center py-32">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-forest-200 border-t-emerald rounded-full animate-spin" />
          <p className="font-body text-sm text-slate-mid">Loading audit log…</p>
        </div>
      </div>
    );

  if (error)
    return (
      <div className="card-bezel max-w-md mx-auto">
        <div className="card-bezel-inner text-center py-12">
          <div className="w-12 h-12 rounded-2xl bg-red-50 flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
          </div>
          <p className="font-body text-sm text-slate-mid">{error}</p>
        </div>
      </div>
    );

  return (
    <section>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-12">
        <div>
          <span className="inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 bg-forest-100 border border-forest-200/60 mb-5">
            <span className="font-mono text-[11px] uppercase tracking-[0.15em] text-dark-emerald font-medium">
              Ledger
            </span>
          </span>
          <h1 className="font-display text-3xl sm:text-4xl md:text-5xl font-bold text-near-black tracking-tight">
            Audit Log
          </h1>
        </div>
        <button onClick={load} className="btn-secondary self-start">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
          </svg>
          Refresh
        </button>
      </div>

      {entries.length === 0 ? (
        <div className="card-bezel max-w-md mx-auto">
          <div className="card-bezel-inner text-center py-16">
            <div className="w-14 h-14 rounded-2xl bg-forest-100 flex items-center justify-center mx-auto mb-5">
              <svg className="w-7 h-7 text-forest-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
            </div>
            <h3 className="font-display text-lg font-semibold text-near-black mb-2">
              No entries yet
            </h3>
            <p className="font-body text-sm text-slate-mid">
              Audit entries will appear here as actions are performed.
            </p>
          </div>
        </div>
      ) : (
        <div className="card-bezel">
          <div className="card-bezel-inner overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-forest-100">
                    {["ID", "Time", "Actor", "Action", "Entity", "Result", "Hash"].map(
                      (h) => (
                        <th
                          key={h}
                          className="text-left px-4 py-3 font-mono text-[10px] uppercase tracking-[0.12em] text-slate-light font-medium"
                        >
                          {h}
                        </th>
                      )
                    )}
                  </tr>
                </thead>
                <tbody>
                  {entries.map((e) => (
                    <tr
                      key={e.id}
                      className="border-b border-forest-50 last:border-0 transition-colors duration-300 spring hover:bg-forest-50/50"
                    >
                      <td className="px-4 py-3 font-mono text-xs text-slate-mid">
                        {e.id}
                      </td>
                      <td className="px-4 py-3 font-body text-xs text-slate-mid">
                        {new Date(e.timestamp).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 font-body text-xs text-near-black font-medium">
                        {e.actor}
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-forest-100 font-mono text-[10px] text-dark-emerald font-medium">
                          {e.action}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-body text-xs text-slate-mid">
                        {e.entity_id ?? "-"}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center gap-1.5 font-body text-xs font-medium ${
                            e.result === "success" ? "text-emerald" : "text-red-500"
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              e.result === "success" ? "bg-emerald" : "bg-red-500"
                            }`}
                          />
                          {e.result ?? "-"}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-[11px] text-slate-light" title={e.signed_hash ?? ""}>
                        {e.signed_hash ? `${e.signed_hash.slice(0, 8)}...` : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
