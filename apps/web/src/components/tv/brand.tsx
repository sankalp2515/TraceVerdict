import { Fingerprint, ArrowUpRight } from "lucide-react";
export function Brand({ light = false }: { light?: boolean }) {
  return (
    <a href="/" className={`brand ${light ? "brand-light" : ""}`} aria-label="TraceVerdict home">
      <span className="brand-mark">
        <Fingerprint size={22} strokeWidth={1.5} />
      </span>
      <span>
        TraceVerdict<span className="brand-dot">.</span>
      </span>
    </a>
  );
}
export function Arrow() {
  return <ArrowUpRight size={16} aria-hidden="true" />;
}
