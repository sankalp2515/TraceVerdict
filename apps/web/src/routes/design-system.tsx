import { createFileRoute, redirect } from "@tanstack/react-router";

// Preserve old bookmarks without exposing internal design material in the product.
export const Route = createFileRoute("/design-system")({
  beforeLoad: () => {
    throw redirect({ href: "/workspace?mode=recorded&case=supplier-contact" });
  },
});
