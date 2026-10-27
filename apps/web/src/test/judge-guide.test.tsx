import { fireEvent, render, screen, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { CaseGuide } from "@/features/workspace/case-guide";
import type { CaseData } from "@/features/workspace/types";

const data = JSON.parse(
  readFileSync("public/samples/supplier-contact-world.json", "utf8"),
) as CaseData;
afterEach(cleanup);
describe("Credential-free reviewer journey", () => {
  it("leads from the incident to evidence without a login action", () => {
    Element.prototype.scrollIntoView = vi.fn();
    const next = vi.fn();
    render(
      <CaseGuide tab="Overview" data={data} onTab={next} onHide={vi.fn()} onExport={vi.fn()} />,
    );
    expect(screen.getByText(/No account required/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Follow the evidence" }));
    expect(next).toHaveBeenCalledWith("Evidence");
    expect(screen.queryByRole("button", { name: /sign in/i })).not.toBeInTheDocument();
  });
  it("finishes with an actual report export action and own-data instructions", () => {
    const exportReport = vi.fn();
    render(
      <CaseGuide
        tab="Review"
        data={data}
        onTab={vi.fn()}
        onHide={vi.fn()}
        onExport={exportReport}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Download the sample report" }));
    expect(exportReport).toHaveBeenCalledOnce();
    expect(screen.getByRole("link", { name: /your own agent or data/ })).toHaveAttribute(
      "href",
      expect.stringContaining("CUSTOM_INTEGRATIONS.md"),
    );
  });
  it("describes the rejected repair correctly when the live model candidate is listed first", () => {
    const live = JSON.parse(
      readFileSync("public/samples/nemotron-live-world.json", "utf8"),
    ) as CaseData;
    render(
      <CaseGuide
        tab="Repairs & validation"
        data={live}
        onTab={vi.fn()}
        onHide={vi.fn()}
        onExport={vi.fn()}
      />,
    );
    expect(screen.getByText(/recipient restriction failed 2 legitimate tasks/)).toBeInTheDocument();
    expect(screen.getByText(/Select Restrict recipients/)).toBeInTheDocument();
  });
});
