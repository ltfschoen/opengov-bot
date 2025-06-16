import json
import os
import asyncio
import logging
from typing import Dict, List, Any, Optional
import aiofiles
from bot.utils.logger import Logger

class NetworkManager:
    """
    Manages multiple blockchain networks, allowing for dynamic addition and removal
    while the bot is running.
    """
    def __init__(self, config_path="../data/networks.json"):
        """
        Initialize the NetworkManager with the path to the networks configuration file.

        Args:
            config_path: Path to the JSON file containing network configurations
        """
        self.config_path = config_path
        self.networks = {}
        self.logger = Logger()
        self._load_lock = asyncio.Lock()
        self._watch_task = None

        # Ensure the network config file exists
        if not os.path.exists(config_path):
            self._create_default_config()

    def _create_default_config(self):
        """Create a default network configuration file if it doesn't exist."""
        default_config = {
            "polkadot": {
                "enabled": True,
                "network_name": "polkadot",
                "symbol": "DOT",
                "token_decimal": 10,
                "substrate_wss": "wss://rpc.polkadot.io",
                "people_wss": None,
                "forum_tags": []  # Discord forum tags for Polkadot referenda
            }
        }

        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(default_config, f, indent=4)

    async def start(self):
        """Start the network manager and begin watching for config changes."""
        await self.load_networks()
        self._watch_task = asyncio.create_task(self._watch_config_changes())
        self.logger.info(f"Network Manager started with {len(self.networks)} networks")

    async def stop(self):
        """Stop the network manager and cancel the config watching task."""
        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Network Manager stopped")

    async def load_networks(self) -> Dict[str, dict]:
        """
        Load network configurations from the config file.

        Returns:
            Dict of network configurations keyed by network ID
        """
        async with self._load_lock:
            try:
                async with aiofiles.open(self.config_path, 'r') as f:
                    content = await f.read()
                    self.networks = json.loads(content)

                # Filter to only enabled networks
                self.networks = {k: v for k, v in self.networks.items() if v.get('enabled', True)}
                self.logger.info(f"Loaded {len(self.networks)} network configurations")
                return self.networks
            except Exception as e:
                self.logger.error(f"Error loading network configurations: {e}")
                return {}

    async def add_network(self, network_id: str, network_config: dict) -> bool:
        """
        Add or update a network configuration.

        Args:
            network_id: Unique identifier for the network
            network_config: Configuration dict for the network

        Returns:
            True if successful, False otherwise
        """
        async with self._load_lock:
            try:
                # Load current config
                async with aiofiles.open(self.config_path, 'r') as f:
                    content = await f.read()
                    config = json.loads(content)

                # Add or update the network
                config[network_id] = network_config

                # Save updated config
                async with aiofiles.open(self.config_path, 'w') as f:
                    await f.write(json.dumps(config, indent=4))

                # Update in-memory networks if the added one is enabled
                if network_config.get('enabled', True):
                    self.networks[network_id] = network_config

                self.logger.info(f"Added/updated network: {network_id}")
                return True
            except Exception as e:
                self.logger.error(f"Error adding network {network_id}: {e}")
                return False

    async def remove_network(self, network_id: str) -> bool:
        """
        Remove a network configuration.

        Args:
            network_id: Unique identifier for the network to remove

        Returns:
            True if successful, False otherwise
        """
        async with self._load_lock:
            try:
                # Load current config
                async with aiofiles.open(self.config_path, 'r') as f:
                    content = await f.read()
                    config = json.loads(content)

                # Remove the network if it exists
                if network_id in config:
                    del config[network_id]

                    # Save updated config
                    async with aiofiles.open(self.config_path, 'w') as f:
                        await f.write(json.dumps(config, indent=4))

                    # Update in-memory networks
                    if network_id in self.networks:
                        del self.networks[network_id]

                    self.logger.info(f"Removed network: {network_id}")
                    return True
                else:
                    self.logger.warning(f"Network {network_id} not found")
                    return False
            except Exception as e:
                self.logger.error(f"Error removing network {network_id}: {e}")
                return False

    async def get_network(self, network_id: str) -> Optional[dict]:
        """Get configuration for a specific network."""
        return self.networks.get(network_id)

    async def get_all_networks(self) -> Dict[str, dict]:
        """Get all enabled network configurations."""
        return self.networks

    async def _watch_config_changes(self):
        """
        Watch for changes to the network configuration file and reload when changes occur.
        This allows adding networks dynamically while the bot is running.
        """
        last_modified = os.path.getmtime(self.config_path) if os.path.exists(self.config_path) else 0

        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                if os.path.exists(self.config_path):
                    current_modified = os.path.getmtime(self.config_path)
                    if current_modified > last_modified:
                        self.logger.info("Network configuration file changed, reloading...")
                        await self.load_networks()
                        last_modified = current_modified
            except Exception as e:
                self.logger.error(f"Error watching network config changes: {e}")
