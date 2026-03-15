type Status = "online" | "offline" | "unknown";

const styles: Record<Status, string> = {
  online: "bg-green-100 text-green-700",
  offline: "bg-red-100 text-red-700",
  unknown: "bg-gray-100 text-gray-500",
};

const dots: Record<Status, string> = {
  online: "bg-green-500",
  offline: "bg-red-500",
  unknown: "bg-gray-400",
};

export function StatusBadge({ status }: { status: string }) {
  const s = (status as Status) in styles ? (status as Status) : "unknown";
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[s]}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dots[s]}`} />
      {s}
    </span>
  );
}
