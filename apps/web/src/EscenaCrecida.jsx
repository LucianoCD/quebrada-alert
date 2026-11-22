import { useEffect, useRef } from "react";

/**
 * Escena animada de crecida repentina (placeholder de la Fase 3 del spec).
 * Sección transversal de un río de montaña en canvas 2D: lluvia convectiva,
 * ascenso del nivel, pico y descenso — ciclo de ~24 s. Sin WebGL ni dependencias.
 */
export default function EscenaCrecida() {
  const lienzo = useRef(null);

  useEffect(() => {
    const cv = lienzo.current;
    const ctx = cv.getContext("2d");
    let raf = 0;
    let w = 0;
    let h = 0;

    const ajustar = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = cv.clientWidth;
      h = cv.clientHeight;
      cv.width = w * dpr;
      cv.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    ajustar();
    const observador = new ResizeObserver(ajustar);
    observador.observe(cv);

    // Relieve fijo de la sección: ladera izq alta, cauce central, ladera der baja.
    const suelo = (x) => {
      const nx = x / w;
      const lecho = h * 0.72 + Math.sin(nx * 9) * h * 0.012;
      const margen = h * 0.16 * Math.exp(-((nx - 0.5) ** 2) / 0.08); // cauce más profundo al centro
      return lecho - margen + h * 0.1 * Math.max(0, nx - 0.72) ** 2 * 4;
    };

    const DURACION = 24000; // ms por ciclo
    const CICLOS = [
      // [t0, t1, intensidad] lluvia por fase
      [0, 0.18, 0],
      [0.18, 0.42, 1], // tormenta
      [0.42, 0.75, 0.15],
      [0.75, 1, 0],
    ];
    const nivelMeta = (t) => {
      // Nivel del agua en fracción del alto útil: llano -> crecida -> repunte -> normal.
      if (t < 0.18) return 0.16;
      if (t < 0.42) return 0.16 + ((t - 0.18) / 0.24) * 0.62; // ascenso rápido
      if (t < 0.62) return 0.78 - ((t - 0.42) / 0.2) * 0.1; // pico
      return 0.68 - ((t - 0.62) / 0.38) * 0.5; // descenso lento
    };
    const lluviaEn = (t) => {
      for (const [a, b, v] of CICLOS) if (t >= a && t < b) return v;
      return 0;
    };

    const gotas = Array.from({ length: 90 }, (_, i) => ({
      x: Math.random(),
      y: Math.random(),
      v: 0.6 + Math.random() * 0.8,
      l: 8 + Math.random() * 10,
    }));

    const dibujar = (ms) => {
      const t = (ms % DURACION) / DURACION;
      const lluvia = lluviaEn(t);
      const nivel = nivelMeta(t);
      const yAgua = h * (1 - nivel);

      // Cielo
      const cielo = ctx.createLinearGradient(0, 0, 0, h);
      cielo.addColorStop(0, "#0a1424");
      cielo.addColorStop(0.7, "#0d1b2e");
      cielo.addColorStop(1, "#12233a");
      ctx.fillStyle = cielo;
      ctx.fillRect(0, 0, w, h);

      // Lluvia (solo en fase tormenta)
      if (lluvia > 0) {
        ctx.strokeStyle = `rgba(125,211,252,${0.25 + lluvia * 0.3})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (const g of gotas) {
          g.y += g.v * 0.02 * lluvia;
          if (g.y > 1) {
            g.y = -0.05;
            g.x = Math.random();
          }
          const x = g.x * w;
          const y = g.y * h;
          ctx.moveTo(x, y);
          ctx.lineTo(x - 2, y + g.l);
        }
        ctx.stroke();
      }

      // Relieve (montaña)
      ctx.beginPath();
      ctx.moveTo(0, h);
      for (let x = 0; x <= w; x += 8) ctx.lineTo(x, suelo(x));
      ctx.lineTo(w, h);
      ctx.closePath();
      const roca = ctx.createLinearGradient(0, 0, 0, h);
      roca.addColorStop(0, "#1c2940");
      roca.addColorStop(1, "#0e1626");
      ctx.fillStyle = roca;
      ctx.fill();
      // línea de cresta
      ctx.beginPath();
      for (let x = 0; x <= w; x += 8) {
        const y = suelo(x);
        x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.strokeStyle = "rgba(148,163,184,0.35)";
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Cauce: agua dentro del lecho
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(0, suelo(0));
      for (let x = 0; x <= w; x += 8) ctx.lineTo(x, suelo(x));
      ctx.lineTo(w, h);
      ctx.lineTo(0, h);
      ctx.closePath();
      ctx.clip();

      // cuerpo de agua
      const agua = ctx.createLinearGradient(0, yAgua, 0, h);
      const crecida = nivel > 0.5;
      agua.addColorStop(0, crecida ? "#0ea5e9" : "#0369a1");
      agua.addColorStop(1, crecida ? "#075985" : "#0c4a6e");
      ctx.fillStyle = agua;
      ctx.fillRect(0, yAgua, w, h - yAgua);

      // superficie ondulada
      ctx.beginPath();
      for (let x = 0; x <= w; x += 6) {
        const y = yAgua + Math.sin(x * 0.05 + ms * 0.004) * 2.5;
        x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.strokeStyle = "rgba(186,230,253,0.8)";
      ctx.lineWidth = 2;
      ctx.stroke();

      // escombros arrastrados durante la crecida
      if (crecida) {
        ctx.fillStyle = "rgba(251,191,36,0.85)";
        for (let i = 0; i < 14; i++) {
          const px = ((i * 137 + ms * 0.05) % (w + 40)) - 20;
          const py = yAgua + 6 + ((i * 53) % Math.max(10, h - yAgua - 14));
          ctx.beginPath();
          ctx.arc(px, py, 1.6 + (i % 3), 0, Math.PI * 2);
          ctx.fill();
        }
      }
      ctx.restore();

      // etiqueta de nivel (estilo gauge)
      ctx.fillStyle = "rgba(8,12,20,0.75)";
      ctx.fillRect(w - 132, 14, 118, 58);
      ctx.strokeStyle = "rgba(148,163,184,0.3)";
      ctx.strokeRect(w - 132, 14, 118, 58);
      ctx.fillStyle = "#94a3b8";
      ctx.font = "10px 'JetBrains Mono', monospace";
      ctx.fillText("NIVEL SIMULADO", w - 122, 30);
      ctx.fillStyle = crecida ? "#f97316" : "#38bdf8";
      ctx.font = "bold 20px 'JetBrains Mono', monospace";
      ctx.fillText(`${Math.round(nivel * 100)}%`, w - 122, 56);
      ctx.fillStyle = "#64748b";
      ctx.font = "9px 'JetBrains Mono', monospace";
      ctx.fillText(lluvia > 0.5 ? "LLUVIA CONVECTIVA" : lluvia > 0 ? "LLUVIZNA" : "SIN LLUVIA", w - 122, 66);

      raf = requestAnimationFrame(dibujar);
    };
    raf = requestAnimationFrame(dibujar);
    return () => {
      cancelAnimationFrame(raf);
      observador.disconnect();
    };
  }, []);

  return <canvas ref={lienzo} className="h-full w-full" aria-label="Simulación animada de crecida de un río de montaña" />;
}
