import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import InterruptorTema from "../InterruptorTema.jsx";
import { useTema } from "../tema.js";

afterEach(() => {
  if (useTema.getState().tema === "dia") useTema.getState().alternar();
});

describe("InterruptorTema", () => {
  it("arranca en noche, alterna a día, lo aplica al documento y lo recuerda", () => {
    render(<InterruptorTema />);
    const interruptor = screen.getByRole("switch", { name: "Tema de día" });
    expect(interruptor).toHaveAttribute("aria-checked", "false");
    expect(document.documentElement.dataset.tema).toBeUndefined();

    fireEvent.click(interruptor);
    expect(interruptor).toHaveAttribute("aria-checked", "true");
    expect(document.documentElement.dataset.tema).toBe("dia");
    expect(localStorage.getItem("quebrada-tema")).toBe("dia");

    fireEvent.click(interruptor);
    expect(interruptor).toHaveAttribute("aria-checked", "false");
    expect(document.documentElement.dataset.tema).toBeUndefined();
    expect(localStorage.getItem("quebrada-tema")).toBe("noche");
  });
});
