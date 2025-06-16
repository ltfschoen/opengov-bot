import discord
from discord import app_commands, Embed
from discord.ext import commands
from typing import Optional, Dict, Any, List
import json
import asyncio
import os

from utils.network_manager import NetworkManager
from utils.logger import Logger

class NetworkCommands:
    """
    Provides Discord commands for managing network configurations at runtime.
    """
    def __init__(self, bot, network_manager: NetworkManager):
        """
        Initialize network commands.

        Args:
            bot: The Discord bot client
            network_manager: The NetworkManager instance
        """
        self.bot = bot
        self.network_manager = network_manager
        self.logger = Logger()

    def register_commands(self, tree: app_commands.CommandTree, guild_id: int):
        """
        Register network management commands with the Discord bot.

        Args:
            tree: Discord command tree
            guild_id: Discord guild ID for command registration
        """
        guild = discord.Object(id=guild_id)

        @tree.command(
            name='network',
            description='Manage blockchain networks for referendum monitoring',
            guild=guild
        )
        @app_commands.describe(
            action='Action to perform on network configuration',
            network_id='Network identifier (e.g., polkadot, kusama)',
            network_name='Human-readable network name',
            substrate_wss='WebSocket endpoint for the substrate node',
            symbol='Token symbol',
            token_decimal='Token decimal places'
        )
        @app_commands.choices(action=[
            app_commands.Choice(name='add', value='add'),
            app_commands.Choice(name='remove', value='remove'),
            app_commands.Choice(name='update', value='update'),
            app_commands.Choice(name='list', value='list'),
            app_commands.Choice(name='enable', value='enable'),
            app_commands.Choice(name='disable', value='disable'),
        ])
        async def network_command(
            interaction: discord.Interaction,
            action: app_commands.Choice[str],
            network_id: Optional[str] = None,
            network_name: Optional[str] = None,
            substrate_wss: Optional[str] = None,
            symbol: Optional[str] = None,
            token_decimal: Optional[float] = None
        ):
            # Check permissions - only admins can manage networks
            admin_role = interaction.guild.get_role(int(self.bot.config.DISCORD_ADMIN_ROLE))
            if admin_role not in interaction.user.roles:
                await interaction.response.send_message(
                    "You don't have permission to manage networks. Admin role required.",
                    ephemeral=True
                )
                return

            # Defer response to avoid timeout for longer operations
            await interaction.response.defer(ephemeral=False, thinking=True)

            if action.value == 'list':
                await self._list_networks(interaction)
                return

            if action.value in ['add', 'update'] and not all([network_id, network_name, substrate_wss, symbol, token_decimal]):
                await interaction.followup.send(
                    "All parameters (network_id, network_name, substrate_wss, symbol, token_decimal) are required for add/update operations.",
                    ephemeral=True
                )
                return

            if action.value in ['remove', 'enable', 'disable'] and not network_id:
                await interaction.followup.send(
                    "Network ID is required for this operation.",
                    ephemeral=True
                )
                return

            try:
                if action.value == 'add':
                    await self._add_network(
                        interaction,
                        network_id,
                        network_name,
                        substrate_wss,
                        symbol,
                        token_decimal
                    )
                elif action.value == 'update':
                    await self._update_network(
                        interaction,
                        network_id,
                        network_name,
                        substrate_wss,
                        symbol,
                        token_decimal
                    )
                elif action.value == 'remove':
                    await self._remove_network(interaction, network_id)
                elif action.value == 'enable':
                    await self._enable_disable_network(interaction, network_id, True)
                elif action.value == 'disable':
                    await self._enable_disable_network(interaction, network_id, False)
            except Exception as e:
                self.logger.error(f"Error in network command: {e}")
                await interaction.followup.send(
                    f"An error occurred: {str(e)}",
                    ephemeral=True
                )

        self.logger.info("Registered network management commands")

    async def _list_networks(self, interaction: discord.Interaction):
        """List all configured networks."""
        try:
            networks = await self.network_manager.get_all_networks()

            if not networks:
                await interaction.followup.send("No networks are configured.")
                return

            embed = Embed(
                title="Configured Networks",
                description="List of networks currently configured for referendum monitoring",
                color=0x00FF00
            )

            for network_id, config in networks.items():
                enabled = config.get('enabled', True)
                status = "✅ Enabled" if enabled else "❌ Disabled"

                embed.add_field(
                    name=f"{config['network_name']} ({network_id}) - {status}",
                    value=f"Symbol: {config['symbol']}\n"
                          f"Decimals: {config['token_decimal']}\n"
                          f"WSS: {config['substrate_wss'][:30]}...",
                    inline=False
                )

            await interaction.followup.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Error listing networks: {e}")
            await interaction.followup.send(f"Error listing networks: {str(e)}")

    async def _add_network(
        self,
        interaction: discord.Interaction,
        network_id: str,
        network_name: str,
        substrate_wss: str,
        symbol: str,
        token_decimal: float
    ):
        """Add a new network configuration."""
        # Check if network already exists
        existing_networks = await self.network_manager.get_all_networks()
        if network_id in existing_networks:
            await interaction.followup.send(
                f"Network '{network_id}' already exists. Use 'update' to modify it.",
                ephemeral=True
            )
            return

        # Create network config
        network_config = {
            'enabled': True,
            'network_name': network_name,
            'symbol': symbol,
            'token_decimal': token_decimal,
            'substrate_wss': substrate_wss,
            'people_wss': None,
            'forum_tags': []
        }

        # Add network to configuration
        success = await self.network_manager.add_network(network_id, network_config)
        if success:
            await interaction.followup.send(
                f"✅ Network '{network_name}' ({network_id}) successfully added. "
                f"The bot will automatically start monitoring this network."
            )
        else:
            await interaction.followup.send(
                f"❌ Failed to add network '{network_id}'. Please check logs for details.",
                ephemeral=True
            )

    async def _update_network(
        self,
        interaction: discord.Interaction,
        network_id: str,
        network_name: str,
        substrate_wss: str,
        symbol: str,
        token_decimal: float
    ):
        """Update an existing network configuration."""
        # Check if network exists
        existing_networks = await self.network_manager.get_all_networks()
        existing_config = existing_networks.get(network_id)

        if not existing_config:
            await interaction.followup.send(
                f"Network '{network_id}' doesn't exist. Use 'add' to create it.",
                ephemeral=True
            )
            return

        # Update network config
        network_config = {
            'enabled': existing_config.get('enabled', True),
            'network_name': network_name,
            'symbol': symbol,
            'token_decimal': token_decimal,
            'substrate_wss': substrate_wss,
            'people_wss': existing_config.get('people_wss'),
            'forum_tags': existing_config.get('forum_tags', [])
        }

        # Update network in configuration
        success = await self.network_manager.add_network(network_id, network_config)
        if success:
            await interaction.followup.send(
                f"✅ Network '{network_name}' ({network_id}) successfully updated. "
                f"The changes will take effect within a minute."
            )
        else:
            await interaction.followup.send(
                f"❌ Failed to update network '{network_id}'. Please check logs for details.",
                ephemeral=True
            )

    async def _remove_network(self, interaction: discord.Interaction, network_id: str):
        """Remove a network configuration."""
        # Check if network exists
        existing_networks = await self.network_manager.get_all_networks()
        if network_id not in existing_networks:
            await interaction.followup.send(
                f"Network '{network_id}' doesn't exist.",
                ephemeral=True
            )
            return

        # Ask for confirmation
        confirm_msg = await interaction.followup.send(
            f"⚠️ Are you sure you want to remove the '{network_id}' network? "
            f"All associated data will remain in the vote_counts.json file.\n\n"
            f"Reply 'confirm' within 30 seconds to proceed."
        )

        def check(m):
            return m.author == interaction.user and m.content.lower() == 'confirm'

        try:
            await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await interaction.followup.send("Operation cancelled due to timeout.")
            return

        # Remove network
        success = await self.network_manager.remove_network(network_id)
        if success:
            await interaction.followup.send(
                f"✅ Network '{network_id}' successfully removed. "
                f"The bot will no longer monitor this network."
            )
        else:
            await interaction.followup.send(
                f"❌ Failed to remove network '{network_id}'. Please check logs for details.",
                ephemeral=True
            )

    async def _enable_disable_network(
        self,
        interaction: discord.Interaction,
        network_id: str,
        enable: bool
    ):
        """Enable or disable a network."""
        # Check if network exists
        existing_networks = await self.network_manager.get_all_networks()
        existing_config = existing_networks.get(network_id)

        if not existing_config:
            await interaction.followup.send(
                f"Network '{network_id}' doesn't exist.",
                ephemeral=True
            )
            return

        # Update enabled status
        existing_config['enabled'] = enable

        # Save the updated configuration
        success = await self.network_manager.add_network(network_id, existing_config)
        if success:
            status = "enabled" if enable else "disabled"
            await interaction.followup.send(
                f"✅ Network '{network_id}' successfully {status}. "
                f"The changes will take effect within a minute."
            )
        else:
            await interaction.followup.send(
                f"❌ Failed to update network '{network_id}'. Please check logs for details.",
                ephemeral=True
            )
