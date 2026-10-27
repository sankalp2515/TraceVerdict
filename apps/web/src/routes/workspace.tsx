import { createFileRoute } from "@tanstack/react-router";
import { Workspace } from "@/features/workspace/workspace";
export const Route = createFileRoute("/workspace")({
  head: () => ({
    meta: [
      { title: "Investigation workspace — TraceVerdict" },
      { name: "robots", content: "noindex, nofollow" },
    ],
  }),
  component: Workspace,
});
