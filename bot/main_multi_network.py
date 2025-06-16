import asyncio
import os
import discord
import re
import logging
import json
import sys
import traceback

from datetime import datetime
from types import SimpleNamespace
from discord import app_commands
from discord.ext import tasks, commands
from typing import List, Dict, Union, Optional, Any

# Utils
from utils.config import Config
from utils.logger import Logger
from utils.data_processing import DiscordFormatting
from utils.governance_monitor import GovernanceMonitor

# Multi-network support
from utils.network_manager import NetworkManager
from utils.multi_network_handler import MultiNetworkHandler
from utils.multi_network_governance import MultiNetworkGovernance
from utils.network_commands import NetworkCommands

# API clients
from bot.utils.price_utils import get_asset_price_v1, get_asset_price_v2, update_all_prices

# Bot tracking
from utils.stats import StatsManager

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Initialize bot with command prefix and intents
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
bot.config = Config()
logger = Logger()
bot_started_at = datetime.now()

# Initialize stats and formatting
stats = StatsManager()
discord_format = DiscordFormatting()

# Price functions are now imported from price_utils

# Attach the price getters to the bot instance
bot.get_asset_price = get_asset_price_v1
bot.get_asset_price_v2 = get_asset_price_v2

@bot.event
async def on_ready():
    """
    Event triggered when the bot has connected to Discord.
    Initialize all components and start background tasks.
    """
    logger.info(f"Logged in as {bot.user.name} (ID: {bot.user.id})")

    try:
        # Initialize multi-network governance
        bot.network_manager = NetworkManager("../data/networks.json")
        await bot.network_manager.start()

        # Initialize multi-network handler
        bot.multi_network_handler = MultiNetworkHandler(bot.network_manager)
        await bot.multi_network_handler.initialize_connections()

        # Initialize governance
        bot.multi_network_governance = MultiNetworkGovernance(bot, discord_format)
        await bot.multi_network_governance.start()

        # Register network commands
        network_commands = NetworkCommands(bot, bot.network_manager)
        network_commands.register_commands(bot.tree, bot.config.DISCORD_SERVER_ID)

        # Start background tasks
        check_governance.start()
        update_prices.start()

        # Sync commands
        await bot.tree.sync()

        logger.info("Bot initialization complete")
    except Exception as error:
        logger.error(f"Error in on_ready: {error}")
        logger.error(traceback.format_exc())

@tasks.loop(hours=3)
async def check_governance():
    """
    Periodic task checks for governance proposals across all configured networks.
    """
    if not hasattr(bot, 'multi_network_governance'):
        logger.error("Multi-network governance not initialized")
        return

    try:
        logger.info("Checking governance proposals across all networks")
        await bot.multi_network_governance.check_governance()
        stats.log_run("check_governance")
    except Exception as error:
        logger.error(f"Error in check_governance: {error}")
        logger.error(traceback.format_exc())

@check_governance.before_loop
async def before_check_governance():
    """Wait for bot to be ready before starting governance check task."""
    await bot.wait_until_ready()

@tasks.loop(minutes=15)
async def update_prices():
    """Update asset prices periodically."""
    try:
        update_all_prices()
        stats.record_run("update_prices")
    except Exception as error:
        logger.error(f"Error updating prices: {error}")

@update_prices.before_loop
async def before_update_prices():
    """Wait for bot to be ready before starting price update task."""
    await bot.wait_until_ready()

# Helper methods for Discord operations
async def lock_threads_by_message_ids(guild_id, thread_ids):
    """Lock multiple threads by their message IDs."""
    if not thread_ids:
        return

    guild = bot.get_guild(guild_id)
    if not guild:
        logger.error(f"Guild not found with ID {guild_id}")
        return

    for thread_id in thread_ids:
        try:
            thread = await guild.fetch_channel(thread_id)
            await thread.edit(locked=True, archived=True)
            logger.info(f"Locked thread {thread_id}")
        except Exception as e:
            logger.error(f"Error locking thread {thread_id}: {e}")

