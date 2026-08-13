import type { ReactNode } from "react";

export function StatusCard({
  tone = "neutral",
  title,
  children,
  action,
}: {
  tone?: "neutral" | "info" | "success" | "warning" | "error";
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className={`status-card status-${tone}`} role={tone === "error" ? "alert" : "status"}>
      <span className="status-dot" aria-hidden="true" />
      <div>
        <strong>{title}</strong>
        <div className="status-copy">{children}</div>
      </div>
      {action && <div className="status-action">{action}</div>}
    </section>
  );
}

