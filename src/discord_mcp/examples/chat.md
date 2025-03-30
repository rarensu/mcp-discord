## Demonstration of Discord Chat Workflow

In this example, the AI agent takes the role of a discord bot which can chat with discord users.  

### Prerequisite

Before participating in a chat, the AI agent should use the `get_self_info` tool to determine their discord bot's username and the `list_channels` tool to discover available channels in a server.

**Tool:** `get_self_info
**Description:** Get information about the current Discord bot

**Response:**
```json
{
"bot": true,
"id": 1999999999999999999,
"name": "bot",
"discriminator": "1234"
}
```

In this example, the agent's discord username is "bot".

**Tool:** `list_channels`
**Description:** Get a list of channels in a server

**Arguments:**
```json
{
"server_id": "1149634031793741824",
"filter_type": "text"
}
```

**Response:**
```
Server Channels (10):

Category: General (ID: 1234567890123456789)
  - general (ID: 1234567890123456790, Type: text)
  - announcements (ID: 1234567890123456791, Type: text)

Category: Community (ID: 1234567890123456792)
  - chat (ID: 1234567890123456793, Type: text)
  - help (ID: 1234567890123456794, Type: text)

Uncategorized Channels:
  - development (ID: 1149634102249660447, Type: text)
  - claude-bot-test (ID: 1355693528596091001, Type: text)
```

This gives the agent a map of all available text channels in the server, allowing it to identify where to look for messages or where to send responses based on the context.

### Step 1: Wait for a discord user to initiate the conversation

An AI agent wants to use a tool on the discord MCP server:

**Tool:** `await_mention`  
**Description:** Wait for the bot to be mentioned (e.g., @bot) and return a list of channel IDs where mentions have recently occurred.

**Response:**
```
Recent mentions in channel: 1234567890123456789
```

In this example, users are chatting with the bot in one channel. Remember the channel ID; we will need it for Step 4. 

### Step 2: Read the recent messages

An AI agent wants to use a tool on the discord MCP server:

**Tool:** `read_messages`  
**Description:** Read recent messages from a channel.

**Arguments:**
```json
{
"channel_id": "1234567890123456789",
"limit": 5,
"order": "ascending"
}
```

**Response:**
```json
Retrieved 5 messages:
user (2025-01-01T00:00:00.000000+00:00): a recent message.
Reactions: No reactions
user (2025-01-01T00:01:00.000000+00:00): a recent message.
Reactions: No reactions
user (2025-01-01T00:02:00.000000+00:00): @bot hello bot.
Reactions: No reactions
bot#1234 (2025-01-01T00:03:00.000000+00:00): Hello!
Reactions: No reactions
user (2025-01-01T00:04:00.000000+00:00): @bot what's the status of X?
Reactions: No reactions
```

In this example, the last message contains a mention (@bot). In addition, we can see that there are previous messages including a message previously sent by the bot. This must be part of an ongoing conversation.

### Step 3: Think and Act, as appropriate

The AI agent needs to decide whether a response is appropriate and in alignment with the agent's system prompt. 

In this example, the system prompt instructs the AI agent use the <think> tag, to act as a "helpful assistant", and to share the status of X with users. The agent has a tool to retrieve the status of X.

```
<think>
A user wants to know about the status of X. I might need to use a tool to retrieve the most up-to-date status of X.
</think>
```

The AI agent generates additional thoughts and actions (e.g., tool use) as appropriate, etc.

```
<think>
I now have enough information to respond. 
I am a helpful assistant, so I should respond if I am able. 
Since I am allowed to share the status of X with users, I can respond.
</think>
```

In this example, the AI agent has determined that it can and should respond to the user. 

### Step 4: Respond to the user

An AI agent wants to use a tool on the discord MCP server:

**Tool:** `send_message`  
**Description:** Send a message to a specific channel.

**Arguments:**

```
{
"channel_id": "1234567890123456789",
"content": "The status of X is: Y."
}
```

**Response:**
```
Message sent successfully. Message ID: 1354309524894384262
```

### Step 5: Repeat

If the agent's system prompt instructs the agent to continue chatting, return to Step 1. 

### Hints

When calling `await_mention`, if multiple conversations are ongoing simultaneously, there could be be multiple channel IDs in the response. The agent should pick any one and proceed to the next step. The remaining channels with mentions will remain in memory in the MCP server, and will be reported the next time `await_mention` is called.

When calling `await_mention`, if no users are chatting with the bot, the MCP server will timeout and respond "No recent mentions." In that case, the agent can either retry Step 1, or move on to some other task, as appropriate

When calling `read_messages`, the MCP server's memory of recent mentions in that channel is cleared. Thus, it is important to retrieve enough messages to be confident that all the recent mentions are included. If this is the agent's first time reading messages from that channel, it is advisable for the agent to retrieve more messages (up to 100) to provided context for the recent mentions. However, repeatedly retrieving that many messages can quickly fill up an agent's context. Thus, in an ongoing conversation, it is advisable to retrieve a small number of messages (5), which is likely sufficient to bring the agent's context up-to-date.

Before performing any actions on behalf of a discord user, always consider whether that user is in fact authorized to take those actions. 
