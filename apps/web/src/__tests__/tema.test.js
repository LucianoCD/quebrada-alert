import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { NIVELES } from "../niveles.js";

// Vitest reemplaza los CSS importados por una cadena vacía; los tokens se leen del archivo.
const css = readFileSync(resolve(__dirname, "../index.css"), "utf8");

function tokens(selector) {
  const bloque = css.slice(css.indexOf(`${selector} {`)).split("}")[0];
  return Object.fromEntries([...bloque.matchAll(/--([\w-]+):\s*([^;]+);/g)].map(([, k, v]) => [k, v.trim()]));
}

function rgba(valor) {
  if (valor.startsWith("#")) return [...[1, 3, 5].map((i) => parseInt(valor.slice(i, i + 2), 16)), 1];
  const [r, g, b, a = 1] = valor.match(/[\d.]+/g).map(Number);
  return [r, g, b, a];
}

const sobre = ([r, g, b, a], [fr, fg, fb]) => [r * a + fr * (1 - a), g * a + fg * (1 - a), b * a + fb * (1 - a)];

function luminancia([r, g, b]) {
  const [R, G, B] = [r, g, b].map((v) => {
    const c = v / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * R + 0.7152 * G + 0.0722 * B;
}

function contraste(a, b) {
  const [alto, bajo] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (alto + 0.05) / (bajo + 0.05);
}

const TEXTOS = ["tinta", "tinta-2", "tinta-3", "agua", "ocre", "verde", "amarillo", "naranja", "rojo", "recuperado", "lora"];

describe("tokens de tema", () => {
  const noche = tokens(":root");
  const temas = { noche, dia: { ...noche, ...tokens(':root[data-tema="dia"]') } };

  for (const [nombre, t] of Object.entries(temas)) {
    it(`tema ${nombre}: todo color de texto alcanza AA (4,5:1) sobre lienzo, superficie, elevada y sus realces`, () => {
      const lienzo = rgba(t.lienzo);
      const superficie = sobre(rgba(t.superficie), lienzo);
      const fondos = {
        lienzo,
        superficie,
        elevada: rgba(t.elevada),
        "superficie hundida": sobre(rgba(t.hundida), superficie),
        "superficie con realce": sobre(rgba(t.realce), superficie),
        "elevada con realce": sobre(rgba(t.realce), rgba(t.elevada)),
      };
      for (const texto of TEXTOS) {
        for (const [fondo, color] of Object.entries(fondos)) {
          expect(contraste(rgba(t[texto]), color), `${texto} sobre ${fondo}`).toBeGreaterThanOrEqual(4.5);
        }
      }
      // Botón primario: texto del color del lienzo sobre agua.
      expect(contraste(lienzo, rgba(t.agua)), "botón primario").toBeGreaterThanOrEqual(4.5);
    });
  }

  it("el texto sobre los rellenos de nivel alcanza AA y cada nivel tiene su token de texto", () => {
    for (const nivel of Object.values(NIVELES)) {
      expect(contraste(rgba(noche["sobre-nivel"]), rgba(nivel.color)), nivel.nombre).toBeGreaterThanOrEqual(4.5);
      expect(nivel.tinta).toMatch(/^var\(--(verde|amarillo|naranja|rojo)\)$/);
    }
  });
});
