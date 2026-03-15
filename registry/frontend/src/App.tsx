import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { MCPCard } from "./components/MCPCard";
import { fetchServers } from "./api/servers";

export default function App() {
  const { data: servers = [], isLoading, isError } = useQuery({
    queryKey: ["servers"],
    queryFn: fetchServers,
    refetchInterval: 30_000,
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">MCP Registry</h1>
        <Link
          to="/register"
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition"
        >
          + Register Server
        </Link>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {isLoading && <p className="text-gray-500">Loading servers...</p>}
        {isError && <p className="text-red-500">Failed to load servers.</p>}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {servers.map((server) => (
            <MCPCard key={server.id} server={server} />
          ))}
        </div>

        {!isLoading && servers.length === 0 && (
          <div className="text-center py-20 text-gray-400">
            No servers registered yet.{" "}
            <Link to="/register" className="text-blue-600 underline">
              Register one now
            </Link>
          </div>
        )}
      </main>
    </div>
  );
}
