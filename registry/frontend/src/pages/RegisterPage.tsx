import { useNavigate } from "react-router-dom";
import { RegisterForm } from "../components/RegisterForm";

export default function RegisterPage() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4">
        <button onClick={() => navigate("/")} className="text-blue-600 hover:underline text-sm">
          ← Back to Registry
        </button>
        <h1 className="text-2xl font-bold text-gray-900 mt-1">Register MCP Server</h1>
      </header>
      <main className="max-w-xl mx-auto px-6 py-10">
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8">
          <RegisterForm onSuccess={() => navigate("/")} />
        </div>
      </main>
    </div>
  );
}
