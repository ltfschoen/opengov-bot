#!/usr/bin/env python3
import asyncio
import sys
import os
import json
import logging
import traceback
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Enable verbose Discord logging
logging.basicConfig(level=logging.DEBUG)

# Import bot modules
from bot.utils.logger import Logger
from bot.utils.subquery import SubstrateAPI
from bot.utils.gov2 import OpenGovernance2
from bot.utils.data_processing import CacheManager

# Discord imports
import discord
from discord.ext import commands

# Set up console logger
console_logger = logging.getLogger("console")
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
console_logger.addHandler(console_handler)
console_logger.setLevel(logging.INFO)

class StandaloneConfig:
    """
    Standalone configuration for running the script without starting the Flask server
    """
    def __init__(self):
        self.logger = Logger()
        
        # Load environment variables
        self.NETWORK = os.getenv('NETWORK_NAME', 'polkadot')
        self.NETWORK_NAME = self.NETWORK  # Alias for compatibility with OpenGovernance2
        self.SYMBOL = os.getenv('SYMBOL', 'DOT')
        self.TOKEN_DECIMAL = int(os.getenv('TOKEN_DECIMAL', '10'))
        self.SUBSTRATE_WSS = os.getenv('SUBSTRATE_WSS', 'wss://rpc.polkadot.io')
        
        # Discord configuration
        self.DISCORD_API_KEY = os.getenv('DISCORD_API_KEY')
        self.DISCORD_SERVER_ID = os.getenv('DISCORD_SERVER_ID')
        self.DISCORD_FORUM_CHANNEL_ID = os.getenv('DISCORD_FORUM_CHANNEL_ID')
        self.DISCORD_NOTIFY_ROLE = os.getenv('DISCORD_NOTIFY_ROLE', 'DOT-GOV')
        self.DISCORD_ADMIN_ROLE = os.getenv('DISCORD_ADMIN_ROLE', 'Admin')
        self.DISCORD_VOTER_ROLE = os.getenv('DISCORD_VOTER_ROLE', 'dao-team-representative')
        
        # Check if Discord posting is possible
        self.can_post_to_discord = all([
            self.DISCORD_API_KEY,
            self.DISCORD_SERVER_ID,
            self.DISCORD_FORUM_CHANNEL_ID
        ])
        
        # Print Discord configuration for debugging
        console_logger.info(f"Discord configuration:")
        console_logger.info(f"  API Key present: {self.DISCORD_API_KEY is not None}")
        console_logger.info(f"  Server ID: {self.DISCORD_SERVER_ID}")
        console_logger.info(f"  Forum Channel ID: {self.DISCORD_FORUM_CHANNEL_ID}")
        console_logger.info(f"  Notify Role: {self.DISCORD_NOTIFY_ROLE}")
        console_logger.info(f"  Can post to Discord: {self.can_post_to_discord}")
        
        if not self.can_post_to_discord:
            missing = []
            if not self.DISCORD_API_KEY:
                missing.append("DISCORD_API_KEY")
            if not self.DISCORD_SERVER_ID:
                missing.append("DISCORD_SERVER_ID")
            if not self.DISCORD_FORUM_CHANNEL_ID:
                missing.append("DISCORD_FORUM_CHANNEL_ID")
            console_logger.warning(f"Discord posting is disabled. Missing: {', '.join(missing)}")

# Initialize Discord bot with proper intents
intents = discord.Intents.default()
try:
    # Message content intent - needed for command parsing
    intents.message_content = True
    console_logger.info("Enabled message_content intent")
except Exception as e:
    console_logger.warning(f"Could not enable message_content intent: {e}")

try:
    # Members intent - needed for member tracking
    intents.members = True
    console_logger.info("Enabled members intent")
except Exception as e:
    console_logger.warning(f"Could not enable members intent: {e}")

# Initialize bot with command prefix and intents
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

