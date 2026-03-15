import { MCPServer } from "../types";
import { StatusBadge } from "./StatusBadge";
import { ExternalLink, Wrench, Tag, User } from "lucide-react";

interface Props {
  server: MCPServer;
}

export function MCPCard({ server }: Props) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5 flex flex-col gap-3 hover:shadow-md transition">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <h2 className="text-lg font-semibold text-gray-900 truncate">{server.name}</h2>
        <StatusBadge status={server.status} />
      </div>

      {/* Description */}
      {server.description && (
        <p className="text-sm text-gray-500 line-clamp-2">{server.description}</p>
      )}

      {/* Meta */}
      <div className="flex flex-wrap gap-2 text-xs text-gray-500">
        {server.owner && (
          <span className="flex items-center gap-1">
            <User size={12} /> {server.owner}
          </span>
        )}
        <span className="flex items-center gap-1">
          <Wrench size={12} /> {server.tools_count} tools
        </span>
        {server.tags && (
          <span className="flex items-center gap-1">
            <Tag size={12} /> {server.tags}
          </span>
        )}
      </div>

      {/* Auth */}
      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full self-start">
        auth: {server.auth_type}
      </span>

      {/* URL */}
      <a
        href={server.url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs text-blue-600 hover:underline flex items-center gap-1 truncate"
      >
        <ExternalLink size={12} /> {server.url}
      </a>

      {/* Last checked */}
      {server.last_checked && (
        <p className="text-xs text-gray-400">
          Checked: {new Date(server.last_checked).toLocaleString()}
        </p>
      )}
    </div>
  );
}
