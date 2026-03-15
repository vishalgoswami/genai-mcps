import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { registerServer } from "../api/servers";
import { MCPServerCreate } from "../types";

const EMPTY: MCPServerCreate = {
  name: "",
  description: "",
  url: "",
  tags: "",
  owner: "",
  auth_type: "none",
  is_public: true,
};

export function RegisterForm({ onSuccess }: { onSuccess?: () => void }) {
  const [form, setForm] = useState<MCPServerCreate>(EMPTY);
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: registerServer,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["servers"] });
      setForm(EMPTY);
      onSuccess?.();
    },
  });

  const set = (k: keyof MCPServerCreate) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => { e.preventDefault(); mutation.mutate(form); }}
    >
      {[
        { label: "Name *", key: "name", placeholder: "my-mcp-server" },
        { label: "URL *", key: "url", placeholder: "https://mcp.example.com" },
        { label: "Owner", key: "owner", placeholder: "Team / email" },
        { label: "Tags", key: "tags", placeholder: "search, data (comma-separated)" },
      ].map(({ label, key, placeholder }) => (
        <div key={key}>
          <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
          <input
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder={placeholder}
            value={String(form[key as keyof MCPServerCreate])}
            onChange={set(key as keyof MCPServerCreate)}
            required={key === "name" || key === "url"}
          />
        </div>
      ))}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
        <textarea
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          rows={3}
          placeholder="What does this MCP server do?"
          value={form.description}
          onChange={set("description")}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Auth Type</label>
        <select
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          value={form.auth_type}
          onChange={set("auth_type")}
        >
          <option value="none">None</option>
          <option value="api_key">API Key</option>
          <option value="oauth">OAuth</option>
        </select>
      </div>

      {mutation.isError && (
        <p className="text-red-500 text-sm">Failed to register server. Please try again.</p>
      )}

      <button
        type="submit"
        disabled={mutation.isPending}
        className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
      >
        {mutation.isPending ? "Registering..." : "Register Server"}
      </button>
    </form>
  );
}