@bot.event
async def on_ready():
    console_logger.info(f"Bot logged in as {bot.user} (ID: {bot.user.id})")
    console_logger.info(f"Bot is in {len(bot.guilds)} guilds:")
    for guild in bot.guilds:
        console_logger.info(f"  - {guild.name} (ID: {guild.id})")
        
    # Check if the bot can see the forum channel
    config = StandaloneConfig()
    if config.DISCORD_FORUM_CHANNEL_ID:
        try:
            channel_id = int(config.DISCORD_FORUM_CHANNEL_ID)
            channel = bot.get_channel(channel_id)
            if channel:
                console_logger.info(f"Found forum channel: {channel.name} (ID: {channel.id})")
                console_logger.info(f"Channel type: {channel.type}")
                if str(channel.type) != 'forum':
                    console_logger.error(f"ERROR: Channel is not a forum channel! Type: {channel.type}")
            else:
                console_logger.error(f"ERROR: Could not find forum channel with ID: {channel_id}")
                console_logger.info("Available channels:")
                for guild in bot.guilds:
                    for ch in guild.channels:
                        console_logger.info(f"  - {ch.name} (ID: {ch.id}, Type: {ch.type})")
        except Exception as e:
            console_logger.error(f"Error checking forum channel: {e}")
            traceback.print_exc()

async def initialize_discord():
    """Initialize Discord client and connect"""
    config = StandaloneConfig()
    if config.DISCORD_API_KEY:
        try:
            console_logger.info("Initializing Discord client...")
            await bot.start(config.DISCORD_API_KEY)
        except Exception as e:
            console_logger.error(f"Failed to initialize Discord client: {e}")
            traceback.print_exc()
    else:
        console_logger.warning("No Discord API key provided, skipping Discord initialization")

async def post_referendum_to_discord(referendum_id, title, description, origin):
    """Post a referendum to the Discord forum channel"""
    config = StandaloneConfig()
    
    if not config.can_post_to_discord:
        console_logger.warning("Cannot post to Discord: missing configuration")
        return False
    
    try:
        console_logger.info(f"Attempting to post referendum #{referendum_id} to Discord...")
        
        # Get the forum channel
        channel_id = int(config.DISCORD_FORUM_CHANNEL_ID)
        channel = bot.get_channel(channel_id)
        
        if not channel:
            console_logger.error(f"Could not find forum channel with ID: {channel_id}")
            return False
            
        if str(channel.type) != 'forum':
            console_logger.error(f"Channel is not a forum channel! Type: {channel.type}")
            return False
        
        # Create a new forum post
        console_logger.info(f"Creating forum post for referendum #{referendum_id}...")
        
        # Prepare content with notification
        notify_role = config.DISCORD_NOTIFY_ROLE
        content = f"<@&{notify_role}> New referendum #{referendum_id} is now available for discussion!"
        
        # Create forum post with appropriate tags
        try:
            # Try to find an appropriate tag based on origin
            available_tags = channel.available_tags
            tag_names = [tag.name for tag in available_tags]
            console_logger.info(f"Available tags: {tag_names}")
            
            # Find matching tag for the origin
            tag_id = None
            for tag in available_tags:
                if origin in tag.name:
                    tag_id = tag.id
                    break
            
            # Create the thread with or without tag
            if tag_id:
                console_logger.info(f"Using tag: {tag_id}")
                thread = await channel.create_thread(
                    name=f"#{referendum_id}: {title}",
                    content=content,
                    applied_tags=[tag_id]
                )
            else:
                console_logger.info("No matching tag found, creating thread without tags")
                thread = await channel.create_thread(
                    name=f"#{referendum_id}: {title}",
                    content=content
                )
            
            console_logger.info(f"Created thread: {thread.name} (ID: {thread.id})")
            
            # Post the description as a follow-up message
            await thread.send(f"**Description**: {description}")
            
            return True
        except Exception as e:
            console_logger.error(f"Error creating forum post: {e}")
            traceback.print_exc()
            return False
            
    except Exception as e:
        console_logger.error(f"Error posting to Discord: {e}")
        traceback.print_exc()
        return False

