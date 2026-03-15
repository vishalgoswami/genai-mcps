"""
Interactive REPL — Gemini LLM supervisor with multi-server MCP tool access.

Connects to one or many MCP servers via streamable HTTP, discovers all
available tools, and uses Gemini function calling to route queries
across any configured server.
"""
from __future__ import annotations
import asyncio
import json
import os

from rich.console import Console
from rich.markdown import Markdown
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from google import genai
from google.genai import types

console = Console()
PROMPT_STYLE = Style.from_dict({"prompt": "bold cyan"})

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "vg-pp-001")


class MCPRepl:
    """Multi-server MCP REPL — acts as a supervisor agent across all configured servers."""

    def __init__(self, server_urls: list[str], model: str):
        self.server_urls = server_urls
        self.model = model
        self._session = PromptSession()
        self._history: list[dict] = []
        self._all_mcp_tools: list = []  # Merged tool defs from all servers
        self._genai_tools: list[types.Tool] = []
        # Maps tool_name → (server_url, original_name)
        self._tool_routing: dict[str, tuple[str, str]] = {}

    def run(self):
        asyncio.run(self._arun())

    async def _arun(self):
        console.print(f"[bold]MCP CLI Supervisor[/bold] — model: [yellow]{self.model}[/yellow]")
        console.print(f"Connecting to {len(self.server_urls)} MCP server(s)...\n")

        # ── Discover tools from all servers ──────────────────────────────────
        for url in self.server_urls:
            try:
                async with streamablehttp_client(url) as (read, write, _):
                    async with ClientSession(read, write) as mcp_session:
                        await mcp_session.initialize()
                        tools_result = await mcp_session.list_tools()

                        console.print(f"[green]✓ {url}[/green] — {len(tools_result.tools)} tool(s)")
                        for t in tools_result.tools:
                            console.print(f"  [cyan]• {t.name}[/cyan]: {t.description}")
                            self._all_mcp_tools.append(t)
                            # Track routing: tool_name → server URL
                            self._tool_routing[t.name] = (url, t.name)
            except Exception as e:
                console.print(f"[red]✗ {url}[/red] — {e}")

        if not self._all_mcp_tools:
            console.print("[red]No tools discovered from any server. Exiting.[/red]")
            return

        # Build Gemini function declarations
        self._genai_tools = self._build_genai_tools()

        console.print(f"\n[bold]{len(self._all_mcp_tools)} total tool(s) available.[/bold]")
        console.print("Type [bold]/quit[/bold] to exit, [bold]/clear[/bold] to reset history, [bold]/servers[/bold] to list servers.\n")

        client = genai.Client(project=GOOGLE_CLOUD_PROJECT, location="us-central1")

        while True:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self._session.prompt("You> ", style=PROMPT_STYLE).strip()
                )
            except (EOFError, KeyboardInterrupt):
                break

            if not user_input:
                continue
            if user_input == "/quit":
                break
            if user_input == "/clear":
                self._history.clear()
                console.print("[dim]History cleared.[/dim]")
                continue
            if user_input == "/servers":
                for url in self.server_urls:
                    console.print(f"  [cyan]{url}[/cyan]")
                continue

            self._history.append({"role": "user", "parts": [{"text": user_input}]})

            # Agent loop: call Gemini, handle tool calls across servers, repeat
            response_text = await self._agent_loop(client)
            self._history.append({"role": "model", "parts": [{"text": response_text}]})
            console.print(Markdown(response_text))

    def _build_genai_tools(self) -> list[types.Tool]:
        """Convert all merged MCP tool definitions to Gemini function declarations."""
        func_decls = []
        for tool in self._all_mcp_tools:
            params = tool.inputSchema if tool.inputSchema else {"type": "object", "properties": {}}
            func_decls.append(types.FunctionDeclaration(
                name=tool.name,
                description=tool.description or "",
                parameters=params,
            ))
        return [types.Tool(function_declarations=func_decls)]

    async def _agent_loop(self, client) -> str:
        """Run the Gemini ↔ multi-server MCP tool loop until a final text response."""
        max_turns = 10
        for _ in range(max_turns):
            response = client.models.generate_content(
                model=self.model,
                contents=self._history,
                config=types.GenerateContentConfig(tools=self._genai_tools),
            )

            candidate = response.candidates[0]
            parts = candidate.content.parts

            # Check for function calls
            fn_calls = [p for p in parts if p.function_call]
            if not fn_calls:
                # Final text answer
                return "".join(p.text for p in parts if hasattr(p, "text") and p.text)

            # Execute each tool call via the correct upstream MCP server
            fn_responses = []
            for part in fn_calls:
                fc = part.function_call
                tool_name = fc.name
                args = dict(fc.args)

                if tool_name not in self._tool_routing:
                    console.print(f"  [red]→ unknown tool: {tool_name}[/red]")
                    fn_responses.append(types.Part.from_function_response(
                        name=tool_name, response={"error": f"Unknown tool: {tool_name}"}
                    ))
                    continue

                server_url, original_name = self._tool_routing[tool_name]
                console.print(f"  [dim]→ calling {original_name}({args}) on {server_url}[/dim]")

                try:
                    async with streamablehttp_client(server_url) as (read, write, _):
                        async with ClientSession(read, write) as mcp_session:
                            await mcp_session.initialize()
                            result = await mcp_session.call_tool(original_name, arguments=args)
                            output = result.content[0].text if result.content else "(empty)"
                except Exception as e:
                    output = f"Error calling tool: {e}"

                fn_responses.append(types.Part.from_function_response(
                    name=tool_name, response={"result": output}
                ))

            # Feed tool results back
            self._history.append({"role": "model", "parts": [{"functionCall": {"name": fc.name, "args": dict(fc.args)}} for part in fn_calls for fc in [part.function_call]]})
            self._history.append({"role": "user", "parts": [{"functionResponse": {"name": fr._raw.get("functionResponse", {}).get("name", ""), "response": {"result": "ok"}}} for fr in fn_responses]})

        return "(max tool-call turns reached)"
