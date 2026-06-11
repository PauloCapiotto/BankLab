import { describe, expect, it } from "vitest";

import { formatCurrency, formatDate, formatDateTime } from "@/lib/format";

describe("formatCurrency", () => {
  it("formata string decimal como moeda brasileira", () => {
    const result = formatCurrency("1500.00");
    expect(result).toContain("R$");
    expect(result).toContain("1.500,00");
  });

  it("formata valores com centavos", () => {
    expect(formatCurrency("6250.55")).toContain("6.250,55");
  });

  it("formata zero", () => {
    expect(formatCurrency("0.00")).toContain("0,00");
  });
});

describe("formatDate", () => {
  it("formata ISO como data curta brasileira", () => {
    expect(formatDate("2026-06-10T12:00:00+00:00")).toMatch(/\d{2}\/\d{2}\/\d{4}/);
  });
});

describe("formatDateTime", () => {
  it("inclui data e hora", () => {
    expect(formatDateTime("2026-06-10T12:00:00+00:00")).toMatch(
      /\d{2}\/\d{2}\/\d{4},? \d{2}:\d{2}/
    );
  });
});
