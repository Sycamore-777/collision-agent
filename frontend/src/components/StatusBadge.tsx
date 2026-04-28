import { formatStatusLabel } from "../utils/labels";

const statusMap: Record<string, string> = {
  pending: "badge pending",
  running: "badge running",
  succeeded: "badge success",
  failed: "badge failed",
  manual_review: "badge review",
  critical: "badge failed",
  high: "badge review",
  medium: "badge running",
  low: "badge success",
  unknown: "badge neutral"
};

export function StatusBadge({ value }: { value: string | null | undefined }) {
  if (!value) {
    return <span className="badge neutral">未知</span>;
  }

  return <span className={statusMap[value] ?? "badge neutral"}>{formatStatusLabel(value)}</span>;
}
