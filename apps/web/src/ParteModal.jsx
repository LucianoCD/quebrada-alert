import { useEffect, useRef, useState } from "react";

/** Visor del Parte de Situación (spec §5.4.C): texto formateado + acciones. */
export default function ParteModal({ basinId, cuenca, onCerrar }) {
  const [texto, setTexto] = useState(null);
  const [error, setError] = useState(false);
  const [copiado, setCopiado] = useState(false);
  const temporizadorRef = useRef(null);

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

  useEffect(() => () => clearTimeout(temporizadorRef.current), []);

  const copiar = async () => {
    if (!texto) return;
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado(true);
      clearTimeout(temporizadorRef.current);
      temporizadorRef.current = setTimeout(() => setCopiado(false), 1500);
    } catch {
      /* portapapeles no disponible */
    }
  };

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs"
      onClick={onCerrar}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="parte-modal-titulo"
        className="panel-crisis flex max-h-[85vh] w-[min(640px,100%)] flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-borde-fuerte px-4 py-2.5">
          <div>
            <div id="parte-modal-titulo" className="text-sm font-bold">
              Parte de situación — {cuenca?.localidad ?? basinId}
            </div>
            <div className="text-[10px] text-tinta-2">{cuenca?.curso} · datos simulados · uso demostrativo</div>
          </div>
          <button
            type="button"
            onClick={onCerrar}
            aria-label="Cerrar parte de situación"
            className="rounded px-2 text-tinta-2 hover:bg-realce hover:text-tinta"
          >
            ✕
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          {error && <div className="text-sm text-rojo">No se pudo obtener el parte.</div>}
          {!texto && !error && <div className="text-sm text-tinta-2">Generando parte…</div>}
          {texto && (
            <pre className="parte-impresion tabular whitespace-pre-wrap rounded bg-hundida p-3 font-mono text-[11px] leading-5 text-tinta">
              {texto}
            </pre>
          )}
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-borde-fuerte px-4 py-2.5">
          <button
            type="button"
            onClick={() => window.open(`/api/parte/${basinId}`, "_blank")}
            className="rounded border border-borde-fuerte px-3 py-1.5 text-xs text-tinta-2 hover:bg-realce"
          >
            TXT crudo
          </button>
          <button
            type="button"
            onClick={() => window.print()}
            className="rounded border border-borde-fuerte px-3 py-1.5 text-xs text-tinta-2 hover:bg-realce"
          >
            Imprimir / PDF
          </button>
          <button
            type="button"
            onClick={copiar}
            className="rounded border border-agua/60 bg-agua/10 px-3 py-1.5 text-xs font-semibold text-agua hover:bg-agua/15"
          >
            {copiado ? "✓ Copiado" : "Copiar WhatsApp"}
          </button>
        </div>
      </div>
    </div>
  );
}
