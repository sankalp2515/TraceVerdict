import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { IntegrationIntake } from "../features/workspace/onboarding";
import { api } from "../features/workspace/api";

vi.mock("../features/workspace/api", () => ({ api: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

it("registers a scoped policy and refreshes the agent list", async () => {
  vi.mocked(api).mockResolvedValue({ agent_id: "my-agent" });
  const refresh = vi.fn().mockResolvedValue(undefined);
  render(<IntegrationIntake tenant="customer" onAgent={refresh} onCase={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("New agent ID"), { target: { value: "my-agent" } });
  fireEvent.click(screen.getByRole("button", { name: "Register agent" }));
  await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
  expect(api).toHaveBeenCalledWith(
    "/v1/agents",
    expect.objectContaining({
      agent_id: "my-agent",
      policy: expect.objectContaining({ org: "customer" }),
    }),
  );
});

it("rejects malformed capture JSON before transmitting it", async () => {
  render(<IntegrationIntake tenant="customer" onAgent={vi.fn()} onCase={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Incident capture JSON"), { target: { value: "{bad" } });
  fireEvent.click(screen.getByRole("button", { name: "Import captured incident" }));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Import captured incident" })).not.toBeDisabled(),
  );
  expect(api).not.toHaveBeenCalled();
});

it("imports the capture then opens a live nonfixture case", async () => {
  vi.mocked(api)
    .mockResolvedValueOnce({ snapshot_id: "snapshot_original" })
    .mockResolvedValueOnce({ case_id: "case_original" });
  const open = vi.fn().mockResolvedValue(undefined);
  render(<IntegrationIntake tenant="customer" onAgent={vi.fn()} onCase={open} />);
  fireEvent.change(screen.getByLabelText("Incident capture JSON"), {
    target: { value: JSON.stringify({ agent_id: "my-agent", document: "original" }) },
  });
  fireEvent.click(screen.getByRole("button", { name: "Import captured incident" }));
  await waitFor(() => expect(open).toHaveBeenCalledWith("case_original"));
  expect(api).toHaveBeenNthCalledWith(
    2,
    "/v1/cases",
    expect.objectContaining({
      agent_id: "my-agent",
      execution_mode: "live",
      snapshot_id: "snapshot_original",
    }),
  );
});