async def main():
    """Main function to check for new referendums"""
    config = StandaloneConfig()
    
    # Initialize Discord client in background if API key is provided
    discord_task = None
    if config.DISCORD_API_KEY:
        console_logger.info("Starting Discord client in background...")
        discord_task = asyncio.create_task(initialize_discord())
    
    console_logger.info("Checking for new referendums...")
    
    # Connect to substrate
    substrate = SubstrateAPI(config)
    await substrate.connect(config.SUBSTRATE_WSS)
    console_logger.info("Connected to Substrate node successfully")
    
    # Initialize governance
    governance = OpenGovernance2(config, substrate)
    console_logger.info("Initializing OpenGovernance2...")
    
    # Check for test mode
    test_mode = os.getenv('TEST_MODE', '').lower() == 'true'
    
    try:
        # Get all ongoing referenda directly
        console_logger.info("Checking for ongoing referendums...")
        try:
            referendum_info_for = await substrate.referendumInfoFor()
            
            # Display all ongoing referenda
            if referendum_info_for:
                ongoing_refs = []
                for ref_id, ref_data in referendum_info_for.items():
                    if 'Ongoing' in ref_data:
                        ongoing_refs.append(int(ref_id))
                
                if ongoing_refs:
                    ongoing_refs.sort()
                    console_logger.info(f"Currently ongoing referendums: {ongoing_refs}")
                    
                    # Get details for each ongoing referendum
                    for ref_id in ongoing_refs[:5]:  # Limit to first 5 to avoid too much output
                        console_logger.info(f"Getting details for referendum #{ref_id}...")
                        ref_data = await governance.fetch_referendum_data(referendum_id=ref_id, network=config.NETWORK_NAME)
                        console_logger.info(f"Referendum #{ref_id} details:")
                        console_logger.info(f"  Title: {ref_data.get('title', 'No title')}")
                        console_logger.info(f"  Origin: {ref_data.get('origin', 'Unknown')}")
                        
                    if len(ongoing_refs) > 5:
                        console_logger.info(f"... and {len(ongoing_refs) - 5} more referendums")
            else:
                console_logger.info("No ongoing referendums found")
        except Exception as e:
            console_logger.error(f"Error getting ongoing referendums: {e}")
            traceback.print_exc()
        
        # Get referenda
        if test_mode:
            console_logger.info("TEST MODE ENABLED: Creating fake test referenda")
            
            # Create fake referendum for testing
            fake_ref_id = 9999
            fake_title = "TEST_DOT_REF"
            fake_desc = "This is a test referendum for Polkadot created in test mode..."
            fake_origin = "TestOrigin"
            
            console_logger.info(f"Created fake Polkadot referendum #{fake_ref_id}: {fake_title}")
            console_logger.info(f"Returning 1 fake referenda: [{fake_ref_id}]")
            
            # Process the fake referendum
            console_logger.info(f"Found 1 new referendums: [{fake_ref_id}]")
            console_logger.info(f"Referendum #{fake_ref_id}: {fake_title}")
            console_logger.info(f"Description: {fake_desc}")
            console_logger.info(f"Origin: {fake_origin}")
            
            # Post to Discord if possible
            if config.can_post_to_discord:
                # Wait for Discord client to be ready
                if discord_task:
                    console_logger.info("Waiting for Discord client to be ready...")
                    try:
                        # Wait for a short time to allow Discord to connect
                        await asyncio.wait_for(discord_task, timeout=10)
                        console_logger.info("Discord client is ready")
                    except asyncio.TimeoutError:
                        console_logger.warning("Timeout waiting for Discord client to be ready")
                
                # Post the referendum
                success = await post_referendum_to_discord(fake_ref_id, fake_title, fake_desc, fake_origin)
                if success:
                    console_logger.info(f"Successfully posted referendum #{fake_ref_id} to Discord")
                else:
                    console_logger.error(f"Failed to post referendum #{fake_ref_id} to Discord")
            else:
                console_logger.warning("Discord posting is disabled due to missing configuration")
        else:
            # Get real referenda from the network
            new_referendums, referendum_info = await governance.check_referendums()
            
            # Display all ongoing referenda
            if referendum_info:
                ongoing_refs = []
                for ref_id, ref_data in referendum_info.items():
                    if 'Ongoing' in ref_data:
                        ongoing_refs.append(int(ref_id))
                
                if ongoing_refs:
                    ongoing_refs.sort()
                    console_logger.info(f"Currently ongoing referendums: {ongoing_refs}")
                    
                    # Get details for each ongoing referendum
                    for ref_id in ongoing_refs[:5]:  # Limit to first 5 to avoid too much output
                        console_logger.info(f"Getting details for referendum #{ref_id}...")
                        ref_data = await governance.fetch_referendum_data(referendum_id=ref_id, network=config.NETWORK_NAME)
                        console_logger.info(f"Referendum #{ref_id} details:")
                        console_logger.info(f"  Title: {ref_data.get('title', 'No title')}")
                        console_logger.info(f"  Origin: {ref_data.get('origin', 'Unknown')}")
                        
                    if len(ongoing_refs) > 5:
                        console_logger.info(f"... and {len(ongoing_refs) - 5} more referendums")
            
            # Process new referenda
            if new_referendums:
                console_logger.info(f"Found {len(new_referendums)} new referendums")
                
                # Process each referendum
                for ref_id in new_referendums:
                    ref_data = new_referendums[ref_id]
                    title = ref_data.get('title', f"Referendum #{ref_id}")
                    description = ref_data.get('description', 'No description available')
                    origin = ref_data.get('origin', 'Unknown')
                    
                    console_logger.info(f"Referendum #{ref_id}: {title}")
                    console_logger.info(f"Description: {description[:100]}...")
                    console_logger.info(f"Origin: {origin}")
                    
                    # Post to Discord if possible
                    if config.can_post_to_discord:
                        success = await post_referendum_to_discord(ref_id, title, description, origin)
                        if success:
                            console_logger.info(f"Successfully posted referendum #{ref_id} to Discord")
                        else:
                            console_logger.error(f"Failed to post referendum #{ref_id} to Discord")
            else:
                console_logger.info("No new referendums found")
    except Exception as e:
        console_logger.error(f"Error checking referenda: {e}")
        traceback.print_exc()
    finally:
        # Close substrate connection
        console_logger.info("Closing Substrate connection...")
        await substrate.close()
        console_logger.info("Substrate connection closed")
        
        # Close Discord connection if it was started
        if discord_task and not discord_task.done():
            console_logger.info("Closing Discord connection...")
            await bot.close()
            console_logger.info("Discord connection closed")
            
        console_logger.info("Manual governance check completed")