async def create_or_get_role(guild, role_name):
    """Create or get a role by name."""
    try:
        existing_role = discord.utils.get(guild.roles, name=role_name)
        if existing_role:
            return existing_role

        new_role = await guild.create_role(
            name=role_name,
            color=0x9B59B6,
            mentionable=True
        )
        return new_role
    except Exception as e:
        logger.error(f"Error creating or getting role {role_name}: {e}")
        return None

async def get_or_create_governance_tag(available_channel_tags, governance_origin, forum, network_name="polkadot"):
    """Get or create a governance tag for a forum channel, prefixed with network name."""
    try:
        origin = governance_origin[0] if governance_origin else "Other"
        # Format for multi-network: [NETWORK] Origin
        tag_name = f"[{network_name.upper()}] {origin}"

        # Check if tag exists
        for tag in available_channel_tags:
            if tag.name == tag_name:
                return tag

        # Create new tag
        if len(available_channel_tags) < 20:  # Discord limit
            new_tag = await forum.create_tag(tag_name)
            return new_tag
        else:
            # If we hit the tag limit, return a generic tag or the first one
            logger.warning(f"Cannot create new tag '{tag_name}', reached Discord limit")
            return available_channel_tags[0] if available_channel_tags else None
    except Exception as e:
        logger.error(f"Error creating tag: {e}")
        return None

async def manage_discord_thread(
    channel,
    operation,
    title=None,
    index=None,
    content=None,
    governance_tag=None,
    message_id=None,
    client=None,
    network_id="polkadot"
):
    """Create or find a Discord thread for referendum discussion."""
    try:
        if operation == 'create':
            # Create a new thread
            first_message = f"**{title}**\n{content[:1900]}" if content else f"**{title}**"
            thread = await channel.create_thread(
                name=title,
                content=first_message,
                applied_tags=[governance_tag] if governance_tag else None,
            )
            return thread
        elif operation == 'find':
            # Find thread by its index in title for use with existing threads
            async for thread in channel.archived_threads():
                if f"#{index}" in thread.name:
                    return thread
            return None
    except Exception as error:
        logger.error(f"Error managing Discord thread: {error}")
        return None

# Attach helper methods to bot instance
bot.lock_threads_by_message_ids = lock_threads_by_message_ids
bot.create_or_get_role = create_or_get_role
bot.get_or_create_governance_tag = get_or_create_governance_tag
bot.manage_discord_thread = manage_discord_thread

# Register slash commands
@bot.tree.command(
    name="info",
    description="Get information about the bot"
)
async def info_command(interaction: discord.Interaction):
    """Display information about bot and its configuration."""
    try:
        # Get network information
        networks = await bot.network_manager.get_all_networks()
        enabled_networks = [f"{net_id} ({config['network_name']})"
                           for net_id, config in networks.items()
                           if config.get('enabled', True)]

        # Create embed
        embed = discord.Embed(
            title="OpenGov Bot Info",
            description="Bot for monitoring multi-network referenda",
            color=0x00FF00
        )

        embed.add_field(
            name="Active Networks",
            value="\n".join(enabled_networks) if enabled_networks else "No networks enabled",
            inline=False
        )

        embed.add_field(
            name="Uptime",
            value=f"{datetime.now() - bot_started_at}",
            inline=True
        )

        embed.add_field(
            name="Latest Governance Check",
            value=stats.get_last_run_time("check_governance") or "Never",
            inline=True
        )

        await interaction.response.send_message(embed=embed)
    except Exception as error:
        logger.error(f"Error in info command: {error}")
        await interaction.response.send_message(
            "Error occurred while getting bot information.",
            ephemeral=True
        )

# Run bot
if __name__ == "__main__":
    try:
        bot.run(bot.config.DISCORD_BOT_TOKEN)
    except Exception as e:
        logger.critical(f"Failed to start bot: {e}")
        sys.exit(1)
    finally:
        # Price APIs are now managed in price_utils

        # Close network connections
        if hasattr(bot, 'multi_network_handler'):
            asyncio.run(bot.multi_network_handler.close_connections())

        # Stop file watcher
        if hasattr(bot, 'network_manager'):
            asyncio.run(bot.network_manager.stop())
