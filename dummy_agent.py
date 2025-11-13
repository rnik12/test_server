# dummy_agent.py
import os
import random
import requests
from typing import Any, Dict, List, Optional


SERVER_URL = os.getenv("ALLIANCE_MCP_SERVER", "http://localhost:8000/mcp")


class MCPClient:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self._id_counter = 0

    def _next_id(self) -> int:
        self._id_counter += 1
        return self._id_counter

    def _post(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        resp = requests.post(self.endpoint, json=payload, timeout=30)
        resp.raise_for_status()
        if not resp.content:
            return None
        return resp.json()

    def initialize(self) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "dummy-agent", "version": "0.1.0"},
            },
        }
        data = self._post(payload)
        return data["result"]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        data = self._post(payload)
        result = data["result"]

        # Prefer JSON content if present
        for item in result.get("content", []):
            if item.get("type") == "json":
                return item["json"]

        # Fallback: parse JSON from text if possible
        for item in result.get("content", []):
            if item.get("type") == "text":
                text = item.get("text", "")
                try:
                    return json.loads(text)
                except Exception:
                    return {"raw_text": text}

        return {}

    def call_method(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict:
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params is not None:
            payload["params"] = params
        data = self._post(payload)
        return data["result"]


class Participant:
    """
    Minimal participant wrapper.
    You can later replace choose_support() with a call to an OpenAI model.
    """

    def __init__(self, name: str, client: MCPClient):
        self.name = name
        self.client = client
        self.private_id: Optional[str] = None
        self.score: int = 0

    def register(self):
        result = self.client.call_tool("register_player", {"player_name": self.name})
        self.private_id = result["private_id"]
        self.score = result["score"]
        print(f"Registered player {self.name} (private_id={self.private_id})")

    def get_status(self) -> Dict[str, Any]:
        if not self.private_id:
            raise RuntimeError("Not registered")
        result = self.client.call_tool("get_status", {"private_id": self.private_id})
        self.score = result["score"]
        return result

    def choose_support(self, status: Dict[str, Any]) -> Optional[str]:
        """
        Dumb strategy:
        - If anyone supported us last round, support the highest-scoring one.
        - Otherwise, support the highest-scoring other player.
        Replace this with a call to an OpenAI model if you like.
        """
        others: List[Dict[str, Any]] = status.get("other_players", [])
        if not others:
            return None

        # First try: allies from last round
        allies = [
            p for p in others if p.get("supported_you_last_round")
        ]
        candidates = allies or others

        # Pick highest score, break ties randomly
        max_score = max(p["score"] for p in candidates)
        best = [p for p in candidates if p["score"] == max_score]
        target = random.choice(best)["player_name"]
        return target

    def play_turn(self):
        status = self.get_status()
        target = self.choose_support(status)
        if target is None:
            return

        # Optionally send a negotiation message
        self.client.call_tool(
            "send_message",
            {
                "private_id": self.private_id,
                "recipient_player_name": target,
                "message": f"Let's mutually support each other this round. - {self.name}",
            },
        )

        # Register support choice
        self.client.call_tool(
            "register_support",
            {
                "private_id": self.private_id,
                "player_to_support": target,
            },
        )


def print_scoreboard(board: Dict[str, Any]):
    round_number = board["round_number"]
    print(f"\n=== SCOREBOARD AFTER ROUND {round_number} ===")
    for entry in board["scores"]:
        supported = entry.get("supported")
        supporters = entry.get("supporters_this_round", [])
        supporters_str = ", ".join(supporters) if supporters else "none"
        print(
            f"- {entry['player_name']}: {entry['score']} points | "
            f"supported: {supported or 'no one'} | "
            f"supporters: {supporters_str}"
        )
    print("======================================")


def main():
    client = MCPClient(SERVER_URL)
    init_info = client.initialize()
    server_name = init_info.get("serverInfo", {}).get("name", "unknown")
    print(f"Connected to MCP server: {server_name}")
    print(f"Using endpoint: {SERVER_URL}")

    # Create 4 participants
    names = ["Alpha", "Bravo", "Charlie", "Delta"]
    participants = [Participant(name, client) for name in names]

    # Register all players
    for p in participants:
        p.register()

    # Play 10 rounds
    NUM_ROUNDS = 10
    for r in range(1, NUM_ROUNDS + 1):
        print(f"\n===== ROUND {r} =====")
        # Each participant takes an action
        for p in participants:
            p.play_turn()

        # Admin: advance round and print scoreboard
        board = client.call_method("game/advance_round", {})
        print_scoreboard(board)

    print("\nGame over.")


if __name__ == "__main__":
    main()
