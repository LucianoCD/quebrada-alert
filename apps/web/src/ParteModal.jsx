import { useEffect, useState } from "react";

/** Visor del Parte de Situación (spec §5.4.C): texto formateado + acciones. */
export default function ParteModal({ basinId, cuenca, onCerrar }) {
  const [texto, setTexto] = useState(null);
  const [error, setError] = useState(false);
  const [copiado, setCopiado] = useState(false);

  useEffect(() => {
    setTexto(null);
    setError(false);
    fetch(`/api/parte/${basinId}`)
      .then((r) => (r.ok ? r.text() : Promise.reject(r)))
      .then(setTexto)
      .catch(() => setError(true));
  }, [basinId]);

  useEffect(() => {
    const esc = (e) => e.key === "Escape" && onCerrar();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onCerrar]);

  const copiar = async () => {
    if (!texto) return;
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 1500);
    } catch {
      /* portapapeles no disponible */
    }
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-100 p-4" onClick={onCerrar}>
      <div
        className="panel-crisis flex max-h-[85vh] w-[min(640px,100%)] flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-300 px-4 py-2.5">
          <div>
            <div className="text-sm font-bold">Parte de situación — {cuenca?.localidad ?? basinId}</div>
            <div className="text-[10px] text-slate-600">{cuenca?.curso} · datos simulados · uso demostrativo</div>
          </div>
          <button type="button" onClick={onCerrar} className="rounded px-2 text-slate-600 hover:bg-slate-200 hover:text-slate-800">
            ✕
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          {error && <div className="text-sm text-rose-400">No se pudo obtener el parte.</div>}
          {!texto && !error && <div className="text-sm text-slate-600">Generando parte…</div>}
          {texto && (
            <pre className="parte-impresion tabular whitespace-pre-wrap rounded bg-slate-100 p-3 font-mono text-[11px] leading-5 text-slate-800">
              {texto}
            </pre>
          )}
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-slate-300 px-4 py-2.5">
          <button
            type="button"
            onClick={() => window.open(`/api/parte/${basinId}`, "_blank")}
            className="rounded border border-slate-300 px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-200"
          >
            TXT crudo
          </button>
          <button
            type="button"
            onClick={() => window.print()}
            className="rounded border border-slate-300 px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-200"
          >
            Imprimir / PDF
          </button>
          <button
            type="button"
            onClick={copiar}
            className="rounded border border-cyan-500/60 bg-cyan-500/10 px-3 py-1.5 text-xs font-semibold text-cyan-300 hover:bg-cyan-500/20"
          >
            {copiado ? "✓ Copiado" : "Copiar WhatsApp"}
          </button>
        </div>
      </div>
    </div>
  );
}
