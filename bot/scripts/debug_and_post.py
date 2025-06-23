#!/usr/bin/env python3
import asyncio
import os
import sys
import logging
import traceback
import argparse
import discord
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from bot.utils.subquery import SubstrateAPI
from bot.utils.gov2 import OpenGovernance2
from bot.scripts.check_referenda import StandaloneConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_and_post")

# Discord bot instance
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Debug and post referenda to Discord.')
parser.add_argument('--single', action='store_true', help='Only fetch and post one referendum per network')
args = parser.parse_args()

async def post_referendum_to_discord(ref_id, title, description, origin):
    """Post a referendum to Discord."""
    # Get the config
    config = StandaloneConfig()
    
    if not config.can_post_to_discord:
        logger.warning("Discord posting is disabled due to missing configuration")
        return False
        
    try:
        # Get the guild
        guild = bot.get_guild(int(config.DISCORD_SERVER_ID))
        if not guild:
            logger.error(f"Could not find guild with ID {config.DISCORD_SERVER_ID}")
            return False
            
        # Get the forum channel
        channel = guild.get_channel(int(config.DISCORD_FORUM_CHANNEL_ID))
        if not channel:
            logger.error(f"Could not find channel with ID {config.DISCORD_FORUM_CHANNEL_ID}")
            return False
            
        # Check if it's a forum channel
        if not isinstance(channel, discord.ForumChannel):
            logger.error(f"Channel {channel.name} is not a forum channel")
            return False
            
        # Get permissions
        permissions = channel.permissions_for(guild.me)
        logger.info(f"Bot permissions in forum channel:")
        logger.info(f"  Send Messages: {permissions.send_messages}")
        logger.info(f"  Create Public Threads: {permissions.create_public_threads}")
        logger.info(f"  Send Messages in Threads: {permissions.send_messages_in_threads}")
        logger.info(f"  Manage Threads: {permissions.manage_threads}")
        
        if not permissions.create_public_threads:
            logger.error("Bot doesn't have permission to create threads")
            logger.info("Please make sure the bot has the 'Create Public Threads' permission")
            return False
            
        # Format the message
        message = f"## Referendum #{ref_id}: {title}\n\n"
        if description:
            message += f"{description}\n\n"
        message += f"**Origin:** {origin}\n"
        
        # Check for available tags
        tags = []
        if hasattr(channel, 'available_tags') and channel.available_tags:
            logger.info(f"Available tags: {[tag.name for tag in channel.available_tags]}")
            
            # Try to find a matching tag
            matching_tag = None
            for tag in channel.available_tags:
                if tag.name.lower() == origin.lower():
                    matching_tag = tag  # Store the entire tag object
                    logger.info(f"Found matching tag: {tag.name}")
                    break
                    
            if matching_tag:
                tags = [matching_tag]  # Use the tag object directly
            else:
                logger.info("No matching tag found, using first available tag")
                if channel.available_tags:
                    tags = [channel.available_tags[0]]  # Use the first tag object
        
        # Check if tags are required
        if hasattr(channel, 'requires_tag') and channel.requires_tag and not tags:
            logger.warning("Forum channel requires tags but no tags are available")
            if channel.available_tags:
                tags = [channel.available_tags[0]]  # Use the first tag object
                logger.info(f"Using first available tag: {channel.available_tags[0].name}")
        
        try:
            # Create the thread with initial message
            thread_name = f"#{ref_id}: {title}"
            if len(thread_name) > 100:
                thread_name = thread_name[:97] + "..."
                
            logger.info(f"Creating thread with name: {thread_name}")
            logger.info(f"Applied tags: {[tag.name for tag in tags]}")
            
            # Use the forum-specific thread creation method
            thread = await channel.create_thread(
                name=thread_name,
                content=message,
                applied_tags=[discord.Object(id=tag.id) for tag in tags] if tags else None  # Convert tag objects to Discord.Object instances
            )
            # ThreadWithMessage object has thread attribute that contains the actual Thread
            logger.info(f"Created thread: {thread.thread.name} (ID: {thread.thread.id})")
            
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
                    logger.info(f"Mentioned role {role.name} in thread")
                else:
                    logger.warning(f"Could not find role with name {config.DISCORD_NOTIFY_ROLE}")
                    # Try sending a message with the role name as text
                    await thread.thread.send(f"@{config.DISCORD_NOTIFY_ROLE} New referendum #{ref_id} is now available for discussion!")
            
            return True
        except Exception as e:
            logger.error(f"Error creating thread: {e}")
            traceback.print_exc()
            return False
            
    except Exception as e:
        logger.error(f"Error posting referendum to Discord: {e}")
        traceback.print_exc()
        return False

