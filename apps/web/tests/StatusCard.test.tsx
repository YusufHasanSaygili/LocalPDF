import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusCard } from "../components/StatusCard";

describe("StatusCard", () => {
  it("announces an error and keeps the recovery copy visible", () => {
    render(
      <StatusCard tone="error" title="PDF_ENCRYPTED">
        Orijinal dosyanız değiştirilmedi.
      </StatusCard>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("PDF_ENCRYPTED");
    expect(screen.getByText("Orijinal dosyanız değiştirilmedi.")).toBeVisible();
  });
});
