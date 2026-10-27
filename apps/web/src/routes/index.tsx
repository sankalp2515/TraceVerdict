import { createFileRoute } from "@tanstack/react-router";
import { Landing } from "@/features/marketing/landing";
export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "TraceVerdict — A conclusion you can inspect" },
      {
        name: "description",
        content:
          "Investigate suspicious AI-agent actions, inspect source-linked evidence and compare tested policy repairs before human review. Explore a recorded sample case.",
      },
      { property: "og:title", content: "TraceVerdict — A conclusion you can inspect" },
      {
        property: "og:description",
        content: "Evidence you can open. Tested policy repairs. A decision you can explain.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: Landing,
});
