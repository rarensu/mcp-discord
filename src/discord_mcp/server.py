import os
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from functools import wraps
import json
import discord
from discord.ext import commands
from mcp.server import Server
from mcp.types import Tool, TextContent, Resource, EmptyResult
from mcp.server.stdio import stdio_server
from pydantic import AnyUrl
from pathlib import Path
# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("discord-mcp-server")

fixed_resources = {
    "examples/chat.md": {
        "name": "Chat Example",
        "description": "An example of using messaging tools to chat with discord users.",
    },
    "examples/moderation.md": {
        "name": "Moderation Example",
        "description": "An example of using management tools to moderate discord users.",
    }
}

# Discord bot setup
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_TIMEOUT = os.getenv("DISCORD_TIMEOUT")
discord_timeout = float(DISCORD_TIMEOUT) if DISCORD_TIMEOUT else 60.0

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is required")

# Initialize Discord bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Initialize MCP server
app = Server("discord-server")

# Store Discord client reference
discord_client = None

# Add a global set to store recent mentions
recent_mentions = set()

@bot.event
async def on_ready():
    global discord_client
    discord_client = bot
    logger.info(f"Logged in as {bot.user.name}")

@bot.event
async def on_message(message):
    global recent_mentions
    if message.author == bot.user:
        return

    # Check if the bot is mentioned
    if f"<@{bot.user.id}>" in message.content:
        # Add the channel ID to recent_mentions
        recent_mentions.add(message.channel.id)

