import axios from "axios";
import { MCPServer, MCPServerCreate } from "../types";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8080";
const api = axios.create({ baseURL: BASE });

export const fetchServers = async (): Promise<MCPServer[]> => {
  const { data } = await api.get<MCPServer[]>("/api/servers");
  return data;
};

export const registerServer = async (payload: MCPServerCreate): Promise<MCPServer> => {
  const { data } = await api.post<MCPServer>("/api/servers", payload);
  return data;
};

export const deleteServer = async (id: number): Promise<void> => {
  await api.delete(`/api/servers/${id}`);
};
