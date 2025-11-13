# alliance_mcp_server.py
import uuid
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ---------- Game State ----------


@dataclass
class Message:
    from_player: str
    to_player: str
    message: str
    round_number: int


@dataclass
class Player:
    name: str
    private_id: str
    score: int = 0
    supported_you_last_round: set = field(default_factory=set)


class GameState:
    def __init__(self):
        self.players_by_name: Dict[str, Player] = {}
        self.players_by_private: Dict[str, Player] = {}
        self.current_round: int = 1
        # For the *current* round: name -> name they support
        self.current_supports: Dict[str, str] = {}
        self.messages: List[Message] = []

    # ----- Core helpers -----

    def _ensure_player_name_unique(self, name: str):
        if name in self.players_by_name:
            raise ValueError(f"Player '{name}' already exists")

    def _get_player_by_private(self, private_id: str) -> Player:
        player = self.players_by_private.get(private_id)
        if not player:
            raise ValueError("Unknown private_id")
        return player

    def _get_player_by_name(self, name: str) -> Player:
        player = self.players_by_name.get(name)
        if not player:
            raise ValueError(f"Unknown player '{name}'")
        return player

    # ----- Tools implementation -----

    def register_player(self, player_name: str) -> Dict:
        self._ensure_player_name_unique(player_name)
        private_id = str(uuid.uuid4())
        player = Player(name=player_name, private_id=private_id)
        self.players_by_name[player_name] = player
        self.players_by_private[private_id] = player
        return self._build_status(player)

    def get_status(self, private_id: str) -> Dict:
        player = self._get_player_by_private(private_id)
        return self._build_status(player)

    def send_message(
        self,
        private_id: str,
        recipient_player_name: str,
        message: str,
    ) -> Dict:
        sender = self._get_player_by_private(private_id)
        recipient = self._get_player_by_name(recipient_player_name)

        self.messages.append(
            Message(
                from_player=sender.name,
                to_player=recipient.name,
                message=message,
                round_number=self.current_round,
            )
        )

        # Return sender's status
        return self._build_status(sender)

    def register_support(self, private_id: str, player_to_support: str) -> Dict:
        supporter = self._get_player_by_private(private_id)

        if player_to_support == supporter.name:
            raise ValueError("You cannot support yourself")

        self._get_player_by_name(player_to_support)  # validate exists

        self.current_supports[supporter.name] = player_to_support
        return self._build_status(supporter)

    # ----- Round logic (admin method) -----

    def advance_round(self) -> Dict:
        """
        Compute scores for the *current* round based on current_supports,
        then move to the next round. Returns a scoreboard for the round.
        """
        prev_round = self.current_round
        supports = dict(self.current_supports)  # copy

        # supporters_of[target] = [supporter1, supporter2, ...]
        supporters_of: Dict[str, List[str]] = {
            name: [] for name in self.players_by_name.keys()
        }
        for supporter, target in supports.items():
            if target in supporters_of:
                supporters_of[target].append(supporter)

        # Clear previous "supported_you_last_round"
        for p in self.players_by_name.values():
            p.supported_you_last_round = set()

        # 1. SUPPORTS RECEIVED: +1 per supporter
        for target, supporters in supporters_of.items():
            if supporters:
                self.players_by_name[target].score += len(supporters)
                self.players_by_name[target].supported_you_last_round = set(supporters)

        # 2. MUTUAL ALLIANCE BONUS: +2 if A supports B and B supports A
        for supporter, target in supports.items():
            # only count each pair once (supporter < target lexicographically)
            if supporter < target and supports.get(target) == supporter:
                self.players_by_name[supporter].score += 2
                self.players_by_name[target].score += 2

        # 3. UNRECIPROCATED PENALTY: -1 if you support someone who doesn't support you
        for supporter, target in supports.items():
            if supports.get(target) != supporter:
                self.players_by_name[supporter].score -= 1

        # 4. NO SUPPORT PENALTY: -1 if you don't support anyone
        for name, player in self.players_by_name.items():
            if name not in supports:
                player.score -= 1

        # Build scoreboard
        scores_list = []
        for name in sorted(self.players_by_name.keys()):
            player = self.players_by_name[name]
            scores_list.append(
                {
                    "player_name": name,
                    "score": player.score,
                    "supported": supports.get(name),
                    "supporters_this_round": supporters_of.get(name, []),
                }
            )

        # Advance round
        self.current_round += 1
        self.current_supports = {}

        return {
            "round_number": prev_round,
            "scores": scores_list,
        }

    # ----- Status builder -----

    def _build_status(self, player: Player) -> Dict:
        other_players = []
        for other_name, other in self.players_by_name.items():
            if other_name == player.name:
                continue
            other_players.append(
                {
                    "player_name": other.name,
                    "score": other.score,
                    "supported_you_last_round": other.name
                    in player.supported_you_last_round,
                }
            )

        messages_this_round = [
            {"from": m.from_player, "message": m.message}
            for m in self.messages
            if m.to_player == player.name and m.round_number == self.current_round
        ]

        return {
            "player_name": player.name,
            "private_id": player.private_id,
            "score": player.score,
            "round_number": self.current_round,
            "seconds_remaining": 0,  # no real-time clock in this test rig
            "other_players": other_players,
            "messages_received_this_round": messages_this_round,
        }