async def process_network(network_name, network_config):
    """Process a single network and post referenda."""
    print(f"\nProcessing network: {network_name}")
    
    # Create a config for this network
    config = StandaloneConfig()
    config.NETWORK_NAME = network_name
    config.NETWORK = network_name
    config.SYMBOL = network_config.get('symbol', '')
    config.TOKEN_DECIMAL = network_config.get('token_decimal', 10)
    config.SUBSTRATE_WSS = network_config.get('substrate_wss', '')
    
    if not config.SUBSTRATE_WSS:
        print(f"No WSS endpoint configured for {network_name}, skipping")
        return
    
    print(f"Network: {config.NETWORK_NAME}")
    print(f"Symbol: {config.SYMBOL}")
    print(f"WSS: {config.SUBSTRATE_WSS}")
    
    # Connect to substrate
    substrate = SubstrateAPI(config)
    await substrate.connect(config.SUBSTRATE_WSS)
    print(f"Connected to {network_name} node successfully")
    
    # Initialize governance
    governance = OpenGovernance2(config, substrate)
    print(f"Initialized OpenGovernance2 for {network_name}")
    
    try:
        # Get referendum info directly
        print(f"Fetching referendum info for {network_name}...")
        referendum_info = await substrate.referendumInfoFor()
        print(f"Found {len(referendum_info)} referendums on {network_name}")
        
        # Process referenda
        if referendum_info:
            # Sort referenda by ID (newest first)
            sorted_refs = sorted(referendum_info.items(), key=lambda x: int(x[0]), reverse=True)
            
            # Limit to one referendum if --single flag is used
            if args.single and sorted_refs:
                sorted_refs = [sorted_refs[0]]
                print(f"--single flag used, processing only referendum #{sorted_refs[0][0]}")
            
            # Process each referendum
            for ref_id, ref_data in sorted_refs:
                print(f"Referendum #{ref_id} on {network_name}:")
                
                # Try to fetch more details
                try:
                    ref_details = await governance.fetch_referendum_data(referendum_id=ref_id, network=config.NETWORK_NAME)
                    title = ref_details.get('title', f"Referendum #{ref_id}")
                    description = ref_details.get('description', '')
                    origin = ref_details.get('origin', 'Unknown')
                    
                    print(f"  Title: {title}")
                    print(f"  Origin: {origin}")
                    
                    # Post to Discord if configured
                    if config.can_post_to_discord:
                        print(f"Posting referendum #{ref_id} from {network_name} to Discord...")
                        success = await post_referendum_to_discord(ref_id, title, description, origin)
                        if success:
                            print(f"Successfully posted referendum #{ref_id} from {network_name} to Discord")
                        else:
                            print(f"Failed to post referendum #{ref_id} from {network_name} to Discord")
                except Exception as e:
                    print(f"  Error fetching details for referendum #{ref_id} on {network_name}: {e}")
                    traceback.print_exc()
        else:
            print(f"No referenda found on {network_name}")
    finally:
        # Close substrate connection
        await substrate.close()
        print(f"Closed connection to {network_name}")

async def debug_and_post_referenda():
    config = StandaloneConfig()
    
    # Print Discord configuration
    print(f"Discord Server ID: {config.DISCORD_SERVER_ID}")
    print(f"Discord Forum Channel ID: {config.DISCORD_FORUM_CHANNEL_ID}")
    
    # Initialize Discord bot if needed
    discord_task = None
    if config.can_post_to_discord:
        print("Starting Discord bot...")
        discord_task = asyncio.create_task(bot.start(config.DISCORD_API_KEY))
        # Wait for bot to be ready
        while not bot.is_ready():
            await asyncio.sleep(1)
        print("Discord bot is ready")
    
    try:
        # Load networks configuration
        networks_file = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')), 'data', 'networks.json')
        if os.path.exists(networks_file):
            import json
            with open(networks_file, 'r') as f:
                networks = json.load(f)
            
            print(f"Found {len(networks)} networks in configuration")
            
            # Process each enabled network
            for network_name, network_config in networks.items():
                if network_config.get('enabled', False):
                    await process_network(network_name, network_config)
        else:
            # If no networks.json file, just process the default network from environment variables
            await process_network(config.NETWORK_NAME, {
                'symbol': config.SYMBOL,
                'token_decimal': config.TOKEN_DECIMAL,
                'substrate_wss': config.SUBSTRATE_WSS
            })
    finally:
        # Close Discord connection if it was started
        if discord_task and not discord_task.done():
            print("Closing Discord connection...")
            await bot.close()
            print("Discord connection closed")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Parse arguments
    args = parser.parse_args()
    
    # Run the debug and post function
    asyncio.run(debug_and_post_referenda())
