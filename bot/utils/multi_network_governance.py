import asyncio
import time
import json
import discord
from datetime import datetime, timezone
from discord import Embed
from typing import List, Dict, Any, Optional, Tuple

from bot.utils.logger import Logger
from bot.utils.data_processing import CacheManager, ProcessCallData, DiscordFormatting
from bot.utils.button_handler import ButtonHandler, ExternalLinkButton
from bot.utils.network_manager import NetworkManager
from bot.utils.multi_network_handler import MultiNetworkHandler

class MultiNetworkGovernance:
    """
    Handles governance operations across multiple networks, creating threads
    and monitoring referenda for each network in parallel.
    """
    def __init__(self, client, discord_format):
        """
        Initialize governance handler.

        Args:
            client: Discord client/bot instance
            discord_format: DiscordFormatting utility instance
        """
        self.client = client
        self.config = client.config
        self.discord_format = discord_format
        self.logger = Logger()

        # Initialize network components
        self.network_manager = NetworkManager("../data/networks.json")
        self.handler = MultiNetworkHandler(self.network_manager)

    async def start(self):
        """Start network manager and initialize connections."""
        await self.network_manager.start()
        await self.handler.initialize_connections()

    async def stop(self):
        """Stop all network operations and close connections."""
        await self.handler.close_connections()
        await self.network_manager.stop()

    async def check_governance(self):
        """
        Check for new governance proposals across all networks and create Discord threads.
        """
        try:
            self.logger.info("Checking for new proposals across all networks")

            # Check all networks in parallel
            referendum_data = await self.handler.check_all_referendums()

            # Get guild
            server_id = self.config.DISCORD_SERVER_ID
            if server_id == 0:
                self.logger.warning("DISCORD_SERVER_ID is set to 0. Please set a valid server ID in your .env file.")
                self.logger.warning("Skipping forum post creation as no valid server is configured.")
                return

            guild = self.client.get_guild(server_id)
            if not guild:
                self.logger.error(f"Guild not found with ID {server_id}")
                self.logger.warning("Bot may not have joined the server or server ID might be incorrect.")
                self.logger.warning("Please check your .env file and ensure the bot has been added to the server.")
                return

            # Handle referenda for each network
            for network_id, (new_referendums, referendum_info_for) in referendum_data.items():
                if not new_referendums:
                    self.logger.info(f"No new proposals for network {network_id}")
                    continue

                self.logger.info(f"Processing {len(new_referendums)} new proposal(s) for network {network_id}")
                await self._process_network_referenda(
                    network_id,
                    new_referendums,
                    referendum_info_for,
                    guild
                )

            # Get active proposals from all networks and archive old ones
            await self._archive_inactive_proposals()

        except Exception as error:
            self.logger.exception(f"Error in check_governance: {error}")
            raise

    async def _archive_inactive_proposals(self):
        """Archive and lock threads for proposals that are no longer active."""
        self.logger.info("Checking active proposals across networks to archive threads")

        try:
            # Get active proposals for all networks
            active_proposals = {}
            for network_id, substrate_api in self.handler.network_apis.items():
                try:
                    ongoing_refs = await substrate_api.ongoing_referendums_idx()
                    if ongoing_refs is not False:
                        active_proposals[network_id] = ongoing_refs
                except Exception as e:
                    self.logger.error(f"Error getting active proposals for {network_id}: {e}")

            # Archive old proposals
            threads_to_lock = CacheManager.multi_network_archive(
                json_file_path='../data/vote_counts.json',
                active_proposals=active_proposals,
                archive_filename='../data/archived_votes.json'
            )

            if threads_to_lock:
                try:
                    await self.client.lock_threads_by_message_ids(self.config.DISCORD_SERVER_ID, threads_to_lock)
                    self.logger.info(f"Locked {len(threads_to_lock)} threads for archived proposals")
                except Exception as e:
                    self.logger.error(f"Failed to lock threads: {e}")
            else:
                self.logger.info("No threads to lock")

        except Exception as e:
            self.logger.error(f"Error archiving inactive proposals: {e}")

    async def _process_network_referenda(
        self,
        network_id: str,
        new_referendums: Dict,
        referendum_info_for: Dict,
        guild
    ):
        """
        Process new referenda for a specific network.

        Args:
            network_id: Network identifier
            new_referendums: Dictionary of new referenda
            referendum_info_for: Full referendum info
            guild: Discord guild object
        """
        try:
            # Get network configuration
            network_config = await self.network_manager.get_network(network_id)
            if not network_config:
                self.logger.error(f"Network configuration not found for {network_id}")
                return

            # Get Discord channel
            channel = self.client.get_channel(self.config.DISCORD_FORUM_CHANNEL_ID)
            if not channel:
                self.logger.error(f"Channel not found with ID {self.config.DISCORD_FORUM_CHANNEL_ID}")
                return

            # Get asset price
            network_name = network_config['network_name']
            current_price = self.client.get_asset_price_v2(asset_id=network_name)

            # Process each referendum
            for index, values in new_referendums.items():
                await self._create_referendum_thread(
                    guild,
                    channel,
                    network_id,
                    network_name,
                    index,
                    values,
                    referendum_info_for,
                    current_price
                )

        except Exception as e:
            self.logger.error(f"Error processing referenda for network {network_id}: {e}")

    async def _create_referendum_thread(
        self,
        guild,
        channel,
        network_id: str,
        network_name: str,
        index: str,
        values: Dict,
        referendum_info_for: Dict,
        current_price: float
    ):
        """
        Create a Discord thread for a new referendum.

        Args:
            guild: Discord guild object
            channel: Discord channel object
            network_id: Network identifier
            network_name: Network name
            index: Referendum index
            values: Referendum values
            referendum_info_for: Full referendum info
            current_price: Current asset price
        """
        try:
            # Get available tags
            available_channel_tags = []
            if channel is not None:
                available_channel_tags = [tag for tag in channel.available_tags]
            else:
                self.logger.error(f"Channel with ID {self.config.DISCORD_FORUM_CHANNEL_ID} not found")
                return

            # Prepare title
            title_prefix = f"[{network_name.upper()}] "
            title_content = values['title'][:self.config.DISCORD_TITLE_MAX_LENGTH - len(title_prefix)].strip() if values['title'] is not None else "No Title"
            title = title_prefix + title_content

            self.logger.info(f"Creating thread for {network_name} referendum #{index}: {title}")

            # Log data source
            if values['successful_url']:
                self.logger.info(f"Getting on-chain data from: {values['successful_url']}")
            else:
                self.logger.error(f"No context has been set on this proposal")

            # Get governance origin
            governance_origin = [v for i, v in values['onchain']['origin'].items()]

            # Create tag if needed
            governance_tag = await self.client.get_or_create_governance_tag(
                available_channel_tags,
                governance_origin,
                channel,
                network_name=network_name
            )

            # Create thread
            new_proposal_thread = await self.client.manage_discord_thread(
                channel=channel,
                operation='create',
                title=title,
                index=index,
                content=values['content'],
                governance_tag=governance_tag,
                message_id=None,
                client=self.client,
                network_id=network_id
            )

            if not new_proposal_thread:
                self.logger.error(f"Failed to create thread for {network_name} referendum #{index}")
                return

            # Create thread data
            thread_data = {
                "index": index,
                "title": title,
                "origin": governance_origin,
                "network": network_id,
                "aye": 0,
                "nay": 0,
                "recuse": 0,
                "users": {},
                "epoch": int(time.time()),
                "thread_id": new_proposal_thread.message.id
            }

            # Save vote counts
            await self.handler.save_vote_counts(
                network_id=network_id,
                referendum_id=index,
                thread_id=new_proposal_thread.message.id,
                data=thread_data
            )

            # Create initial message and buttons
            initial_results_message = f"👍 AYE: 0    |    👎 NAY: 0    |    ⛔️ RECUSE: 0"
            channel_thread = await guild.fetch_channel(new_proposal_thread.message.id)

            external_links = ExternalLinkButton(index, network_name)
            results_message = await channel_thread.send(content=initial_results_message, view=external_links)

            message_id = new_proposal_thread.message.id
            voting_buttons = ButtonHandler(self.client, message_id, network_id=network_id)
            await new_proposal_thread.message.edit(view=voting_buttons)

            # Pin important messages
            await new_proposal_thread.message.pin()
            await results_message.pin()

            # Clean up pin notifications
            async for message in channel_thread.history(limit=5):
                if message.type == discord.MessageType.pins_add:
                    await message.delete()

            # Send instructions
            if guild is not None:
                try:
                    role = await self.client.create_or_get_role(guild, self.config.TAG_ROLE_NAME)
                    if role:
                        instructions = await channel_thread.send(content=
                                                f"||<@&{role.id}>||"
                                                f"\n**INSTRUCTIONS:**"
                                                f"\n- Vote **AYE** if you want to see this proposal pass"
                                                f"\n- Vote **NAY** if you want to see this proposal fail"
                                                f"\n- Vote **RECUSE** if and **ONLY** if you have a conflict of interest with this proposal"
                                                )
                        self.logger.info(f"Vote instructions added for {network_name} referendum #{index}")
                except Exception as error:
                    self.logger.error(f"Error sending instructions: {error}")

            # Create and add embeds
            try:
                # General info embed
                general_info_embed = Embed(color=0x00FF00)
                general_info = await self.discord_format.add_fields_to_embed(
                    general_info_embed,
                    referendum_info_for[index],
                    network_name=network_name
                )
                await new_proposal_thread.message.edit(embed=general_info)

                # Get Substrate API for network
                substrate_api = await self.handler.get_substrate_api(network_id)
                if not substrate_api:
                    self.logger.error(f"SubstrateAPI not found for network {network_id}")
                    return

                # Add call data
                process_call_data = ProcessCallData(price=current_price, substrate=substrate_api)
                call_data, preimagehash = await substrate_api.referendum_call_data(index=index, gov1=False, call_data=False)
                call_data = await process_call_data.consolidate_call_args(call_data)
                embedded_call_data = await process_call_data.find_and_collect_values(
                    call_data,
                    preimagehash,
                    network_name=network_name
                )

                # Find network logo or use default
                logo_path = f'../assets/{network_name}/{network_name}.png'
                try:
                    await instructions.edit(
                        embed=embedded_call_data,
                        attachments=[discord.File(logo_path, filename='symbol.png')]
                    )
                except FileNotFoundError:
                    self.logger.warning(f"Logo not found for {network_name}, using default")
                    await instructions.edit(embed=embedded_call_data)

            except Exception as e:
                self.logger.error(f"Error creating embeds: {e}")

        except discord.errors.Forbidden as forbidden:
            self.logger.exception(f"Forbidden error: {forbidden}")
            raise forbidden
        except discord.errors.HTTPException as http:
            self.logger.exception(f"HTTP exception: {http}")
            raise http
        except Exception as error:
            self.logger.exception(f"Unexpected error: {error}")
            raise error