game_state = GameState()

# ---------- MCP Server (FastAPI + JSON-RPC over HTTP) ----------

app = FastAPI()


def _tool_def(name: str, description: str, input_schema: Dict) -> Dict:
    return {
        "name": name,
        "description": description,
        "inputSchema": input_schema,
    }


TOOLS = [
    _tool_def(
        "register_player",
        "Register your agent to join the Alliance negotiation game.",
        {
            "type": "object",
            "properties": {
                "player_name": {
                    "type": "string",
                    "description": "Your unique player name",
                }
            },
            "required": ["player_name"],
        },
    ),
    _tool_def(
        "get_status",
        "Get your current game status and the state of the game.",
        {
            "type": "object",
            "properties": {
                "private_id": {
                    "type": "string",
                    "description": "Your private ID from register_player()",
                }
            },
            "required": ["private_id"],
        },
    ),
    _tool_def(
        "send_message",
        "Send a private message to another player to negotiate alliances.",
        {
            "type": "object",
            "properties": {
                "private_id": {
                    "type": "string",
                    "description": "Your private ID",
                },
                "recipient_player_name": {
                    "type": "string",
                    "description": "Name of the player to send the message to",
                },
                "message": {
                    "type": "string",
                    "description": "Your message text",
                },
            },
            "required": ["private_id", "recipient_player_name", "message"],
        },
    ),
    _tool_def(
        "register_support",
        "Choose which player to support this round.",
        {
            "type": "object",
            "properties": {
                "private_id": {
                    "type": "string",
                    "description": "Your private ID",
                },
                "player_to_support": {
                    "type": "string",
                    "description": "Name of the player you want to support",
                },
            },
            "required": ["private_id", "player_to_support"],
        },
    ),
]


def _json_rpc_result(id_value, result_obj):
    return JSONResponse(
        {
            "jsonrpc": "2.0",
            "id": id_value,
            "result": result_obj,
        }
    )


def _json_rpc_error(id_value, code: int, message: str):
    return JSONResponse(
        {
            "jsonrpc": "2.0",
            "id": id_value,
            "error": {"code": code, "message": message},
        }
    )


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    payload = await request.json()
    method = payload.get("method")
    req_id = payload.get("id")
    params = payload.get("params", {}) or {}

    # Notifications (no id) – just acknowledge with 204
    if req_id is None and method.startswith("notifications/"):
        return JSONResponse(status_code=204, content=None)

    # ----- initialize -----
    if method == "initialize":
        # we mostly ignore requested protocolVersion/capabilities
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {
                    "listChanged": False,
                }
            },
            "serverInfo": {
                "name": "Local Alliance Game MCP Server",
                "version": "0.1.0",
            },
        }
        return _json_rpc_result(req_id, result)

    # ----- tools/list -----
    if method == "tools/list":
        result = {
            "tools": TOOLS,
            "nextCursor": None,
        }
        return _json_rpc_result(req_id, result)

    # ----- tools/call -----
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}

        try:
            if name == "register_player":
                res = game_state.register_player(arguments["player_name"])
            elif name == "get_status":
                res = game_state.get_status(arguments["private_id"])
            elif name == "send_message":
                res = game_state.send_message(
                    arguments["private_id"],
                    arguments["recipient_player_name"],
                    arguments["message"],
                )
            elif name == "register_support":
                res = game_state.register_support(
                    arguments["private_id"],
                    arguments["player_to_support"],
                )
            else:
                return _json_rpc_error(
                    req_id, -32602, f"Unknown tool: {name}"
                )

            content = [
                {"type": "json", "json": res},
                {
                    "type": "text",
                    "text": json.dumps(res, indent=2),
                },
            ]
            return _json_rpc_result(
                req_id,
                {
                    "content": content,
                    "isError": False,
                },
            )
        except Exception as e:
            # Tool execution error – still a valid result with isError = True
            content = [{"type": "text", "text": f"Error: {e}"}]
            return _json_rpc_result(
                req_id,
                {
                    "content": content,
                    "isError": True,
                },
            )

    # ----- Admin method: game/advance_round -----
    if method == "game/advance_round":
        scoreboard = game_state.advance_round()
        return _json_rpc_result(req_id, scoreboard)

    # Unknown method
    return _json_rpc_error(req_id, -32601, f"Method not found: {method}")


if __name__ == "__main__":
    # Run as: python alliance_mcp_server.py
    import uvicorn

    uvicorn.run("alliance_mcp_server:app", host="0.0.0.0", port=8000, reload=True)
