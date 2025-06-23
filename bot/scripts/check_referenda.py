#!/usr/bin/env python3
import asyncio
import sys
import os
import json
import logging
import traceback
from datetime import datetime
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load from .env file in project root
    dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', '.env'))
    if os.path.exists(dotenv_path):
        console_logger = logging.getLogger("console")
        print(f"Loading environment variables from {dotenv_path}")
        load_dotenv(dotenv_path)
        print("Environment variables loaded successfully")
    else:
        print(f"Warning: .env file not found at {dotenv_path}")
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables from .env file will not be loaded.")
    print("Install with: pip install python-dotenv")

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
        
        # Handle TOKEN_DECIMAL which might be in scientific notation (e.g., 1e10)
        token_decimal_str = os.getenv('TOKEN_DECIMAL', '10')
        try:
            # Try parsing as float first to handle scientific notation
            self.TOKEN_DECIMAL = int(float(token_decimal_str))
            console_logger.info(f"Using TOKEN_DECIMAL: {self.TOKEN_DECIMAL}")
        except ValueError:
            console_logger.warning(f"Invalid TOKEN_DECIMAL value: {token_decimal_str}, using default 10")
            self.TOKEN_DECIMAL = 10
            
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

async def post_referendum_to_discord(ref_id, title, description, origin):
    """Post a referendum to Discord."""
    # Get the config
    config = StandaloneConfig()
    
    if not config.can_post_to_discord:
        console_logger.warning("Discord posting is disabled due to missing configuration")
        return False
        
    try:
        # Get the guild
        guild = bot.get_guild(int(config.DISCORD_SERVER_ID))
        if not guild:
            console_logger.error(f"Could not find guild with ID {config.DISCORD_SERVER_ID}")
            return False
            
        # Get the forum channel
        channel = guild.get_channel(int(config.DISCORD_FORUM_CHANNEL_ID))
        if not channel:
            console_logger.error(f"Could not find channel with ID {config.DISCORD_FORUM_CHANNEL_ID}")
            return False
            
        # Check if it's a forum channel
        if not isinstance(channel, discord.ForumChannel):
            console_logger.error(f"Channel {channel.name} is not a forum channel")
            return False
            
        # Get permissions
        permissions = channel.permissions_for(guild.me)
        console_logger.info(f"Bot permissions in forum channel:")
        console_logger.info(f"  Send Messages: {permissions.send_messages}")
        console_logger.info(f"  Create Public Threads: {permissions.create_public_threads}")
        console_logger.info(f"  Send Messages in Threads: {permissions.send_messages_in_threads}")
        console_logger.info(f"  Manage Threads: {permissions.manage_threads}")
        
        if not permissions.create_public_threads:
            console_logger.error("Bot doesn't have permission to create threads")
            console_logger.info("Please make sure the bot has the 'Create Public Threads' permission")
            return False
            
        # Format the message
        message = f"## Referendum #{ref_id}: {title}\n\n"
        if description:
            message += f"{description}\n\n"
        message += f"**Origin:** {origin}\n"
        
        # Check for available tags
        tags = []
        if hasattr(channel, 'available_tags') and channel.available_tags:
            console_logger.info(f"Available tags: {[tag.name for tag in channel.available_tags]}")
            
            # Try to find a matching tag
            matching_tag = None
            for tag in channel.available_tags:
                if tag.name.lower() == origin.lower():
                    matching_tag = tag  # Store the entire tag object
                    console_logger.info(f"Found matching tag: {tag.name}")
                    break
                    
            if matching_tag:
                tags = [matching_tag]  # Use the tag object directly
            else:
                console_logger.info("No matching tag found, using first available tag")
                if channel.available_tags:
                    tags = [channel.available_tags[0]]  # Use the first tag object
        
        # Check if tags are required
        if hasattr(channel, 'requires_tag') and channel.requires_tag and not tags:
            console_logger.warning("Forum channel requires tags but no tags are available")
            if channel.available_tags:
                tags = [channel.available_tags[0]]  # Use the first tag object
                console_logger.info(f"Using first available tag: {channel.available_tags[0].name}")
        
        try:
            # Create the thread with initial message
            thread_name = f"#{ref_id}: {title}"
            if len(thread_name) > 100:
                thread_name = thread_name[:97] + "..."
                
            console_logger.info(f"Creating thread with name: {thread_name}")
            console_logger.info(f"Applied tags: {[tag.name for tag in tags]}")
            
            # Use the forum-specific thread creation method
            thread = await channel.create_thread(
                name=thread_name,
                content=message,
                applied_tags=[discord.Object(id=tag.id) for tag in tags] if tags else None  # Convert tag objects to Discord.Object instances
            )
            # ThreadWithMessage object has thread attribute that contains the actual Thread
            console_logger.info(f"Created thread: {thread.thread.name} (ID: {thread.thread.id})")
            
            # Mention the notify role if configured
            if config.DISCORD_NOTIFY_ROLE:
                # Find the role
                role = None
                for r in guild.roles:
                    if r.name == config.DISCORD_NOTIFY_ROLE:
                        role = r
                        break
                
                if role:
                    await thread.thread.send(f"{role.mention} New referendum #{ref_id} is now available for discussion!")
                    console_logger.info(f"Mentioned role {role.name} in thread")
                else:
                    console_logger.warning(f"Could not find role with name {config.DISCORD_NOTIFY_ROLE}")
                    # Try sending a message with the role name as text
                    await thread.thread.send(f"@{config.DISCORD_NOTIFY_ROLE} New referendum #{ref_id} is now available for discussion!")
            
            return True
        except discord.Forbidden as e:
            console_logger.error(f"Error creating forum post: {e}")
            console_logger.error("The bot doesn't have the required permissions")
            console_logger.info("Please check the bot's role permissions and channel-specific permissions")
            traceback.print_exc()
            return False
        except discord.HTTPException as e:
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
            fake_origin = "TestOrigin" # tag
            
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
                for ref_id, ref_data in new_referendums.items():
                    title = ref_data.get('title', f"Referendum #{ref_id}")
                    description = ref_data.get('description')
                    origin = ref_data.get('origin', 'Unknown')
                    status = ref_data.get('status', 'Unknown')
                    
                    console_logger.info(f"Referendum #{ref_id}: {title}")
                    if description:
                        console_logger.info(f"Description: {description[:100]}..." if len(description) > 100 else f"Description: {description}")
                    else:
                        console_logger.info("Description: None")
                    
                    console_logger.info(f"Origin: {origin}")
                    console_logger.info(f"Status: {status}")
                    
                    # Prepare the message content
                    message = f"## {title or 'Untitled Referendum'}\n\n"
                    if description:
                        message += f"{description}\n\n"
                    message += f"**Origin:** {origin}\n"
                    message += f"**Status:** {status}\n"
                    message += f"**Referendum ID:** {ref_id}\n\n"
                    
                    # Post to Discord if possible
                    if config.can_post_to_discord:
                        try:
                            # Find the forum channel
                            guild = bot.get_guild(int(config.DISCORD_SERVER_ID))
                            if not guild:
                                console_logger.error(f"Could not find Discord server with ID {config.DISCORD_SERVER_ID}")
                                continue
                                
                            forum_channel = guild.get_channel(int(config.DISCORD_FORUM_CHANNEL_ID))
                            if not forum_channel:
                                console_logger.error(f"Could not find forum channel with ID {config.DISCORD_FORUM_CHANNEL_ID}")
                                continue
                                
                            # Check if forum channel has required tags
                            tags = []
                            if hasattr(forum_channel, 'available_tags') and forum_channel.available_tags:
                                # Try to find a tag that matches the origin
                                origin_tag = None
                                for tag in forum_channel.available_tags:
                                    if tag.name.lower() == origin.lower():
                                        origin_tag = tag.id
                                        break
                                
                                # If no matching tag found, use the first available tag
                                if origin_tag:
                                    tags = [origin_tag]
                                    console_logger.info(f"Using matching tag for origin: {origin}")
                                elif forum_channel.available_tags:
                                    tags = [forum_channel.available_tags[0].id]
                                    console_logger.info(f"Using first available tag: {forum_channel.available_tags[0].name}")
                            
                            # Create thread in forum channel
                            thread = await forum_channel.create_thread(
                                name=f"Referendum #{ref_id}: {title[:80]}" if len(title) > 80 else f"Referendum #{ref_id}: {title}",
                                content=message,
                                applied_tags=[discord.Object(id=tag) for tag in tags] if tags else None  # Convert tag IDs to Discord.Object instances
                            )
                            console_logger.info(f"Posted referendum #{ref_id} to Discord thread: {thread.thread.name}")
                            
                            # Mention roles if configured
                            if config.DISCORD_NOTIFY_ROLE:
                                role_mention = None
                                for role in guild.roles:
                                    if role.name == config.DISCORD_NOTIFY_ROLE:
                                        role_mention = role
                                        break
                                
                                if role_mention:
                                    await thread.thread.send(f"{role_mention.mention} A new referendum has been posted!")
                                    console_logger.info(f"Mentioned role {role_mention.name} in thread")
                                else:
                                    console_logger.warning(f"Could not find role with name {config.DISCORD_NOTIFY_ROLE}")
                                    # Try sending a message with the role name as text
                                    await thread.thread.send(f"@{config.DISCORD_NOTIFY_ROLE} New referendum #{ref_id} is now available for discussion!")
                        except Exception as e:
                            console_logger.error(f"Error posting referendum #{ref_id} to Discord: {e}")
                            traceback.print_exc()
                    else:
                        console_logger.info("Skipping Discord posting (not configured)")
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
    
    console_logger.info("=== DISCORD TEST MODE ===")
    console_logger.info("Testing Discord connectivity and permissions...")
    
    # Check Discord configuration
    console_logger.info("Discord configuration:")
    console_logger.info(f"  API Key present: {bool(config.DISCORD_API_KEY)}")
    console_logger.info(f"  Server ID: {config.DISCORD_SERVER_ID}")
    console_logger.info(f"  Forum Channel ID: {config.DISCORD_FORUM_CHANNEL_ID}")
    console_logger.info(f"  Notify Role: {config.DISCORD_NOTIFY_ROLE}")
    
    # Check if Discord can be used
    if not config.can_post_to_discord:
        missing = []
        if not config.DISCORD_API_KEY:
            missing.append("DISCORD_API_KEY")
        if not config.DISCORD_SERVER_ID:
            missing.append("DISCORD_SERVER_ID")
        if not config.DISCORD_FORUM_CHANNEL_ID:
            missing.append("DISCORD_FORUM_CHANNEL_ID")
        
        console_logger.error(f"Discord posting is disabled. Missing: {', '.join(missing)}")
        console_logger.info("Please set these environment variables and try again.")
        console_logger.info("You can create a .env file in the project root with these variables.")
        console_logger.info("Example:")
        console_logger.info("DISCORD_API_KEY=your_bot_token")
        console_logger.info("DISCORD_SERVER_ID=1234567890")
        console_logger.info("DISCORD_FORUM_CHANNEL_ID=0987654321")
        console_logger.info("DISCORD_NOTIFY_ROLE=DOT-GOV")
        return False
    
    # Initialize Discord client
    console_logger.info("Initializing Discord client...")
    try:
        await initialize_discord()
        
        # Wait for the bot to be ready
        console_logger.info("Waiting for Discord client to be ready...")
        start_time = time.time()
        while not bot.is_ready():
            await asyncio.sleep(1)
            if time.time() - start_time > 30:
                console_logger.error("Timeout waiting for Discord client to be ready")
                return False
        
        console_logger.info("Discord client is ready!")
        
        # List available guilds
        console_logger.info(f"Connected to {len(bot.guilds)} guilds:")
        for guild in bot.guilds:
            console_logger.info(f"  - {guild.name} (ID: {guild.id})")
            
            # Check if this is the target guild
            if str(guild.id) == config.DISCORD_SERVER_ID:
                console_logger.info(f"    Found target guild: {guild.name}")
                
                # Find the forum channel
                forum_channel = guild.get_channel(int(config.DISCORD_FORUM_CHANNEL_ID))
                if forum_channel:
                    console_logger.info(f"    Found forum channel: {forum_channel.name}")
                    
                    # Check channel type
                    if forum_channel.type == discord.ChannelType.forum:
                        console_logger.info(f"    Channel is a forum channel")
                        
                        # Check permissions
                        permissions = forum_channel.permissions_for(guild.me)
                        console_logger.info(f"    Bot permissions in forum channel:")
                        console_logger.info(f"      Send Messages: {permissions.send_messages}")
                        console_logger.info(f"      Create Public Threads: {permissions.create_public_threads}")
                        console_logger.info(f"      Send Messages in Threads: {permissions.send_messages_in_threads}")
                        console_logger.info(f"      Manage Threads: {permissions.manage_threads}")
                        console_logger.info(f"      Read Message History: {permissions.read_message_history}")
                        
                        # Log all permissions for debugging
                        console_logger.info(f"    All permissions (raw value: {permissions.value}):")
                        for perm_name, perm_value in permissions:
                            console_logger.info(f"      {perm_name}: {perm_value}")
                        
                        # Check available tags
                        if hasattr(forum_channel, 'available_tags'):
                            console_logger.info(f"    Available tags in forum channel:")
                            for tag in forum_channel.available_tags:
                                console_logger.info(f"      - {tag.name} (ID: {tag.id})")
                        else:
                            console_logger.warning(f"    No tags available in forum channel")
                        
                        # Test posting a message
                        console_logger.info("    Testing post to forum channel...")
                        try:
                            # Create a test thread
                            thread = await forum_channel.create_thread(
                                name="Test Thread - Please Ignore",
                                content="This is a test thread created by the OpenGov Bot to verify Discord connectivity. This thread can be safely deleted.",
                                auto_archive_duration=60
                            )
                            console_logger.info(f"    Successfully created test thread: {thread.thread.name}")
                            
                            # Post a message in the thread
                            await thread.thread.send("Test message in thread. This confirms the bot can post in threads.")
                            console_logger.info(f"    Successfully posted message in thread")
                            
                            # Lock the thread to indicate it's a test
                            await thread.thread.edit(locked=True)
                            console_logger.info(f"    Successfully locked thread")
                            
                            return True
                        except Exception as e:
                            console_logger.error(f"    Error posting to forum channel: {e}")
                            traceback.print_exc()
                    else:
                        console_logger.error(f"    Channel is not a forum channel (type: {forum_channel.type})")
                else:
                    console_logger.error(f"    Forum channel not found (ID: {config.DISCORD_FORUM_CHANNEL_ID})")
        
        # If we got here, we didn't find the target guild
        if config.DISCORD_SERVER_ID not in [str(g.id) for g in bot.guilds]:
            console_logger.error(f"Target guild not found (ID: {config.DISCORD_SERVER_ID})")
            console_logger.info("Make sure the bot has been added to the server and has the correct permissions")
    
    except Exception as e:
        console_logger.error(f"Error testing Discord: {e}")
        traceback.print_exc()
        return False
    finally:
        # Close Discord connection
        console_logger.info("Closing Discord connection...")
        await bot.close()
        console_logger.info("Discord connection closed")
    
    return False

if __name__ == "__main__":
    # Check if we should run the main function or just test Discord
    test_only = len(sys.argv) > 1 and sys.argv[1] == "--test-discord"
    
    if test_only:
        console_logger.info("Running Discord test only...")
        asyncio.run(test_discord())
    else:
        console_logger.info("Running full referendum check...")
        asyncio.run(main())
