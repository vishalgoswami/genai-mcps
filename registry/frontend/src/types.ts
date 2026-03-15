export interface MCPServer {
  id: number;
  name: string;
  description: string;
  url: string;
  tags: string;
  owner: string;
  auth_type: string;
  is_public: boolean;
  status: "online" | "offline" | "unknown";
  last_checked: string | null;
  tools_count: number;
  created_at: string;
  updated_at: string;
}

export interface MCPServerCreate {
  name: string;
  description: string;
  url: string;
  tags: string;
  owner: string;
  auth_type: string;
  is_public: boolean;
}
