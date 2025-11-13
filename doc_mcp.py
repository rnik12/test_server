import json
import datetime
from typing import Any, Dict, List, Optional

import requests


class MCPClient:
    """
    Minimal MCP JSON-RPC client for HTTP endpoints.

    It implements:
      - initialize
      - notifications/initialized
      - tools/list (with pagination)
      - resources/list (with pagination)
      - prompts/list (with pagination)
    """

    def __init__(
        self,
        endpoint: str,
        protocol_version: str = "2025-06-18",
        timeout: int = 30,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.protocol_version = protocol_version
        self.timeout = timeout
        self._id_counter = 0

    def _next_id(self) -> str:
        self._id_counter += 1
        return f"req-{self._id_counter}"

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(
            self.endpoint,
            json=payload,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        return data

    def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a JSON-RPC request and return the 'result' field.
        Raises RuntimeError if the server returns an error object.
        """
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        data = self._post(payload)

        if "error" in data:
            raise RuntimeError(
                f"JSON-RPC error from {method}: "
                f"{data['error'].get('code')} {data['error'].get('message')}"
            )

        return data.get("result", {})

    def notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """
        Send a JSON-RPC notification (no id, no result expected).
        """
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        # Fire-and-forget; we still check HTTP status
        self._post(payload)

    def initialize(
        self,
        client_name: str = "mcp-doc-generator",
        client_version: str = "0.1.0",
        capabilities: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform MCP initialize handshake and send the initialized notification.
        Returns the initialize result (server capabilities, serverInfo, etc.).
        """
        if capabilities is None:
            # We declare we understand tools/resources/prompts, which is typical.
            capabilities = {
                "tools": {},
                "resources": {},
                "prompts": {},
            }

        result = self.call(
            "initialize",
            {
                "protocolVersion": self.protocol_version,
                "capabilities": capabilities,
                "clientInfo": {
                    "name": client_name,
                    "version": client_version,
                },
            },
        )

        # Official spec uses `notifications/initialized` for this notification.
        # Some implementations accept just "initialized" — but this is the
        # spec'd version.
        self.notify("notifications/initialized")

        return result

    def _list_with_pagination(
        self,
        method: str,
        result_key: str,
    ) -> List[Dict[str, Any]]:
        """
        Generic helper for list endpoints that support cursor + nextCursor.
        e.g. tools/list, resources/list, prompts/list
        """
        items: List[Dict[str, Any]] = []
        cursor: Optional[str] = None

        while True:
            params = {}
            if cursor is not None:
                params["cursor"] = cursor

            result = self.call(method, params or None)
            batch = result.get(result_key, [])
            items.extend(batch)

            cursor = result.get("nextCursor")
            if not cursor:
                break

        return items

    def list_tools(self) -> List[Dict[str, Any]]:
        return self._list_with_pagination("tools/list", "tools")

    def list_resources(self) -> List[Dict[str, Any]]:
        return self._list_with_pagination("resources/list", "resources")

    def list_prompts(self) -> List[Dict[str, Any]]:
        return self._list_with_pagination("prompts/list", "prompts")


def _to_markdown_code_block(obj: Any, language: str = "json") -> str:
    return f"```{language}\n{json.dumps(obj, indent=2, sort_keys=True)}\n```"


def generate_mcp_documentation(
    endpoint: str,
    output_path: str = "mcp-server-docs.md",
    protocol_version: str = "2025-06-18",
) -> None:
    """
    Connects to an MCP server over HTTP JSON-RPC and writes a markdown
    documentation file describing its tools, resources, and prompts.
    """
    client = MCPClient(endpoint=endpoint, protocol_version=protocol_version)

    # 1. Initialize / handshake
    init_result = client.initialize()
    server_info = init_result.get("serverInfo", {})
    capabilities = init_result.get("capabilities", {})
    negotiated_proto = init_result.get("protocolVersion", protocol_version)

    now = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    md_lines: List[str] = []

    # Header
    md_lines.append("# MCP Server Documentation\n")
    md_lines.append(f"- **Endpoint:** `{endpoint}`")
    md_lines.append(f"- **Generated at (UTC):** `{now}`")
    md_lines.append(f"- **Negotiated protocolVersion:** `{negotiated_proto}`")

    if server_info:
        md_lines.append(f"- **Server name:** `{server_info.get('name', '?')}`")
        md_lines.append(f"- **Server version:** `{server_info.get('version', '?')}`")

    md_lines.append("\n---\n")

    # Capabilities
    md_lines.append("## Capabilities\n")
    if capabilities:
        md_lines.append(_to_markdown_code_block(capabilities))
    else:
        md_lines.append("_Server did not return capabilities in initialize result._\n")

    # 2. Tools
    md_lines.append("\n---\n")
    md_lines.append("## Tools\n")

    try:
        tools = client.list_tools()
    except Exception as exc:
        md_lines.append(
            f"_Failed to call `tools/list`: `{type(exc).__name__}: {exc}`_\n"
        )
        tools = []

    if not tools:
        md_lines.append("_No tools reported by server or call failed._\n")
    else:
        for tool in tools:
            name = tool.get("name", "unknown_tool")
            md_lines.append(f"\n### `{name}`\n")

            desc = tool.get("description")
            if desc:
                md_lines.append(desc + "\n")

            input_schema = tool.get("inputSchema")
            if input_schema:
                md_lines.append("**Input schema:**")
                md_lines.append(_to_markdown_code_block(input_schema))

            output_schema = tool.get("outputSchema")
            if output_schema:
                md_lines.append("**Output schema:**")
                md_lines.append(_to_markdown_code_block(output_schema))

            # Any extra fields
            extras = {
                k: v
                for k, v in tool.items()
                if k not in {"name", "description", "inputSchema", "outputSchema"}
            }
            if extras:
                md_lines.append("**Extra metadata:**")
                md_lines.append(_to_markdown_code_block(extras))

    # 3. Resources
    md_lines.append("\n---\n")
    md_lines.append("## Resources\n")

    try:
        resources = client.list_resources()
    except Exception as exc:
        md_lines.append(
            f"_Failed to call `resources/list`: `{type(exc).__name__}: {exc}`_\n"
        )
        resources = []

    if not resources:
        md_lines.append("_No resources reported by server or call failed._\n")
    else:
        for res in resources:
            uri = res.get("uri", "unknown://")
            md_lines.append(f"\n### `{uri}`\n")

            name = res.get("name")
            if name:
                md_lines.append(f"- **Name:** {name}")
            title = res.get("title")
            if title:
                md_lines.append(f"- **Title:** {title}")
            mime_type = res.get("mimeType")
            if mime_type:
                md_lines.append(f"- **MIME type:** `{mime_type}`")

            desc = res.get("description")
            if desc:
                md_lines.append(f"- **Description:** {desc}")

            # Extra resource fields
            extras = {
                k: v
                for k, v in res.items()
                if k not in {"uri", "name", "title", "description", "mimeType"}
            }
            if extras:
                md_lines.append("\n**Extra metadata:**")
                md_lines.append(_to_markdown_code_block(extras))

    # 4. Prompts
    md_lines.append("\n---\n")
    md_lines.append("## Prompts\n")

    try:
        prompts = client.list_prompts()
    except Exception as exc:
        md_lines.append(
            f"_Failed to call `prompts/list`: `{type(exc).__name__}: {exc}`_\n"
        )
        prompts = []

    if not prompts:
        md_lines.append("_No prompts reported by server or call failed._\n")
    else:
        for prompt in prompts:
            name = prompt.get("name", "unnamed_prompt")
            md_lines.append(f"\n### `{name}`\n")

            desc = prompt.get("description")
            if desc:
                md_lines.append(desc + "\n")

            args = prompt.get("arguments") or []
            if args:
                md_lines.append("**Arguments:**")
                for arg in args:
                    arg_name = arg.get("name", "arg")
                    arg_desc = arg.get("description", "")
                    required = arg.get("required", False)
                    md_lines.append(
                        f"- `{arg_name}` "
                        f"{'(required)' if required else '(optional)'}"
                        f"{' — ' + arg_desc if arg_desc else ''}"
                    )

            # Extra prompt fields
            extras = {
                k: v for k, v in prompt.items() if k not in {"name", "description", "arguments"}
            }
            if extras:
                md_lines.append("\n**Extra metadata:**")
                md_lines.append(_to_markdown_code_block(extras))

    # 5. Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"Documentation written to {output_path}")


if __name__ == "__main__":
    # Example: generate docs for your server
    generate_mcp_documentation(
        endpoint="https://dcvgyhis9s.us-east-1.awsapprunner.com/mcp",
        output_path="mcp-server-docs.md",
    )