async def test_discord():
    """Test Discord connectivity and forum channel access"""
    config = StandaloneConfig()
    
    if not config.DISCORD_API_KEY:
        console_logger.error("Cannot test Discord: No API key provided")
        return
        
    try:
        console_logger.info("Testing Discord connectivity...")
        
        # Start Discord client if not already started
        if not bot.is_ready():
            console_logger.info("Starting Discord client for testing...")
            await bot.start(config.DISCORD_API_KEY)
        
        # Check if we can access the forum channel
        if config.DISCORD_FORUM_CHANNEL_ID:
            channel_id = int(config.DISCORD_FORUM_CHANNEL_ID)
            channel = bot.get_channel(channel_id)
            
            if channel:
                console_logger.info(f"Found channel: {channel.name} (ID: {channel.id})")
                console_logger.info(f"Channel type: {channel.type}")
                
                # Try to send a test message
                if str(channel.type) == 'forum':
                    console_logger.info("Creating test thread in forum channel...")
                    test_thread = await channel.create_thread(
                        name="Test Thread - Please Ignore",
                        content="This is a test thread to verify bot permissions. You can delete this."
                    )
                    console_logger.info(f"Successfully created test thread: {test_thread.name} (ID: {test_thread.id})")
                    
                    # Send a message in the thread
                    await test_thread.send("Test message in thread. If you can see this, the bot is working correctly!")
                    console_logger.info("Successfully sent message in test thread")
                else:
                    console_logger.error(f"Channel is not a forum channel! Type: {channel.type}")
                    console_logger.info("Attempting to send a direct message to the channel...")
                    await channel.send("Test message from referendum bot. If you can see this, the bot can post to this channel but it's not a forum channel.")
            else:
                console_logger.error(f"Could not find channel with ID: {channel_id}")
                console_logger.info("Available channels:")
                for guild in bot.guilds:
                    console_logger.info(f"Guild: {guild.name}")
                    for ch in guild.channels:
                        console_logger.info(f"  - {ch.name} (ID: {ch.id}, Type: {ch.type})")
        else:
            console_logger.error("No forum channel ID provided")
    except Exception as e:
        console_logger.error(f"Error testing Discord: {e}")
        traceback.print_exc()
    finally:
        # Close Discord connection
        console_logger.info("Closing Discord connection...")
        await bot.close()
        console_logger.info("Discord connection closed")

if __name__ == "__main__":
    # Check if we should run the main function or just test Discord
    test_only = len(sys.argv) > 1 and sys.argv[1] == "--test-discord"
    
    if test_only:
        console_logger.info("Running Discord test only...")
        asyncio.run(test_discord())
    else:
        console_logger.info("Running full referendum check...")
        asyncio.run(main())