# Helper function to ensure Discord client is ready
def require_discord_client(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not discord_client:
            raise RuntimeError("Discord client not ready")
        return await func(*args, **kwargs)
    return wrapper

@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available Discord tools."""
    return [
        # Server Information Tools
        Tool(
            name="get_server_info",
            description="Get information about a Discord server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server (guild) ID"
                    }
                },
                "required": ["server_id"]
            }
        ),
        Tool(
            name="list_channels",
            description="Get a list of channels in a server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server (guild) ID"
                    },
                    "filter_type": {
                        "type": "string",
                        "description": "Optional filter for channel type (text, voice, category, all)",
                        "enum": ["text", "voice", "category", "all"]
                    }
                },
                "required": ["server_id"]
            }
        ),
        Tool(
            name="list_members",
            description="Get a list of members in a server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server (guild) ID"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of members to fetch",
                        "minimum": 1,
                        "maximum": 1000
                    }
                },
                "required": ["server_id"]
            }
        ),

        # Role Management Tools
        Tool(
            name="add_role",
            description="Add a role to a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User to add role to"
                    },
                    "role_id": {
                        "type": "string",
                        "description": "Role ID to add"
                    }
                },
                "required": ["server_id", "user_id", "role_id"]
            }
        ),
        Tool(
            name="remove_role",
            description="Remove a role from a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User to remove role from"
                    },
                    "role_id": {
                        "type": "string",
                        "description": "Role ID to remove"
                    }
                },
                "required": ["server_id", "user_id", "role_id"]
            }
        ),

        # Channel Management Tools
        Tool(
            name="create_text_channel",
            description="Create a new text channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Channel name"
                    },
                    "category_id": {
                        "type": "string",
                        "description": "Optional category ID to place channel in"
                    },
                    "topic": {
                        "type": "string",
                        "description": "Optional channel topic"
                    }
                },
                "required": ["server_id", "name"]
            }
        ),
        Tool(
            name="delete_channel",
            description="Delete a channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "ID of channel to delete"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for deletion"
                    }
                },
                "required": ["channel_id"]
            }
        ),

        # Message Reaction Tools
        Tool(
            name="add_reaction",
            description="Add a reaction to a message",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel containing the message"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message to react to"
                    },
                    "emoji": {
                        "type": "string",
                        "description": "Emoji to react with (Unicode or custom emoji ID)"
                    }
                },
                "required": ["channel_id", "message_id", "emoji"]
            }
        ),
        Tool(
            name="add_multiple_reactions",
            description="Add multiple reactions to a message",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel containing the message"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message to react to"
                    },
                    "emojis": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "Emoji to react with (Unicode or custom emoji ID)"
                        },
                        "description": "List of emojis to add as reactions"
                    }
                },
                "required": ["channel_id", "message_id", "emojis"]
            }
        ),
        Tool(
            name="remove_reaction",
            description="Remove a reaction from a message",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel containing the message"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message to remove reaction from"
                    },
                    "emoji": {
                        "type": "string",
                        "description": "Emoji to remove (Unicode or custom emoji ID)"
                    }
                },
                "required": ["channel_id", "message_id", "emoji"]
            }
        ),
        Tool(
            name="send_message",
            description="Send a message to a specific channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Discord channel ID"
                    },
                    "content": {
                        "type": "string",
                        "description": "Message content"
                    }
                },
                "required": ["channel_id", "content"]
            }
        ),
        Tool(
            name="read_messages",
            description="Read recent messages from a channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Discord channel ID"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Number of messages to fetch (max 100)",
                        "minimum": 1,
                        "maximum": 100
                    },
                    "order": {
                        "type": "string",
                        "description": "Order of messages (ascending or descending)",
                        "enum": ["ascending", "descending"]
                    }
                },
                "required": ["channel_id"]
            }
        ),
        Tool(
            name="get_user_info",
            description="Get information about a Discord user",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "Discord user ID"
                    }
                },
                "required": ["user_id"]
            }
        ),
        Tool(
            name="get_self_info",
            description="Get information about the current Discord bot",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="moderate_message",
            description="Delete a message and optionally timeout the user",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel ID containing the message"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "ID of message to moderate"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for moderation"
                    },
                    "timeout_minutes": {
                        "type": "number",
                        "description": "Optional timeout duration in minutes",
                        "minimum": 0,
                        "maximum": 40320  # Max 4 weeks
                    }
                },
                "required": ["channel_id", "message_id", "reason"]
            }
        ),
        Tool(
            name="await_mention",
            description="Wait for the bot to be mentioned and return a list of channel IDs where mentions have recently occurred",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

@app.call_tool()
@require_discord_client
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    global recent_mentions

    if name == "send_message":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.send(arguments["content"])
        return [TextContent(
            type="text",
            text=f"Message sent successfully. Message ID: {message.id}"
        )]

    elif name == "read_messages":
        channel_id = int(arguments["channel_id"])
        # Remove the channel ID from recent_mentions
        recent_mentions.discard(channel_id)

        # If recent_mentions is empty, allow await_mention to wait
        if not recent_mentions:
            recent_mentions.clear()

        # ...existing code for reading messages...
        channel = await discord_client.fetch_channel(channel_id)
        limit = min(int(arguments.get("limit", 10)), 100)
        order = arguments.get("order", "descending")
        fetch_users = arguments.get("fetch_reaction_users", False)  # Only fetch users if explicitly requested
        messages = []
        async for message in channel.history(limit=limit):
            reaction_data = []
            for reaction in message.reactions:
                emoji_str = str(reaction.emoji.name) if hasattr(reaction.emoji, 'name') and reaction.emoji.name else str(reaction.emoji.id) if hasattr(reaction.emoji, 'id') else str(reaction.emoji)
                reaction_info = {
                    "emoji": emoji_str,
                    "count": reaction.count
                }
                logger.info(f"Emoji: {emoji_str}")
                reaction_data.append(reaction_info)
            # Replace user ID with username in message content
            content = message.content.replace(f"<@{discord_client.user.id}>", f"@{discord_client.user.name}")
            messages.append({
                "id": str(message.id),
                "author": str(message.author),
                "content": content,
                "timestamp": message.created_at.isoformat(),
                "reactions": reaction_data
            })
        if order == "ascending":
                messages.reverse()
        return [TextContent(
            type="text",
            text=f"Retrieved {len(messages)} messages:\n\n" +
                 "\n".join([
                     f"{m['author']} ({m['timestamp']}): {m['content']}\n" +
                     f"Reactions: {', '.join([f'{r['emoji']}({r['count']})' for r in m['reactions']]) if m['reactions'] else 'No reactions'}"
                     for m in messages
                 ])
        )]
    
    elif name == "get_self_info":
        content = json.dumps({
            "bot":discord_client.user.bot,
            "id":discord_client.user.id,
            "name":discord_client.user.name,
            "discriminator": discord_client.user.discriminator
            },indent=0)
        return [TextContent(
            type="text",
            text=content
        )]

    elif name == "get_user_info":
        user = await discord_client.fetch_user(int(arguments["user_id"]))
        user_info = {
            "id": str(user.id),
            "name": user.name,
            "discriminator": user.discriminator,
            "bot": user.bot,
            "created_at": user.created_at.isoformat()
        }
        return [TextContent(
            type="text",
            text=f"User information:\n" + 
                 f"Name: {user_info['name']}#{user_info['discriminator']}\n" +
                 f"ID: {user_info['id']}\n" +
                 f"Bot: {user_info['bot']}\n" +
                 f"Created: {user_info['created_at']}"
        )]

    elif name == "moderate_message":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        
        # Delete the message
        await message.delete(reason=arguments["reason"])
        
        # Handle timeout if specified
        if "timeout_minutes" in arguments and arguments["timeout_minutes"] > 0:
            if isinstance(message.author, discord.Member):
                duration = discord.utils.utcnow() + datetime.timedelta(
                    minutes=arguments["timeout_minutes"]
                )
                await message.author.timeout(
                    duration,
                    reason=arguments["reason"]
                )
                return [TextContent(
                    type="text",
                    text=f"Message deleted and user timed out for {arguments['timeout_minutes']} minutes."
                )]
        
        return [TextContent(
            type="text",
            text="Message deleted successfully."
        )]

    # Server Information Tools
    elif name == "get_server_info":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        info = {
            "name": guild.name,
            "id": str(guild.id),
            "owner_id": str(guild.owner_id),
            "member_count": guild.member_count,
            "created_at": guild.created_at.isoformat(),
            "description": guild.description,
            "premium_tier": guild.premium_tier,
            "explicit_content_filter": str(guild.explicit_content_filter)
        }
        return [TextContent(
            type="text",
            text=f"Server Information:\n" + "\n".join(f"{k}: {v}" for k, v in info.items())
        )]
        
    elif name == "list_channels":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        channels = await guild.fetch_channels()
        
        # Filter channels based on type if specified
        filter_type = arguments.get("filter_type", "all")
        
        filtered_channels = []
        for channel in channels:
            if filter_type == "all":
                filtered_channels.append(channel)
            elif filter_type == "text" and isinstance(channel, discord.TextChannel):
                filtered_channels.append(channel)
            elif filter_type == "voice" and isinstance(channel, discord.VoiceChannel):
                filtered_channels.append(channel)
            elif filter_type == "category" and isinstance(channel, discord.CategoryChannel):
                filtered_channels.append(channel)
        
        # Organize channels by category
        categories = {}
        uncategorized = []
        
        for channel in filtered_channels:
            if isinstance(channel, discord.CategoryChannel):
                categories[channel.id] = {
                    "name": channel.name,
                    "id": str(channel.id),
                    "channels": []
                }
        
        for channel in filtered_channels:
            if not isinstance(channel, discord.CategoryChannel):
                channel_info = {
                    "name": channel.name,
                    "id": str(channel.id),
                    "type": "text" if isinstance(channel, discord.TextChannel) else "voice" if isinstance(channel, discord.VoiceChannel) else "unknown"
                }
                
                if channel.category_id and channel.category_id in categories:
                    categories[channel.category_id]["channels"].append(channel_info)
                else:
                    uncategorized.append(channel_info)
        
        # Format the output
        output = f"Server Channels ({len(filtered_channels)}):\n\n"
        
        # Add categories with their channels
        for category_id, category_data in categories.items():
            output += f"Category: {category_data['name']} (ID: {category_data['id']})\n"
            if category_data["channels"]:
                for channel in category_data["channels"]:
                    output += f"  - {channel['name']} (ID: {channel['id']}, Type: {channel['type']})\n"
            else:
                output += "  (No channels in this category)\n"
            output += "\n"
        
        # Add uncategorized channels
        if uncategorized:
            output += "Uncategorized Channels:\n"
            for channel in uncategorized:
                output += f"  - {channel['name']} (ID: {channel['id']}, Type: {channel['type']})\n"
        
        return [TextContent(
            type="text",
            text=output
        )]

    elif name == "list_members":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        limit = min(int(arguments.get("limit", 100)), 1000)
        
        members = []
        async for member in guild.fetch_members(limit=limit):
            members.append({
                "id": str(member.id),
                "name": member.name,
                "nick": member.nick,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                "roles": [str(role.id) for role in member.roles[1:]]  # Skip @everyone
            })
        
        return [TextContent(
            type="text",
            text=f"Server Members ({len(members)}):\n" + 
                 "\n".join(f"{m['name']} (ID: {m['id']}, Roles: {', '.join(m['roles'])})" for m in members)
        )]

    # Role Management Tools
    elif name == "add_role":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        member = await guild.fetch_member(int(arguments["user_id"]))
        role = guild.get_role(int(arguments["role_id"]))
        
        await member.add_roles(role, reason="Role added via MCP")
        return [TextContent(
            type="text",
            text=f"Added role {role.name} to user {member.name}"
        )]

    elif name == "remove_role":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        member = await guild.fetch_member(int(arguments["user_id"]))
        role = guild.get_role(int(arguments["role_id"]))
        
        await member.remove_roles(role, reason="Role removed via MCP")
        return [TextContent(
            type="text",
            text=f"Removed role {role.name} from user {member.name}"
        )]

    # Channel Management Tools
    elif name == "create_text_channel":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        category = None
        if "category_id" in arguments:
            category = guild.get_channel(int(arguments["category_id"]))
        
        channel = await guild.create_text_channel(
            name=arguments["name"],
            category=category,
            topic=arguments.get("topic"),
            reason="Channel created via MCP"
        )
        
        return [TextContent(
            type="text",
            text=f"Created text channel #{channel.name} (ID: {channel.id})"
        )]

    elif name == "delete_channel":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        await channel.delete(reason=arguments.get("reason", "Channel deleted via MCP"))
        return [TextContent(
            type="text",
            text=f"Deleted channel successfully"
        )]

    # Message Reaction Tools
    elif name == "add_reaction":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        await message.add_reaction(arguments["emoji"])
        return [TextContent(
            type="text",
            text=f"Added reaction {arguments['emoji']} to message"
        )]

    elif name == "add_multiple_reactions":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        for emoji in arguments["emojis"]:
            await message.add_reaction(emoji)
        return [TextContent(
            type="text",
            text=f"Added reactions: {', '.join(arguments['emojis'])} to message"
        )]

    elif name == "remove_reaction":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        await message.remove_reaction(arguments["emoji"], discord_client.user)
        return [TextContent(
            type="text",
            text=f"Removed reaction {arguments['emoji']} from message"
        )]

    if name == "await_mention":
        # Wait for recent_mentions to have channel IDs
        T=0.0
        dt=0.1
        while not recent_mentions and T < discord_timeout:
            T=T+dt
            await asyncio.sleep(dt)  # Wait for mentions to accumulate
        # Convert recent_mentions to a JSON string and clear it
        if len(recent_mentions) > 1:
            mentions = json.dumps({"Recent mentions in channels": list(recent_mentions)}, indent=0)
        if len(recent_mentions) == 1:
            mentions = f"Recent mentions in channel: {list(recent_mentions)[0]}"
        if len(recent_mentions) == 0:
            mentions = "No recent mentions"
        return [TextContent(
            type="text",
            text=mentions
        )]

    raise ValueError(f"Unknown tool: {name}")

@app.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri=AnyUrl(f"file://{key}"),
            name=fixed_resources[key]["name"],
            description=fixed_resources[key]["description"],
            mimeType="text/plain",
        )
        for key in fixed_resources.keys()
    ]

@app.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    if not uri:
        raise ValueError("Missing resource_name parameter")
    if uri.scheme != "file":
        raise ValueError(f"Unsupported URI scheme: {uri.scheme}")
    resource_name = str(uri).replace("file://", "")
    if resource_name in list(fixed_resources.keys()):
        file_path = Path(__file__).resolve().parent / resource_name
        with open(file_path, "r") as file:
            return file.read()
    else:
        return "Resource not found."

async def main():
    # Start Discord bot in the background
    asyncio.create_task(bot.start(DISCORD_TOKEN))
    
    # Run MCP server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
