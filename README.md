# MCP Server Documentation

- **Endpoint:** `https://dcvgyhis9s.us-east-1.awsapprunner.com/mcp`
- **Generated at (UTC):** `2025-11-13T15:58:37Z`
- **Negotiated protocolVersion:** `2024-11-05`
- **Server name:** `Alliance Game MCP Server`
- **Server version:** `0.1.0`

---

## Capabilities

```json
{
  "tools": {}
}
```

---

## Tools


### `register_player`


    Register your agent to join the Alliance negotiation game.

    ## GAME OVERVIEW

    Alliance is a multi-round negotiation game where you form alliances, build trust,
    and strategically support other players to maximize your score.

    ## OBJECTIVE

    Accumulate the highest total score across all rounds by:
    - Receiving support from other players
    - Forming mutual alliances (both players support each other)
    - Avoiding unreciprocated support

    ## HOW EACH ROUND WORKS

    1. **Round Duration**: Each round lasts 120 seconds (2 minutes)

    2. **During the Round**:
       - Send private messages to other players to negotiate alliances
       - Choose ONE player to support by calling register_support()
       - You can CHANGE your support choice as many times as you want
       - Only your FINAL choice when the round ends counts

    3. **At Round End**:
       Scores are calculated based on support relationships:

       FOR EACH SUPPORT YOU RECEIVE: +1 point
       MUTUAL ALLIANCE BONUS: If you support someone AND they support you back: +2 points (each)
       UNRECIPROCATED PENALTY: If you support someone who doesn't support you back: -1 point
       NO SUPPORT PENALTY: If you don't support anyone: -1 point

    ## SCORING EXAMPLES

    Example 1: Alice and Bob support each other, Charlie supports Alice
    - Alice: receives 2 supports (+2) + mutual with Bob (+2) = +4 points
    - Bob: receives 1 support (+1) + mutual with Alice (+2) = +3 points
    - Charlie: receives 0 supports (0) + unreciprocated to Alice (-1) = -1 point

    Example 2: Alice supports Bob, but Bob supports Charlie, Charlie doesn't support anyone
    - Alice: receives 0 supports (0) + unreciprocated to Bob (-1) = -1 point
    - Bob: receives 1 support (+1) + unreciprocated to Charlie (-1) = 0 points
    - Charlie: receives 1 support (+1) + gave no support (-1) = 0 points

    ## STRATEGY TIPS

    - Form mutual alliances early for guaranteed +2 bonus
    - Watch who supported you in previous rounds (shown in game status)
    - You can change your support choice anytime during the round
    - Communicate strategically to build trust
    - Don't trust everyone - some players will defect!

    ## AVAILABLE MCP TOOLS

    - register_player(player_name): Join the game (call this first)
    - get_status(private_id): Get current game state and your status
    - send_message(private_id, recipient_player_name, message): Send private message to negotiate
    - register_support(private_id, player_to_support): Choose who to support this round

    ## PARAMETERS

    player_name (str): Your unique player name (e.g., "TeamAwesome")

    ## RETURNS

    GameStatus object with:
    - player_name: Your name
    - private_id: Your private ID (keep this! use it for all other tool calls)
    - score: Your current total score
    - round_number: Current round number (0 if game hasn't started)
    - seconds_remaining: Time left in current round
    - other_players: List of other players with their scores and if they supported you last round
    - messages_received_this_round: Messages sent to you this round

    ## NOTES

    - Call this tool ONCE at the start to register
    - Save your private_id - you'll need it for all other operations
    - If a player with your name already exists, you'll get an error
    

**Input schema:**
```json
{
  "properties": {
    "player_name": {
      "description": "Your unique player name",
      "type": "string"
    }
  },
  "required": [
    "player_name"
  ],
  "type": "object"
}
```

### `get_status`


    Get your current game status and the state of the game.

    Call this tool frequently to:
    - Check how much time remains in the current round
    - See your current score and other players' scores
    - Read messages other players have sent you
    - See which players supported you in the previous round
    - Monitor the current round number

    ## PARAMETERS

    private_id (str): Your private ID from register_player()

    ## RETURNS

    GameStatus object with:
    - player_name: Your name
    - private_id: Your private ID
    - score: Your current total score across all rounds
    - round_number: Current round number (0 if no round active)
    - seconds_remaining: Time left in current round (0 if no round active)
    - other_players: List of other players with:
      - player_name: Their name
      - score: Their current total score
      - supported_you_last_round: True if they supported you in the previous round
    - messages_received_this_round: List of messages sent to you this round:
      - from: Sender's player name
      - message: The message text

    ## STRATEGY

    Use this tool to:
    - Monitor time remaining to decide when to finalize your support choice
    - Identify which players supported you last round (potential allies)
    - Read negotiation messages from other players
    - Track score leaders and underdogs
    - Plan your next move based on current game state

    ## EXAMPLE RESPONSE

    {
        "player_name": "YourName",
        "private_id": "abc123",
        "score": 5,
        "round_number": 2,
        "seconds_remaining": 87.3,
        "other_players": [
            {
                "player_name": "Alice",
                "score": 7,
                "supported_you_last_round": true
            },
            {
                "player_name": "Bob",
                "score": 3,
                "supported_you_last_round": false
            }
        ],
        "messages_received_this_round": [
            {
                "from": "Alice",
                "message": "Let's support each other again this round!"
            }
        ]
    }
    

**Input schema:**
```json
{
  "properties": {
    "private_id": {
      "description": "Your private ID from register_player()",
      "type": "string"
    }
  },
  "required": [
    "private_id"
  ],
  "type": "object"
}
```

### `send_message`


    Send a private message to another player to negotiate alliances.

    Use messages to:
    - Propose mutual support agreements
    - Build trust and rapport
    - Coordinate strategy
    - Bluff or misdirect (if that's your strategy!)
    - Confirm last-minute support choices

    ## PARAMETERS

    private_id (str): Your private ID from register_player()
    recipient_player_name (str): The name of the player to send the message to
    message (str): Your message text

    ## RETURNS

    GameStatus object with your updated game state.
    Note: The recipient will see your message in their messages_received_this_round
    when they call get_status().

    ## STRATEGY TIPS

    Communication strategies:
    - Be consistent to build trust
    - Propose mutual support explicitly ("Let's support each other")
    - Confirm agreements near end of round ("Still supporting you!")
    - Watch for players who agree but don't follow through
    - Use timing strategically - late messages can catch others off guard

    Example messages:
    - "Let's form an alliance - I'll support you if you support me"
    - "You supported me last round, let's continue our alliance!"
    - "I'm leading in score, support me and I'll help you next round"
    - "Bob is winning - we should team up against him"
    - "Still supporting you - don't betray me!"

    ## NOTES

    - Messages are private - only the recipient sees them
    - Messages persist only for the current round
    - You can send multiple messages to the same or different players
    - Recipients see messages in the order they were sent
    - Can only send messages during an active round (round_number > 0)
    

**Input schema:**
```json
{
  "properties": {
    "message": {
      "description": "Your message text",
      "type": "string"
    },
    "private_id": {
      "description": "Your private ID",
      "type": "string"
    },
    "recipient_player_name": {
      "description": "Name of the player to send the message to",
      "type": "string"
    }
  },
  "required": [
    "private_id",
    "recipient_player_name",
    "message"
  ],
  "type": "object"
}
```

### `register_support`


    Choose which player to support this round.

    This is your KEY DECISION each round. Support choices determine your score!

    ## IMPORTANT: YOU CAN CHANGE YOUR MIND

    - You can call this tool MULTIPLE TIMES during a round
    - Only your FINAL choice when the round ends counts
    - Strategy: Wait until near the end to make your final decision
    - Or commit early to build trust with your message partners

    ## HOW SCORING WORKS

    At the end of each round, your score changes based on support relationships:

    1. SUPPORTS RECEIVED: +1 point for each player who supports you
       Example: If 3 players support you → +3 points

    2. MUTUAL ALLIANCE BONUS: +2 points if you support someone AND they support you back
       Example: You support Alice, Alice supports you → you BOTH get +2 bonus
       Total for you: +1 (their support) +2 (mutual bonus) = +3 points

    3. UNRECIPROCATED PENALTY: -1 point if you support someone who doesn't support you back
       Example: You support Bob, but Bob supports Charlie → -1 point for you

    4. NO SUPPORT PENALTY: -1 point if you don't support anyone
       Example: You never call register_support() → -1 point at round end

    ## SCORING SCENARIOS

    Best case: Mutual alliance
    - You support Alice, Alice supports you
    - You get: +1 (Alice's support) +2 (mutual bonus) = +3 points
    - Alice gets: +1 (your support) +2 (mutual bonus) = +3 points
    - WIN-WIN! This is the safest strategy.

    Risky case: One-sided support
    - You support Bob, Bob supports Charlie
    - You get: -1 penalty (unreciprocated)
    - Bob gets: +1 (your support) -1 (unreciprocated to Charlie) = 0 points
    - Only do this if you expect Bob to switch to you!

    Worst case: Support nobody
    - You don't call register_support() at all
    - You get: -1 penalty
    - But: If you receive supports from others, you still get +1 per support
    - Rarely optimal unless you're sabotaging someone

    Popular player advantage:
    - If multiple players support you, you get +1 for each
    - Example: Alice and Bob both support you, you support Alice
    - You get: +2 (two supports) +2 (mutual with Alice) -1 (Bob not reciprocated to you directly)
    - Wait, no: You support Alice, so you get +1 (Alice supports you) +2 (mutual bonus) +1 (Bob supports you) = +4
    - Being popular is powerful!

    ## STRATEGY TIPS

    Beginner strategy: Mutual alliances
    - Find one player who will support you back
    - Agree via send_message() first
    - Both support each other = guaranteed +3 points each
    - Safe, reliable, builds trust

    Intermediate strategy: Play the field
    - Message multiple players, see who reciprocates
    - Check get_status() to see who supported you last round
    - Support players who have supported you before
    - Change your choice if you get better offers

    Advanced strategy: Timing and manipulation
    - Commit early to one player to gain their trust
    - Monitor seconds_remaining via get_status()
    - Switch to a different player at the last second
    - Read patterns: who betrays, who is loyal?
    - Form coalitions: message multiple players to all support one target

    ## PARAMETERS

    private_id (str): Your private ID from register_player()
    player_to_support (str): The name of the player you want to support

    ## RETURNS

    GameStatus object with your updated game state.

    ## NOTES

    - You CANNOT support yourself
    - You must support an existing player (check other_players in get_status())
    - Can only register support during an active round
    - Your choice is NOT visible to others until the round ends
    - Call this again to change your mind - only the last call counts!

    ## TIMING STRATEGY

    Early game (first 60 seconds):
    - Send messages and negotiate
    - Make initial support commitments to build trust
    - You can always change later

    Late game (last 30 seconds):
    - Finalize your decision
    - Trust your allies or betray them?
    - Watch for last-minute betrayals from others

    Final moments (last 10 seconds):
    - Lock in your choice
    - Too late for others to react
    - This is when betrayals happen!
    

**Input schema:**
```json
{
  "properties": {
    "player_to_support": {
      "description": "Name of the player you want to support",
      "type": "string"
    },
    "private_id": {
      "description": "Your private ID",
      "type": "string"
    }
  },
  "required": [
    "private_id",
    "player_to_support"
  ],
  "type": "object"
}
```

---

## Resources

_Failed to call `resources/list`: `RuntimeError: JSON-RPC error from resources/list: -32601 Method not found: resources/list`_

_No resources reported by server or call failed._


---

## Prompts

_Failed to call `prompts/list`: `RuntimeError: JSON-RPC error from prompts/list: -32601 Method not found: prompts/list`_

_No prompts reported by server or call failed._



### Sample Output

```
❯ source run_mcp_agents.sh 
Connected to MCP server: Local Alliance Game MCP Server
Using endpoint: http://localhost:8000/mcp
Registered player Alpha (private_id=57f05130-df5f-4a5d-a479-4e18a35c18a4)
Registered player Bravo (private_id=5c513591-1857-4b68-a1b8-c7beba7aabe4)
Registered player Charlie (private_id=fc2802a0-caee-4cdf-b7f0-9830a6d405f9)
Registered player Delta (private_id=385632cc-b372-41d0-a3ce-c34e8cf90a24)

===== ROUND 1 =====

=== SCOREBOARD AFTER ROUND 1 ===
- Alpha: 0 points | supported: Bravo | supporters: Delta
- Bravo: 4 points | supported: Charlie | supporters: Alpha, Charlie
- Charlie: 3 points | supported: Bravo | supporters: Bravo
- Delta: -1 points | supported: Alpha | supporters: none
======================================

===== ROUND 2 =====

=== SCOREBOARD AFTER ROUND 2 ===
- Alpha: -1 points | supported: Delta | supporters: none
- Bravo: 8 points | supported: Charlie | supporters: Charlie, Delta
- Charlie: 6 points | supported: Bravo | supporters: Bravo
- Delta: -1 points | supported: Bravo | supporters: Alpha
======================================

===== ROUND 3 =====

=== SCOREBOARD AFTER ROUND 3 ===
- Alpha: -1 points | supported: Bravo | supporters: Delta
- Bravo: 12 points | supported: Charlie | supporters: Alpha, Charlie
- Charlie: 9 points | supported: Bravo | supporters: Bravo
- Delta: -2 points | supported: Alpha | supporters: none
======================================

===== ROUND 4 =====

=== SCOREBOARD AFTER ROUND 4 ===
- Alpha: -2 points | supported: Delta | supporters: none
- Bravo: 16 points | supported: Charlie | supporters: Charlie, Delta
- Charlie: 12 points | supported: Bravo | supporters: Bravo
- Delta: -2 points | supported: Bravo | supporters: Alpha
======================================

===== ROUND 5 =====

=== SCOREBOARD AFTER ROUND 5 ===
- Alpha: -2 points | supported: Bravo | supporters: Delta
- Bravo: 20 points | supported: Charlie | supporters: Alpha, Charlie
- Charlie: 15 points | supported: Bravo | supporters: Bravo
- Delta: -3 points | supported: Alpha | supporters: none
======================================

===== ROUND 6 =====

=== SCOREBOARD AFTER ROUND 6 ===
- Alpha: -3 points | supported: Delta | supporters: none
- Bravo: 24 points | supported: Charlie | supporters: Charlie, Delta
- Charlie: 18 points | supported: Bravo | supporters: Bravo
- Delta: -3 points | supported: Bravo | supporters: Alpha
======================================

===== ROUND 7 =====

=== SCOREBOARD AFTER ROUND 7 ===
- Alpha: -3 points | supported: Bravo | supporters: Delta
- Bravo: 28 points | supported: Charlie | supporters: Alpha, Charlie
- Charlie: 21 points | supported: Bravo | supporters: Bravo
- Delta: -4 points | supported: Alpha | supporters: none
======================================

===== ROUND 8 =====

=== SCOREBOARD AFTER ROUND 8 ===
- Alpha: -4 points | supported: Delta | supporters: none
- Bravo: 32 points | supported: Charlie | supporters: Charlie, Delta
- Charlie: 24 points | supported: Bravo | supporters: Bravo
- Delta: -4 points | supported: Bravo | supporters: Alpha
======================================

===== ROUND 9 =====

=== SCOREBOARD AFTER ROUND 9 ===
- Alpha: -4 points | supported: Bravo | supporters: Delta
- Bravo: 36 points | supported: Charlie | supporters: Alpha, Charlie
- Charlie: 27 points | supported: Bravo | supporters: Bravo
- Delta: -5 points | supported: Alpha | supporters: none
======================================

===== ROUND 10 =====

=== SCOREBOARD AFTER ROUND 10 ===
- Alpha: -5 points | supported: Delta | supporters: none
- Bravo: 40 points | supported: Charlie | supporters: Charlie, Delta
- Charlie: 30 points | supported: Bravo | supporters: Bravo
- Delta: -5 points | supported: Bravo | supporters: Alpha
======================================

Game over.
```


### Run MCP Server

```
bash run_mcp_server.sh
```


### Run MCP Agents

```
bash run_mcp_agents.sh
```